"""
Custom exceptions for the Research Assistant application.
"""
from typing import Optional


class ResearchAssistantException(Exception):
    def __init__(self, message: str, detail: Optional[str] = None, status_code: int = 500):
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(self.message)


class DocumentProcessingError(ResearchAssistantException):
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=422)


class PDFExtractionError(DocumentProcessingError):
    pass


class RetrievalError(ResearchAssistantException):
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=500)


class EmbeddingError(ResearchAssistantException):
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=500)


class LLMError(ResearchAssistantException):
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=500)


class ValidationError(ResearchAssistantException):
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=400)


class NotFoundError(ResearchAssistantException):
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=404)


class PaperNotFoundError(NotFoundError):
    pass


class ServiceUnavailableError(ResearchAssistantException):
    def __init__(self, service_name: str, detail: Optional[str] = None):
        super().__init__(f"Service unavailable: {service_name}", detail, status_code=503)
