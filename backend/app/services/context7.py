"""
Context7 Service - Fetch up-to-date library documentation via Context7 REST API.

Provides async functions to search for libraries and retrieve documentation
to supplement the existing ChromaDB-based RAG pipeline.
"""

import httpx
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

CONTEXT7_BASE_URL = "https://api.context7.com/v1"


async def search_library(
    library_name: str,
    query: str = "",
) -> list[dict]:
    """
    Search Context7 for a library by name.

    Args:
        library_name: Library identifier (e.g. "stellar/soroban-sdk")
        query: Optional query to narrow results

    Returns:
        List of matching libraries with IDs, or empty list on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = _build_headers()
            resp = await client.post(
                f"{CONTEXT7_BASE_URL}/search",
                json={"query": library_name},
                headers=headers,
            )

            if resp.status_code == 429:
                logger.warning("Context7 rate limited, skipping")
                return []

            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get("results", [])

    except Exception as e:
        logger.warning(f"Context7 library search failed: {e}")
        return []


async def get_library_docs(
    library_id: str,
    topic: str = "",
) -> Optional[str]:
    """
    Fetch documentation for a specific library from Context7.

    Args:
        library_id: Context7 library ID (from search_library results)
        topic: Topic or query to focus the documentation

    Returns:
        Documentation text, or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = _build_headers()
            params: dict = {"libraryId": library_id}
            if topic:
                params["topic"] = topic
            params["tokens"] = 5000

            resp = await client.get(
                f"{CONTEXT7_BASE_URL}/context",
                params=params,
                headers=headers,
            )

            if resp.status_code == 429:
                logger.warning("Context7 rate limited, skipping")
                return None

            resp.raise_for_status()
            data = resp.json()

            # Extract text content from response
            if isinstance(data, str):
                return data
            if isinstance(data, dict):
                return data.get("content") or data.get("text") or data.get("docs", "")

            return None

    except Exception as e:
        logger.warning(f"Context7 doc fetch failed: {e}")
        return None


def _build_headers() -> dict:
    """Build request headers, including API key if configured."""
    headers = {"Accept": "application/json"}
    if settings.context7_api_key:
        headers["Authorization"] = f"Bearer {settings.context7_api_key}"
    return headers
