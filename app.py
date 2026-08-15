"""Entry point for Transcriber.

Usage:
    python app.py
"""

from __future__ import annotations

import logging
import sys


def main() -> int:
    from transcriber.logging_setup import setup_logging

    setup_logging()
    logger = logging.getLogger("transcriber")

    from transcriber.i18n import t

    try:
        from transcriber.ui.main_window import run
    except ImportError as exc:  # Tkinter missing on some Linux distributions
        logger.exception("Could not import the interface")
        print(t("error.no_gui", detail=exc), file=sys.stderr)
        return 1

    try:
        return run()
    except Exception:
        logger.exception("Fatal application error")
        print(t("error.fatal"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
