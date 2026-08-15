"""Integration with the operating system file manager."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def reveal_in_file_manager(path: Path) -> None:
    """Open the containing folder, selecting the file when the OS allows it."""
    target = Path(path)
    folder = target if target.is_dir() else target.parent
    if not folder.exists():
        raise FileNotFoundError(folder)

    if sys.platform == "darwin":
        command = ["open", "-R", str(target)] if target.is_file() else ["open", str(folder)]
    elif os.name == "nt":
        command = (
            ["explorer", f"/select,{target}"] if target.is_file() else ["explorer", str(folder)]
        )
    else:
        command = ["xdg-open", str(folder)]

    logger.debug("Opening file manager: %s", command)
    # Windows Explorer returns exit code 1 even on success.
    subprocess.run(command, check=False)
