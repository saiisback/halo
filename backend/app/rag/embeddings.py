"""
Sentence Transformers Embeddings Client

Generates embeddings using local sentence-transformers models.
Uses all-MiniLM-L6-v2 for efficient, high-quality embeddings.
"""

import asyncio
from typing import Optional
from sentence_transformers import SentenceTransformer

from app.core.config import settings


class LocalEmbeddings:
    """Client for local sentence-transformers embeddings"""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.embedding_model
        self._model: Optional[SentenceTransformer] = None

    def _get_model(self) -> SentenceTransformer:
        """Get or create the embedding model"""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    async def embed(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        try:
            model = self._get_model()
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, lambda: model.encode(text, convert_to_numpy=True)
            )
            return embedding.tolist()
        except Exception as e:
            print(f"Embedding error: {e}")
            return []

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            model = self._get_model()
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, lambda: model.encode(texts, convert_to_numpy=True)
            )
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            print(f"Batch embedding error: {e}")
            return [[] for _ in texts]


# Global instance
_embeddings_client: Optional[LocalEmbeddings] = None


def get_embeddings_client() -> LocalEmbeddings:
    """Get global embeddings client"""
    global _embeddings_client
    if _embeddings_client is None:
        _embeddings_client = LocalEmbeddings()
    return _embeddings_client


async def get_embedding(text: str) -> list[float]:
    """
    Convenience function to get embedding for text.

    Args:
        text: Text to embed

    Returns:
        Embedding vector
    """
    client = get_embeddings_client()
    return await client.embed(text)


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Convenience function to get embeddings for multiple texts.

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    client = get_embeddings_client()
    return await client.embed_batch(texts)


async def check_embeddings_available() -> bool:
    """Check if embedding model is available"""
    try:
        embedding = await get_embedding("test")
        return len(embedding) > 0
    except Exception:
        return False
