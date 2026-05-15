"""structlog configuration. Call configure_logging() once at process start."""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog
from structlog.typing import Processor

from paczkomat_atlas_api.config import settings

# Matches `password=foo`, `api_key: "bar"`, `token=baz`, etc. Catches both
# query-string and JSON-ish forms. Used by redact_sensitive() below to scrub
# any string value passed to structlog before it hits the renderer.
#
# The pattern looks for a sensitive key, followed by `:` or `=` (optional
# quotes/spaces), then the value up to the next whitespace, quote, or `&`.
_SENSITIVE_PATTERN = re.compile(
    r"(?i)(password|passwd|pwd|secret|token|bearer|api[_-]?key)"
    r"(\"?\s*[:=]\s*\"?)"
    r"([^\s\"'&]+)"
)


def redact_sensitive(
    logger: Any,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Redact common credential patterns from string values in the event dict.

    Defence in depth: nothing in this codebase deliberately logs a credential,
    but if a future caller logs an ogr2ogr command, a DSN, or a request URL
    that happens to contain `password=...`, this processor scrubs the value
    before the JSON/console renderer sees it.
    """
    for key, value in list(event_dict.items()):
        if isinstance(value, str) and _SENSITIVE_PATTERN.search(value):
            event_dict[key] = _SENSITIVE_PATTERN.sub(r"\1\2***REDACTED***", value)
    return event_dict


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
        # Last processor before the renderer — scrub credential patterns from
        # any string value (e.g. a DSN that leaked into a log line).
        redact_sensitive,
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
