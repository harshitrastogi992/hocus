from __future__ import annotations

import os
import sys
from pathlib import Path

from platformdirs import user_cache_dir, user_config_dir

APP_NAME = "Hocus"


def models_dir() -> Path:
    if override := os.environ.get("HOCUS_MODELS_DIR"):
        return Path(override)
    bundled = Path(getattr(sys, "_MEIPASS", "")) / "models"
    if getattr(sys, "frozen", False) and bundled.is_dir():
        return bundled
    return Path(user_cache_dir(APP_NAME, appauthor=False)) / "models"


def config_file() -> Path:
    if override := os.environ.get("HOCUS_CONFIG"):
        return Path(override)
    return Path(user_config_dir(APP_NAME, appauthor=False)) / "settings.json"
