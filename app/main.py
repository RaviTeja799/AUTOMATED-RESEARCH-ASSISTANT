"""
Main FastAPI application with middleware, exception handlers, and lifecycle events.
"""
import time
import uuid
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.exceptions import ResearchAssistantException
from app.api.v1.router import api_router
from app.api.deps import cleanup_services
from app.utils.logger import app_logger, set_request_id


# ============================================================================
# Lifespan Context Manager
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    app_logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    app_logger.info(f"Environment: {'Development' if settings.debug else 'Production'}")
    app_logger.info(f"Elasticsearch URL: {settings.elasticsearch_url}")
    app_logger.info(f"Ollama URL: {settings.ollama_base_url}")
    
    yield
    
    # Shutdown
    app_logger.info("Shutting down application...")
    await cleanup_services()
    app_logger.info("Application shutdown complete")


# ============================================================================
# Create FastAPI Application
# ============================================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    **Automated Research Assistant API**
    
    A production-grade research assistant system that processes academic PDFs, 
    performs intelligent retrieval, and provides AI-powered research capabilities 
    using RAG (Retrieval-Augmented Generation).
    
    ## Features
    
    * **Document Processing**: Upload and process academic PDFs
    * **Hybrid Search**: Semantic + keyword search using Elasticsearch
    * **RAG-based Q&A**: Answer research questions with source citations
    * **Paper Summarization**: Generate concise summaries of academic papers
    * **Literature Reviews**: Automated literature review generation
    
    ## Tech Stack
    
    * FastAPI for backend APIs
    * Ollama for local LLM inference
    * Elasticsearch for hybrid retrieval
    * LangChain for agent orchestration
    * sentence-transformers for embeddings
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    debug=settings.debug,
    lifespan=lifespan,
)


# ============================================================================
# Middleware
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip Middleware for response compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request ID and Logging Middleware
@app.middleware("http")
async def add_request_id_and_logging(request: Request, call_next: Callable) -> Response:
    """
    Add request ID to all requests and log request/response.
    """
    # Generate or extract request ID
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    set_request_id(request_id)
    
    # Log request
    start_time = time.time()
    app_logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={"request_id": request_id, "method": request.method, "path": request.url.path}
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Add headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log response
    app_logger.info(
        f"Request completed: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time": process_time,
        }
    )
    
    return response


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(ResearchAssistantException)
async def research_assistant_exception_handler(
    request: Request,
    exc: ResearchAssistantException
) -> JSONResponse:
    """
    Handle custom application exceptions.
    """
    app_logger.error(
        f"Application error: {exc.message}",
        extra={"detail": exc.detail, "status_code": exc.status_code}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "detail": exc.detail,
            "status_code": exc.status_code,
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handle HTTP exceptions.
    """
    app_logger.warning(
        f"HTTP error: {exc.status_code} - {exc.detail}",
        extra={"status_code": exc.status_code}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP error",
            "detail": exc.detail,
            "status_code": exc.status_code,
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle request validation errors.
    """
    app_logger.warning(
        f"Validation error: {exc.errors()}",
        extra={"errors": exc.errors()}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "detail": exc.errors(),
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle unexpected exceptions.
    """
    app_logger.error(
        f"Unexpected error: {str(exc)}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        }
    )


# ============================================================================
# Include Routers
# ============================================================================

app.include_router(api_router)


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["Root"])
async def root() -> dict:
    """
    Root endpoint with API information.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
    }


# ============================================================================
# Run Application (for development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
