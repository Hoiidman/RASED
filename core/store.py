"""Validated aggregate store. No mock numbers are loaded by the real engine."""
from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from core.security import suppress
from core.settings import DataUnavailable, config, data_dir, read_json

COLUMNS = ["period", "frequency", "indicator", "group_type", "group", "value", "unit", "source", "is_partial"]
KEY = ["period", "frequency", "indicator", "group_type", "group"]
CATALOG_COLUMNS = ["id", "name_en", "name_ar", "unit", "frequency", "group_types", "source", "last_period"]


def validate(frame: pd.DataFrame) -> pd.DataFrame:
    missing = set(COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing standard columns: {sorted(missing)}")
    df = frame[COLUMNS + (["record_count"] if "record_count" in frame else [])].copy()
    if df.empty or df.isna().any().any():
        raise ValueError("Source is empty or contains missing cells")
    for col in set(COLUMNS) - {"value", "is_partial"}:
        df[col] = df[col].astype(str).str.strip()
        if (df[col] == "").any():
            raise ValueError(f"Blank {col}")
    df["value"] = pd.to_numeric(df["value"], errors="raise")
    if not np.isfinite(df["value"]).all():
        raise ValueError("Non-finite values")
    if "record_count" in df:
        df["record_count"] = pd.to_numeric(df["record_count"], errors="raise")
        if not np.isfinite(df["record_count"]).all() or (df["record_count"] < 0).any():
            raise ValueError("Invalid record counts")
    flags = df["is_partial"].astype(str).str.lower().map({"true": True, "false": False, "1": True, "0": False})
    if flags.isna().any():
        raise ValueError("is_partial must be boolean")
    df["is_partial"] = flags.astype(bool)
    today = datetime.now(ZoneInfo("Asia/Dubai"))
    for freq, pattern, current in [("M", r"\d{4}-(0[1-9]|1[0-2])", today.strftime("%Y-%m")),
                                   ("Y", r"\d{4}", today.strftime("%Y"))]:
        selected = df["frequency"] == freq
        periods = df.loc[selected, "period"]
        if not periods.map(lambda p: bool(re.fullmatch(pattern, p))).all() or (periods > current).any():
            raise ValueError("Invalid or future period")
        df.loc[selected & (df["period"] == current), "is_partial"] = True
    if not df["frequency"].isin(["M", "Y"]).all():
        raise ValueError("Only M and Y frequencies are supported")
    if df.duplicated(KEY).any():
        raise ValueError("Duplicate aggregate keys; resolve source overlap before ingestion")
    for _, cells in df.groupby("indicator"):
        if cells["unit"].nunique() != 1 or cells["frequency"].nunique() != 1:
            raise ValueError("Indicator must have one unit and frequency")
    nonnegative = df["unit"].isin(["registrations", "licences", "businesses", "records", "permits", "%"])
    if (df.loc[nonnegative, "value"] < 0).any() or (df.loc[df["unit"] == "%", "value"] > 100).any():
        raise ValueError("Counts or percentages out of range")
    return df.sort_values(KEY).reset_index(drop=True)


def load_table() -> pd.DataFrame:
    manifest = read_json(data_dir() / "cache" / "manifest.json", {})
    frames = []
    for item in config("sources")["sources"]:
        file = manifest.get(item["id"], f"snapshot/{item['id']}.json")
        path = (data_dir() / file).resolve()
        if not path.is_relative_to(data_dir().resolve()):
            raise ValueError("Snapshot path escapes data directory")
        if path.exists():
            frames.append(pd.DataFrame(read_json(path, [])))
    if not frames:
        return pd.DataFrame(columns=COLUMNS)
    return validate(pd.concat(frames, ignore_index=True))


def get_series(ids, group_type=None, start=None, end=None) -> pd.DataFrame:
    df = load_table()
    df = df[df["indicator"].isin(list(ids)) & (df["group_type"] == (group_type or "total"))]
    if start and end and start > end:
        raise ValueError("start must not be after end")
    if start:
        df = df[df["period"] >= start]
    if end:
        # Year-only upper bounds include every month of that year.
        df = df[df["period"] <= (end + "-12" if len(end) == 4 else end)]
    return suppress(df)[COLUMNS].reset_index(drop=True)


def get_catalog() -> pd.DataFrame:
    df = suppress(load_table())
    labels = config("indicators")
    rows = []
    for ind, cells in df.groupby("indicator"):
        meta = labels.get(ind, {})
        complete = cells.loc[~cells["is_partial"].astype(bool), "period"]
        rows.append({"id": ind, "name_en": meta.get("name_en", ind.replace("_", " ")),
                     "name_ar": meta.get("name_ar", ""), "unit": cells["unit"].iloc[0],
                     "frequency": cells["frequency"].iloc[0], "group_types": ",".join(sorted(cells["group_type"].unique())),
                     "source": "; ".join(sorted(cells["source"].unique())),
                     "last_period": complete.max() if not complete.empty else cells["period"].max()})
    return pd.DataFrame(rows, columns=CATALOG_COLUMNS)


if __name__ == "__main__":
    print(get_catalog().to_string(index=False))
    if load_table().empty:
        print("No source data loaded. Add the kit, configure sources.yaml, then run python -m core.sync.")
