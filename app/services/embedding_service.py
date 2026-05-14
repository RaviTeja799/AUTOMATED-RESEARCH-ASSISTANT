"""
Embedding generation service using sentence-transformers.
"""
from typing import List, Union
import torch
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.utils.logger import app_logger


class EmbeddingService:
    """Generate embeddings for text using sentence-transformers."""
    
    _instance = None
    _model = None
    
    def __new__(cls):
        """Singleton pattern to avoid loading model multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize embedding model."""
        if self._model is None:
            self.logger = app_logger
            self.model_name = settings.embedding_model
            self.batch_size = settings.embedding_batch_size
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
            self.logger.info(f"Loading embedding model: {self.model_name}")
            self.logger.info(f"Using device: {self.device}")
            
            try:
                self._model = SentenceTransformer(self.model_name)
                self._model.to(self.device)
                self.logger.info("Embedding model loaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to load embedding model: {e}")
                raise
    
    def embed_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text.
        
        Args:
            text: Single text string or list of texts
            
        Returns:
            Single embedding vector or list of embedding vectors
        """
        if isinstance(text, str):
            text = [text]
            single_input = True
        else:
            single_input = False
        
        try:
            # Generate embeddings in batches
            embeddings = self._model.encode(
                text,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True  # Normalize for cosine similarity
            )
            
            # Convert to list
            embeddings = embeddings.tolist()
            
            if single_input:
                return embeddings[0]
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {e}")
            raise
    
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
        return self._model.get_sentence_embedding_dimension()
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between -1 and 1
        """
        import numpy as np
        
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Cosine similarity
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        
        return float(similarity)


# Global instance
embedding_service = EmbeddingService()
