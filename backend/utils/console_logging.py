"""Send selected app log lines to the process console (stderr)."""

from __future__ import annotations

import logging
import sys

_done = False


def attach_api_loggers_to_console() -> None:
    """Wire important app loggers to stderr so lines show in the terminal."""
    global _done
    if _done:
        return
    _done = True

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.INFO)
    handler.setFormatter(fmt)

    for name in ("api.inbound", "planner.airports", "planner.routes"):
        log = logging.getLogger(name)
        log.setLevel(logging.INFO)
        log.handlers.clear()
        log.addHandler(handler)
        log.propagate = False
