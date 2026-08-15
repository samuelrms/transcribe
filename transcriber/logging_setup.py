"""Central logging setup: rotating file plus terminal."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from .config import LOG_FILENAME
from .paths import log_dir

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_MAX_BYTES = 1_000_000
_BACKUPS = 2


def setup_logging(level: int = logging.INFO) -> Path:
    """Install the log handlers and return the log file path.

    Idempotent: calling it twice does not duplicate handlers.
    """
    directory = log_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        directory = Path.home()
    log_path = directory / LOG_FILENAME
    root = logging.getLogger()

    if getattr(root, "_app_logging_configured", False):
        return log_path

    root.setLevel(level)
    formatter = logging.Formatter(_FORMAT)

    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=_MAX_BYTES, backupCount=_BACKUPS, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # Read-only directory (e.g. an .exe under Program Files): console only.
        pass

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    # Download libraries are very noisy at DEBUG level.
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    root._app_logging_configured = True  # type: ignore[attr-defined]
    logging.getLogger(__name__).info("Logging to %s", log_path)
    return log_path
