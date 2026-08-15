"""Where Whisper models live on disk, and whether one is already there.

Plain filesystem checks: importing ``huggingface_hub`` just to answer "is this
downloaded?" would slow the window down and drag in a heavy dependency chain.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_TEMPLATE = "models--Systran--faster-whisper-{model}"
WEIGHTS_FILENAME = "model.bin"


def hub_cache_dir() -> Path:
    """Hugging Face hub cache, honouring the usual environment overrides."""
    for variable in ("HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE"):
        value = os.environ.get(variable)
        if value:
            return Path(value).expanduser()
    home = os.environ.get("HF_HOME")
    if home:
        return Path(home).expanduser() / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def model_dir(model_size: str) -> Path:
    return hub_cache_dir() / REPO_TEMPLATE.format(model=model_size)


def is_model_cached(model_size: str) -> bool:
    """True when the weights are already on disk and no download is needed.

    A local path typed by the user counts as cached: nothing to fetch.
    """
    candidate = Path(model_size).expanduser()
    if candidate.is_dir():
        return True

    snapshots = model_dir(model_size) / "snapshots"
    if not snapshots.is_dir():
        return False
    return any(
        (snapshot / WEIGHTS_FILENAME).exists()
        for snapshot in snapshots.iterdir()
        if snapshot.is_dir()
    )
