"""Read configured sources only during sync; never during dashboard reads."""
from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path

import httpx
import pandas as pd

from core.settings import ROOT
from core.store import validate


def fetch(source: dict) -> tuple[pd.DataFrame, str]:
    kind = source.get("kind", "local_file")
    if kind == "forecast_kit":
        from core.kit_adapter import aggregates, fingerprint
        return validate(aggregates()), fingerprint()
    if kind == "local_file":
        path = Path(source["path"])
        if not path.is_absolute():
            path = ROOT / path
        raw = path.read_bytes()
        fmt = source.get("format", path.suffix.lstrip("."))
    elif kind == "http":
        url = source["url"]
        if not url.startswith("https://"):
            raise ValueError("Remote sources require an explicitly configured HTTPS endpoint")
        response = httpx.get(url, timeout=5, follow_redirects=False,
                             headers={"User-Agent": "RASED/1.0 (aggregate data sync)"})
        response.raise_for_status()
        raw, fmt = response.content, source.get("format", "json")
    else:
        raise ValueError(f"Unknown connector: {kind}")
    if fmt == "csv":
        df = pd.read_csv(BytesIO(raw), dtype={"period": str})
    elif fmt in ("xlsx", "xls"):
        df = pd.read_excel(BytesIO(raw), sheet_name=source.get("sheet", 0), dtype={"period": str})
    elif fmt == "json":
        import json
        records = json.loads(raw)
        for key in source.get("records_path", []):
            records = records[key]
        df = pd.DataFrame(records)
    else:
        raise ValueError(f"Unsupported source format: {fmt}")
    df = df.rename(columns=source.get("column_map", {}))
    for key, value in source.get("defaults", {}).items():
        if key not in df:
            df[key] = value
    return validate(df), sha256(raw).hexdigest()
