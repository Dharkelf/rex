"""Load and cache config/settings.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml


@lru_cache(maxsize=1)
def load_config() -> dict:
    path = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
    with path.open() as f:
        return yaml.safe_load(f)
