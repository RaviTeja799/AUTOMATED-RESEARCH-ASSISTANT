"""
Embedding generation service using sentence-transformers.
Falls back gracefully when torch is not available (e.g., Vercel).
"""
from typing import List, Union, Optional

from app.core.config import settings
from app.utils.logger import app_logger


class EmbeddingService:
    """Generate embeddings for text using sentence-transformers."""

    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self.logger = app_logger
            self.model_name = settings.embedding_model
            self.batch_size = settings.embedding_batch_size

            try:
                import torch
                from sentence_transformers import SentenceTransformer

                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                self.logger.info(f"Loading embedding model: {self.model_name}")
                self.logger.info(f"Using device: {self.device}")

                self._model = SentenceTransformer(self.model_name)
                self._model.to(self.device)
                self._use_local = True
                self.logger.info("Embedding model loaded successfully")

            except ImportError:
                self.logger.warning(
                    "sentence-transformers/torch not available. "
                    "Using Ollama embeddings as fallback."
                )
                self._model = "ollama_fallback"
                self._use_local = False
                self.device = "cpu"
    
    def embed_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """Generate embeddings for text."""
        if isinstance(text, str):
            text = [text]
            single_input = True
        else:
            single_input = False

        if self._use_local:
            try:
                embeddings = self._model.encode(
                    text,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
                embeddings = embeddings.tolist()
            except Exception as e:
                self.logger.error(f"Error generating embeddings: {e}")
                raise
        else:
            # Ollama fallback
            import httpx
            embeddings = []
            with httpx.Client(timeout=30.0) as client:
                for t in text:
                    resp = client.post(
                        f"{settings.ollama_base_url}/api/embeddings",
                        json={"model": "nomic-embed-text", "prompt": t}
                    )
                    resp.raise_for_status()
                    embeddings.append(resp.json()["embedding"])

        return embeddings[0] if single_input else embeddings
    
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            Embedding vector
        """
        return self.embed_text(query)
    
    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple documents.
        
        Args:
            documents: List of document texts
            
        Returns:
            List of embedding vectors
        """
        return self.embed_text(documents)
    
    @property
    def embedding_dimension(self) -> int:
        """Get the dimension of embeddings."""
        if self._use_local:
            return self._model.get_sentence_embedding_dimension()
        return settings.embedding_dimension

    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        import numpy as np
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))


# Global instance
embedding_service = EmbeddingService()
