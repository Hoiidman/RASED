"""Aggregate suppression and append-only audit trail. API authentication is in api/main.py."""
from __future__ import annotations

import json
from threading import RLock

from core.settings import data_dir, now

LOCK = RLock()


def suppress(frame):
    """Drop small count cells, including zero; never interpret a percentage as a count."""
    count = frame["unit"].isin(["registrations", "licences", "businesses", "records", "permits"])
    safe = frame.loc[~(count & (frame["value"] < 5))].copy()
    if "record_count" in safe:
        safe = safe.loc[safe["record_count"] >= 5]
    return safe


def audit(action: str, user: str = "local", **details):
    entry = {"time": now(), "user": user, "action": action, **details}
    with LOCK:
        path = data_dir() / "audit.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, allow_nan=False) + "\n")
