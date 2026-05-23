"""Centralised logging configuration."""

from __future__ import annotations

import logging
import os

import yaml

from src.utils.paths import logs_dir, project_root

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return

    settings_path = project_root() / "config" / "settings.yaml"
    with settings_path.open() as f:
        cfg = yaml.safe_load(f)

    level_str = os.environ.get("LOG_LEVEL", cfg["logging"]["level"])
    level = getattr(logging, level_str.upper(), logging.INFO)
    fmt = cfg["logging"]["format"]

    logs_dir().mkdir(parents=True, exist_ok=True)
    log_file = logs_dir() / "rex.log"

    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    _configured = True
