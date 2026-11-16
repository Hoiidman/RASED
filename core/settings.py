"""Paths, configuration and atomic runtime state shared by the engine."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

import yaml

ROOT = Path(__file__).resolve().parents[1]


def data_dir() -> Path:
    return Path(os.getenv("RASED_DATA_DIR", str(ROOT / "data")))


def config(name: str):
    root = Path(os.getenv("RASED_CONFIG_DIR", str(ROOT / "config")))
    with (root / f"{name}.yaml").open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
        json.dump(value, f, ensure_ascii=False, allow_nan=False)
        temp = Path(f.name)
    temp.replace(path)


class DataUnavailable(ValueError):
    """Required source data or a validated model is not loaded."""
