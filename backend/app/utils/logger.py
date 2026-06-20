"""
TenderAI — Structured Logging with Loguru
Replaces Python's default logging with colored, structured output.
"""

import sys

from loguru import logger

from app.config import settings

# Remove default handler
logger.remove()

log_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

logger.add(
    sys.stderr,
    format=log_format,
    level="DEBUG" if settings.APP_DEBUG else "INFO",
    colorize=True,
    backtrace=True,
    diagnose=settings.APP_DEBUG,
)

if settings.APP_ENV == "production":
    logger.add(
        "logs/tenderai_{time:YYYY-MM-DD}.log",
        rotation="500 MB",
        retention="30 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="INFO",
        enqueue=True,  # Thread-safe
    )

# Export logger for use across the app
__all__ = ["logger"]
