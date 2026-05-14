"""
Custom exceptions for the Research Assistant application.
"""
from typing import Optional, Any, Dict


class ResearchAssistantException(Exception):
    """Base exception for all application errors."""
    
    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        status_code: int = 500
    ):
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(self.message)


class DocumentProcessingError(ResearchAssistantException):
    """Raised when document processing fails."""
    
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=422)


class PDFExtractionError(DocumentProcessingError):
    """Raised when PDF text extraction fails."""
    pass


class ChunkingError(DocumentProcessingError):
    """Raised when text chunking fails."""
    pass


class RetrievalError(ResearchAssistantException):
    """Raised when retrieval operations fail."""
    
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=500)


class ElasticsearchError(RetrievalError):
    """Raised when Elasticsearch operations fail."""
    pass


class EmbeddingError(ResearchAssistantException):
    """Raised when embedding generation fails."""
    
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=500)


class LLMError(ResearchAssistantException):
    """Raised when LLM operations fail."""
    
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=500)


class OllamaError(LLMError):
    """Raised when Ollama API calls fail."""
    pass


class ValidationError(ResearchAssistantException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=400)


class NotFoundError(ResearchAssistantException):
    """Raised when a resource is not found."""
    
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=404)


class PaperNotFoundError(NotFoundError):
    """Raised when a paper is not found."""
    pass


class RateLimitError(ResearchAssistantException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", detail: Optional[str] = None):
        super().__init__(message, detail, status_code=429)


class AuthenticationError(ResearchAssistantException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", detail: Optional[str] = None):
        super().__init__(message, detail, status_code=401)


class AuthorizationError(ResearchAssistantException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Insufficient permissions", detail: Optional[str] = None):
        super().__init__(message, detail, status_code=403)


class ServiceUnavailableError(ResearchAssistantException):
    """Raised when a required service is unavailable."""
    
    def __init__(self, service_name: str, detail: Optional[str] = None):
        message = f"Service unavailable: {service_name}"
        super().__init__(message, detail, status_code=503)
