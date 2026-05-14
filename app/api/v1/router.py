"""
Main API v1 router that aggregates all endpoint routers.
"""
from fastapi import APIRouter

from app.api.v1 import health, papers, query, summarize, literature, agent


# Create main v1 router
api_router = APIRouter(prefix="/api/v1")

# Include all sub-routers
api_router.include_router(health.router)
api_router.include_router(papers.router)
api_router.include_router(query.router)
api_router.include_router(summarize.router)
api_router.include_router(literature.router)
api_router.include_router(agent.router)
