"""Centralized logging setup using rich for readable console output."""
from __future__ import annotations

import logging
from pathlib import Path

try:
    from rich.logging import RichHandler
    _HAS_RICH = True
except ImportError:  # pragma: no cover - rich is optional at runtime
    _HAS_RICH = False


def setup_logging(level: str = "INFO", file: str | None = None) -> logging.Logger:
    """Configure the root 'heartwood' logger and return it."""
    logger = logging.getLogger("heartwood")
    logger.setLevel(level.upper())
    logger.handlers.clear()

    if _HAS_RICH:
        console_handler: logging.Handler = RichHandler(
            rich_tracebacks=True, show_path=False
        )
        console_handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    else:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
        )
    logger.addHandler(console_handler)

    if file:
        path = Path(file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the 'heartwood' namespace."""
    return logging.getLogger(f"heartwood.{name}")
