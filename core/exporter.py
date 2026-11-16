"""Exports use the same suppressed aggregate rows as the dashboard and API."""
from __future__ import annotations

import json

from core.security import audit
from core.settings import now
from core.store import get_series


def export(ids, group_type=None, start=None, end=None, fmt="json") -> bytes:
    if fmt not in ("json", "csv"):
        raise ValueError("fmt must be json or csv")
    frame = get_series(ids, group_type, start, end)
    if fmt == "csv":
        safe = frame.copy()
        for col in safe.select_dtypes(include=["object", "str"]).columns:
            safe[col] = safe[col].map(lambda x: "'" + x if isinstance(x, str) and x.startswith(("=", "+", "-", "@", "\t", "\r")) else x)
        payload = safe.to_csv(index=False).encode("utf-8-sig")
    else:
        payload = json.dumps({"generated": now(), "rows": frame.to_dict("records")},
                             ensure_ascii=False, allow_nan=False, indent=2).encode("utf-8")
    audit("export", ids=list(ids), group_type=group_type, start=start, end=end, format=fmt, rows=len(frame))
    return payload
