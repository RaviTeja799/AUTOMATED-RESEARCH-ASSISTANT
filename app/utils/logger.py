"""
Centralized logging configuration using loguru.
"""
import sys
import logging
from pathlib import Path
from typing import Optional, Any
from contextvars import ContextVar

from loguru import logger

from app.core.config import settings


# Context variable for request ID tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


def setup_logger():
    """Configure application logger with request ID support."""
    
    # Remove default handler
    logger.remove()
    
    # Console handler with color and request ID
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <yellow>{extra[request_id]}</yellow> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )
    
    # File handler for all logs
    log_file = settings.log_dir / "app.log"
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {extra[request_id]} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )
    
    # Error file handler with backtrace
    error_log_file = settings.log_dir / "error.log"
    logger.add(
        error_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {extra[request_id]} - {message}\n{exception}",
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )
    
    # Configure logger to include request_id in extra
    logger.configure(extra={"request_id": "N/A"})
    
    logger.info(f"Logging configured with level: {settings.log_level}")
    
    return logger


def get_logger_with_context(**context: Any):
    """
    Get a logger instance with additional context.
    
    Args:
        **context: Additional context to include in logs
        
    Returns:
        Logger instance with context
    """
    request_id = request_id_var.get()
    if request_id:
        context['request_id'] = request_id
    else:
        context['request_id'] = 'N/A'
    
    return logger.bind(**context)


def set_request_id(request_id: str) -> None:
    """Set the request ID for the current context."""
    request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """Get the request ID for the current context."""
    return request_id_var.get()


class InterceptHandler(logging.Handler):
    """Intercept standard logging messages and redirect to loguru."""
    
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_intercept_handler() -> None:
    """Intercept standard library logging and redirect to loguru."""
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Intercept specific loggers
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]


# Initialize logger
app_logger = setup_logger()
setup_intercept_handler()
