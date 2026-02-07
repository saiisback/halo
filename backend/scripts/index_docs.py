"""
Documentation Indexer Script

Scrapes Stellar documentation and indexes it into ChromaDB for RAG.

Usage:
    python -m scripts.index_docs

This script:
1. Scrapes official Stellar/Soroban documentation
2. Chunks the content into manageable pieces
3. Generates embeddings using Ollama
4. Stores in ChromaDB for retrieval
"""

import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from bs4 import BeautifulSoup
import chromadb

from app.core.config import settings
from app.rag.embeddings import get_embeddings


# Base URL for Stellar docs
STELLAR_DOCS_BASE = "https://developers.stellar.org"

# Sections to crawl (will discover pages within these)
DOCS_SECTIONS = [
    "/docs/build/smart-contracts",
    "/docs/learn/fundamentals",
    "/docs/tools/sdks",
]

# Collection names in ChromaDB
COLLECTIONS = {
    "soroban-sdk": "soroban_sdk_docs",
    "stellar-sdk-js": "stellar_js_sdk_docs",
    "soroban-examples": "soroban_examples_docs",
}


async def fetch_page(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
    """Fetch a page and return (url, html)"""
    try:
        response = await client.get(url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        return (str(response.url), response.text)
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return (url, "")


def extract_text(html: str) -> str:
    """Extract main text content from HTML"""
    if not html:
        return ""

    soup = BeautifulSoup(html, 'html.parser')

    # Remove script, style, nav, footer elements
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
        element.decompose()

    # Try to find main content area
    main_content = (
        soup.find('main') or
        soup.find('article') or
        soup.find(class_=re.compile(r'content|main|article', re.I)) or
        soup.find('body')
    )

    if main_content:
        return main_content.get_text(separator='\n', strip=True)

    return soup.get_text(separator='\n', strip=True)


def extract_links(html: str, base_url: str, section_prefix: str) -> list[str]:
    """Extract documentation links from a page"""
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    links = set()

    for a in soup.find_all('a', href=True):
        href = a['href']

        # Skip anchors, external links, assets
        if href.startswith('#') or href.startswith('mailto:'):
            continue
        if any(ext in href for ext in ['.png', '.jpg', '.svg', '.pdf', '.zip']):
            continue

        # Build absolute URL
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        # Only keep links within our section and same domain
        if parsed.netloc == urlparse(STELLAR_DOCS_BASE).netloc:
            if parsed.path.startswith(section_prefix) or parsed.path.startswith('/docs/'):
                # Remove fragments and query params
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                links.add(clean_url)

    return list(links)


async def crawl_section(section: str, max_pages: int = 50) -> list[tuple[str, str]]:
    """Crawl a documentation section and return list of (url, content)"""

    start_url = f"{STELLAR_DOCS_BASE}{section}"
    print(f"\n  Crawling section: {section}")

    visited = set()
    to_visit = [start_url]
    results = []

    async with httpx.AsyncClient() as client:
        while to_visit and len(visited) < max_pages:
            # Get next batch of URLs
            batch = []
            while to_visit and len(batch) < 5:
                url = to_visit.pop(0)
                if url not in visited:
                    visited.add(url)
                    batch.append(url)

            if not batch:
                break

            # Fetch batch concurrently
            tasks = [fetch_page(client, url) for url in batch]
            pages = await asyncio.gather(*tasks)

            for url, html in pages:
                if html:
                    text = extract_text(html)
                    if text and len(text) > 100:  # Skip empty pages
                        results.append((url, text))
                        print(f"    ✓ {url}")

                    # Find more links
                    new_links = extract_links(html, url, section)
                    for link in new_links:
                        if link not in visited and link not in to_visit:
                            to_visit.append(link)

    return results


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []

    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = ' '.join(words[start:end])
        if len(chunk) > 50:  # Skip tiny chunks
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


async def index_documents(
    doc_type: str,
    documents: list[str],
    metadatas: list[dict],
) -> int:
    """Index documents into ChromaDB."""

    if not documents:
        return 0

    # Get ChromaDB client
    persist_dir = Path(settings.chroma_persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(persist_dir))

    collection_name = COLLECTIONS.get(doc_type, "default_docs")

    # Delete existing collection if exists
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    # Create collection
    collection = client.create_collection(
        name=collection_name,
        metadata={"doc_type": doc_type},
    )

    # Generate embeddings
    print(f"  Generating embeddings for {len(documents)} chunks...")
    embeddings = await get_embeddings(documents)

    # Filter out empty embeddings
    valid_docs = []
    valid_embeddings = []
    valid_metadatas = []
    valid_ids = []

    for i, (doc, emb, meta) in enumerate(zip(documents, embeddings, metadatas)):
        if emb:
            valid_docs.append(doc)
            valid_embeddings.append(emb)
            valid_metadatas.append(meta)
            valid_ids.append(f"{doc_type}_{i}")

    if not valid_docs:
        print("  No valid embeddings generated")
        return 0

    # Add to collection
    collection.add(
        documents=valid_docs,
        embeddings=valid_embeddings,
        metadatas=valid_metadatas,
        ids=valid_ids,
    )

    return len(valid_docs)


async def index_stellar_docs():
    """Index Stellar documentation by crawling"""
    print("\nIndexing Stellar documentation...")

    all_chunks = []
    all_metadatas = []

    # Crawl each section
    for section in DOCS_SECTIONS:
        pages = await crawl_section(section, max_pages=30)

        for url, content in pages:
            chunks = chunk_text(content)
            for chunk in chunks:
                all_chunks.append(chunk)
                all_metadatas.append({"source": url, "type": "soroban-sdk"})

    # Also add hardcoded essential docs (these are always reliable)
    print("\n  Adding built-in documentation...")
    from app.rag.retriever import SOROBAN_FALLBACK_DOCS, STELLAR_JS_FALLBACK_DOCS

    for doc in SOROBAN_FALLBACK_DOCS:
        all_chunks.append(doc)
        all_metadatas.append({"source": "builtin", "type": "soroban-sdk"})

    for doc in STELLAR_JS_FALLBACK_DOCS:
        all_chunks.append(doc)
        all_metadatas.append({"source": "builtin", "type": "stellar-sdk-js"})

    count = await index_documents("soroban-sdk", all_chunks, all_metadatas)
    print(f"\n  Total indexed: {count} chunks")
    return count


async def main():
    """Main indexing function"""
    print("=" * 50)
    print("Halo Documentation Indexer")
    print("=" * 50)

    # Check if Ollama is available for embeddings
    from app.rag.embeddings import check_embeddings_available

    print("\nChecking Ollama embeddings...")
    if not await check_embeddings_available():
        print("ERROR: Ollama embeddings not available.")
        print("Please ensure Ollama is running with nomic-embed-text model:")
        print("  ollama pull nomic-embed-text")
        print("  ollama serve")
        return

    print("Ollama embeddings available!")

    # Index documentation
    total = await index_stellar_docs()

    print("\n" + "=" * 50)
    print(f"Total documents indexed: {total}")
    print(f"ChromaDB persisted to: {settings.chroma_persist_dir}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
