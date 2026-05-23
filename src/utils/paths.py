"""Repository pattern for all filesystem paths derived from config/settings.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SETTINGS_PATH = _PROJECT_ROOT / "config" / "settings.yaml"


def _load_settings() -> dict:
    with _SETTINGS_PATH.open() as f:
        return yaml.safe_load(f)


def project_root() -> Path:
    return _PROJECT_ROOT


def raw_dir() -> Path:
    cfg = _load_settings()
    p = _PROJECT_ROOT / cfg["data"]["raw_dir"]
    p.mkdir(parents=True, exist_ok=True)
    return p


def processed_dir() -> Path:
    cfg = _load_settings()
    p = _PROJECT_ROOT / cfg["data"]["processed_dir"]
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    cfg = _load_settings()
    p = _PROJECT_ROOT / cfg["data"]["logs_dir"]
    p.mkdir(parents=True, exist_ok=True)
    return p


def raw_parquet(symbol: str) -> Path:
    safe = symbol.replace("^", "").replace("/", "-")
    return raw_dir() / f"{safe}_1h.parquet"


def feature_matrix_path() -> Path:
    return processed_dir() / "feature_matrix.parquet"


def regimes_path() -> Path:
    return processed_dir() / "regimes.parquet"


def signal_log_path() -> Path:
    return logs_dir() / "signals.log"
