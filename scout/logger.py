"""Logging utilities for Scout v0."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str, log_file: str = "scout_retries.log") -> logging.Logger:
    """
    Setup a dedicated logger that appends LLM validation/retry errors to a file.

    Args:
        name: Logger name (typically __name__).
        log_file: Path to the log file (default: scout_retries.log in CWD).

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # File handler: Rotating file handler for LLM errors and retries
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)

    # Console handler: Only errors and critical
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.ERROR)
    console_formatter = logging.Formatter(
        fmt="%(levelname)s: %(message)s",
    )
    console_handler.setFormatter(console_formatter)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
