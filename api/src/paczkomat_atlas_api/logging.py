"""structlog configuration. Call configure_logging() once at process start."""

from __future__ import annotations

import logging
import sys

import structlog
from structlog.typing import Processor

from paczkomat_atlas_api.config import settings


def configure_logging() -> None:
    """Wire stdlib logging through structlog. JSON in prod, pretty in dev."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    is_tty = sys.stderr.isatty()
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if is_tty:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger, optionally bound to a name."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
