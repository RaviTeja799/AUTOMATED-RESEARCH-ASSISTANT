"""
Lightweight embedding service for Vercel deployment.
Uses Ollama's embedding API instead of local sentence-transformers.
Falls back gracefully when torch is not available.
"""
from typing import List, Union, Optional
import httpx

from app.core.config import settings
from app.utils.logger import app_logger


class EmbeddingServiceLite:
    """
    Lightweight embedding service using Ollama's embedding endpoint.
    No torch/sentence-transformers dependency required.
    """

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = "nomic-embed-text"  # Ollama embedding model
        self.dimension = settings.embedding_dimension
        app_logger.info(f"EmbeddingServiceLite initialized: {self.base_url}")

    def embed_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        single = isinstance(text, str)
        texts = [text] if single else text

        embeddings = []
        with httpx.Client(timeout=30.0) as client:
            for t in texts:
                response = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": t}
                )
                response.raise_for_status()
                embeddings.append(response.json()["embedding"])

        return embeddings[0] if single else embeddings

    def embed_query(self, query: str) -> List[float]:
        return self.embed_text(query)

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        return self.embed_text(documents)

    @property
    def embedding_dimension(self) -> int:
        return self.dimension


def get_embedding_service():
    """
    Factory that returns the appropriate embedding service
    based on available packages.
    """
    try:
        from app.services.embedding_service import EmbeddingService
        return EmbeddingService()
    except ImportError:
        app_logger.warning("sentence-transformers not available, using lite embedding service")
        return EmbeddingServiceLite()
