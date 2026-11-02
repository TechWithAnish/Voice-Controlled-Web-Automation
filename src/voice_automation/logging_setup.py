"""Logging configuration.

The previous version called ``logging.basicConfig`` at import time with a
hard-coded relative filename, which meant the log landed wherever the
process happened to start, grew without bound, and could not be reconfigured
by anything that imported the module.  Configuration now happens once,
explicitly, from the CLI, writes only when a path is requested, and rotates.
"""

from __future__ import annotations

import contextlib
import logging
import logging.handlers
from pathlib import Path

from .config import Settings

#: Third-party loggers that are far too chatty at INFO.
_NOISY = ("selenium", "urllib3", "WDM", "webdriver_manager", "comtypes")

_CONSOLE_FORMAT = "%(levelname)-8s %(message)s"
_FILE_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def configure_logging(settings: Settings, console: bool = True) -> Path | None:
    """Configure the root logger from ``settings``.

    Returns the resolved log-file path, or ``None`` when file logging is off.
    Safe to call more than once: existing handlers are replaced.
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        with contextlib.suppress(Exception):  # closing must never raise
            handler.close()

    root.setLevel(getattr(logging, settings.log_level, logging.INFO))

    if console:
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
        # The assistant narrates itself out loud; keep the console terse.
        stream.setLevel(max(root.level, logging.WARNING))
        root.addHandler(stream)

    path: Path | None = None
    if settings.log_file is not None:
        path = settings.log_file.expanduser()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                path,
                maxBytes=settings.log_max_bytes,
                backupCount=settings.log_backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(logging.Formatter(_FILE_FORMAT))
            file_handler.setLevel(root.level)
            root.addHandler(file_handler)
        except OSError as exc:
            root.addHandler(logging.NullHandler())
            logging.getLogger(__name__).warning(
                "Could not open log file %s (%s); continuing without file logging",
                path,
                exc,
            )
            path = None

    for name in _NOISY:
        logging.getLogger(name).setLevel(logging.WARNING)

    return path
