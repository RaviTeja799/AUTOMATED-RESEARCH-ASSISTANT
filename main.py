"""
Main entry point for the Research Assistant application.
"""
import uvicorn

from app.core.config import settings
from app.utils.logger import app_logger


def main():
    """
    Run the FastAPI application with uvicorn.
    """
    app_logger.info("=" * 60)
    app_logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    app_logger.info("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
        workers=1 if settings.debug else 4,
    )


if __name__ == "__main__":
    main()
