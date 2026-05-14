"""
Vercel serverless entry point for the Research Assistant API.

This module provides a lightweight FastAPI app for Vercel deployment.
Heavy services (embeddings, LLM) connect lazily on first request.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create minimal app for Vercel
app = FastAPI(
    title="Automated Research Assistant",
    version="1.0.0",
    description="AI-powered research assistant with RAG capabilities",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "Automated Research Assistant",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "note": "Configure ELASTICSEARCH_URL and OLLAMA_BASE_URL env vars to enable full functionality",
        "github": "https://github.com/vamsi-op/AUTOMATED-RESEARCH-ASSISTANT",
    }


@app.get("/api/v1/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/api/v1/health/ready")
async def readiness():
    """Check if external services are reachable."""
    import httpx

    es_url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    es_ok = False
    ollama_ok = False

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(es_url)
            es_ok = r.status_code < 500
    except Exception:
        pass

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{ollama_url}/api/tags")
            ollama_ok = r.status_code < 500
    except Exception:
        pass

    return {
        "status": "ready" if (es_ok or ollama_ok) else "degraded",
        "elasticsearch": es_ok,
        "ollama": ollama_ok,
        "note": "Set ELASTICSEARCH_URL and OLLAMA_BASE_URL environment variables in Vercel dashboard",
    }


@app.get("/api/v1/health")
async def health():
    """Full health check."""
    import httpx
    from datetime import datetime

    es_url = os.getenv("ELASTICSEARCH_URL", "")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "")

    es_ok = False
    ollama_ok = False

    if es_url:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(es_url)
                es_ok = r.status_code < 500
        except Exception:
            pass

    if ollama_url:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{ollama_url}/api/tags")
                ollama_ok = r.status_code < 500
        except Exception:
            pass

    configured = bool(es_url and ollama_url)

    return {
        "status": "healthy" if configured else "unconfigured",
        "version": "1.0.0",
        "elasticsearch_connected": es_ok,
        "ollama_available": ollama_ok,
        "timestamp": datetime.utcnow().isoformat(),
        "setup_required": not configured,
        "setup_instructions": "Add ELASTICSEARCH_URL and OLLAMA_BASE_URL in Vercel Project Settings → Environment Variables",
    }


# Include full API routes if services are configured
_full_app_loaded = False


def _try_load_full_app():
    """Attempt to load the full application routes."""
    global _full_app_loaded
    if _full_app_loaded:
        return

    try:
        from app.api.v1.router import api_router
        app.include_router(api_router)
        _full_app_loaded = True
    except Exception as e:
        # Log but don't crash - basic endpoints still work
        import logging
        logging.warning(f"Could not load full API routes: {e}")


# Try to load full routes at startup
_try_load_full_app()
