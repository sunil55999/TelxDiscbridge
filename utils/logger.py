"""Logging configuration and utilities."""

import sys
import os
from pathlib import Path
from loguru import logger


def setup_logger(log_level: str = "INFO", log_file: str = "forwarder_bot.log"):
    """Setup loguru logger with custom configuration."""
    
    # Remove default handler
    logger.remove()
    
    # Custom format with extra context
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "session:<yellow>{extra[session_name]}</yellow> | "
        "pair:<blue>{extra[pair_id]}</blue> - "
        "<level>{message}</level>"
    )

    # Console handler with colored output
    logger.add(
        sys.stdout,
        level=log_level.upper(),
        format=log_format,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # File handler for persistent logging
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        str(log_path),
        level="DEBUG",
        format=log_format,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,  # Thread-safe logging
        # Default values for extra context
        filter=lambda record: record.update(session_name=record["extra"].get("session_name", "N/A"), pair_id=record["extra"].get("pair_id", "N/A"))
    )
    
    # Error file handler for errors only
    error_log_path = log_path.parent / f"error_{log_path.name}"
    logger.add(
        str(error_log_path),
        level="ERROR",
        format=log_format,
        rotation="5 MB",
        retention="60 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,
        filter=lambda record: record.update(session_name=record["extra"].get("session_name", "N/A"), pair_id=record["extra"].get("pair_id", "N/A"))
    )
    
    logger.info(f"Logger initialized - Level: {log_level}, File: {log_file}")


def get_logger(name: str, session_name: str = None, pair_id: int = None):
    """Get a logger instance with a specific name and context."""
    return logger.patch(lambda record: record["extra"].update(session_name=session_name, pair_id=pair_id)).bind(name=name)


def log_function_call(func):
    """Decorator to log function calls."""
    def wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed with error: {e}")
            raise
    return wrapper


def log_async_function_call(func):
    """Decorator to log async function calls."""
    async def wrapper(*args, **kwargs):
        logger.debug(f"Calling async {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Async {func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Async {func.__name__} failed with error: {e}")
            raise
    return wrapper


class LoggerMixin:
    """Mixin class to add logger to any class."""
    
    @property
    def logger(self):
        """Get logger instance for this class."""
        return logger.bind(name=self.__class__.__name__)


def log_performance(func):
    """Decorator to log function performance."""
    import time
    
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            logger.debug(f"{func.__name__} executed in {end_time - start_time:.4f} seconds")
            return result
        except Exception as e:
            end_time = time.time()
            logger.error(f"{func.__name__} failed after {end_time - start_time:.4f} seconds: {e}")
            raise
    return wrapper


def log_async_performance(func):
    """Decorator to log async function performance."""
    import time
    
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            end_time = time.time()
            logger.debug(f"Async {func.__name__} executed in {end_time - start_time:.4f} seconds")
            return result
        except Exception as e:
            end_time = time.time()
            logger.error(f"Async {func.__name__} failed after {end_time - start_time:.4f} seconds: {e}")
            raise
    return wrapper


def configure_logging_for_library(library_name: str, level: str = "WARNING"):
    """Configure logging level for external libraries."""
    import logging
    logging.getLogger(library_name).setLevel(getattr(logging, level.upper()))


# Configure external library logging levels
def setup_external_logging():
    """Setup logging for external libraries."""
    configure_logging_for_library("telethon", "WARNING")
    configure_logging_for_library("discord", "WARNING")
    configure_logging_for_library("telegram", "WARNING")
    configure_logging_for_library("urllib3", "WARNING")
    configure_logging_for_library("aiohttp", "WARNING")
    configure_logging_for_library("sqlalchemy", "WARNING")


# Call setup for external libraries
setup_external_logging()
