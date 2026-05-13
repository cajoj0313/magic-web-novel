"""Structured logging configuration."""

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for the application.

    All loggers use a consistent format: timestamp | level | logger_name | message
    """
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger("app")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.addHandler(handler)

    # Silence overly verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a namespaced logger under the 'app' namespace."""
    return logging.getLogger(f"app.{name}")
