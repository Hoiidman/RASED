"""Build data/reference/competitors.csv from the public Ajman Open Data register. Run offline, by hand:

    python scripts/build_competitors.py

Two public DED datasets hold activity and area separately, so they are linked by licence number here,
in memory only. The output keeps counts per activity x area (groups under 5 removed) and the most common
licence type per activity. No licence numbers, trade names or other record-level fields are written,
and the app never downloads record-level data.
"""
from __future__ import annotations

import io
import re
from datetime import date
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "reference" / "competitors.csv"
BASE = "https://data.ajman.ae/api/explore/v2.1/catalog/datasets"
MIN_CELL = 5
# spelling differences in the register (normalised form -> the kit's normalised form)
ALIASES = {"retaisaleofwomenreadymadeclothes": "retailsaleofwomenreadymadeclothes"}


def norm(s) -> str:
    """'Jurf Industrial Zone1', 'Jurf Industrial 1' and 'jurf industrial  1' are the same area."""
    return re.sub(r"[^a-z0-9]", "", str(s).lower().replace("zone", ""))


def export(dataset: str, fields: str) -> pd.DataFrame:
    r = httpx.get(f"{BASE}/{dataset}/exports/csv", params={"select": fields, "delimiter": ","}, timeout=120,
                  headers={"User-Agent": "RASED/1.0 (aggregate build)"})
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.content.decode("utf-8-sig")))


def main():
    area = export("license-in-ajman-area", "licensenumber,areaen")
    act = export("license-in-ajman-activities", "licensenumber,activitiyen,licensetypeen,startdate")
    through = str(act["startdate"].max())[:7]

    # display names: the kit's spelling where one exists, else the register's most common spelling
    kit_areas = pd.read_csv(ROOT / "kit/data/by_area.csv", nrows=0).columns[1:]
    kit_acts = pd.read_csv(ROOT / "kit/data/by_activity.csv", nrows=0, encoding="utf-8").columns[1:]
    area = area.dropna(subset=["areaen"])  # licences with no area recorded can't be placed
    area["k"] = area["areaen"].map(norm)
    act["k"] = act["activitiyen"].map(norm).replace(ALIASES)
    area_name = {norm(a): a for a in kit_areas if a not in ("Unknown", "Other")}
    act_name = {norm(a): a for a in kit_acts if a != "Other"}
    for k, s in area.dropna(subset=["areaen"]).groupby("k")["areaen"]:
        name = re.sub(r"\s+", " ", s.mode().iat[0]).strip()
        area_name.setdefault(k, re.sub(r"(?<=[A-Za-z])(\d+)$", r" \1", name))  # 'Jurf2' -> 'Jurf 2'

    act = act[act["k"].isin(act_name)]  # the activities the app offers
    joined = act.merge(area.drop_duplicates("licensenumber")[["licensenumber", "k"]].rename(columns={"k": "ak"}),
                       on="licensenumber", how="left")
    joined = joined.dropna(subset=["ak"])
    joined = joined[joined["ak"] != ""]

    counts = (joined.groupby(["k", "ak"]).size().rename("licences").reset_index())
    counts = counts[counts["licences"] >= MIN_CELL]
    counts["activity"] = counts["k"].map(act_name)
    counts["area"] = counts["ak"].map(area_name)
    totals = act.groupby("k").size().rename("licences").reset_index()
    totals = totals[totals["licences"] >= MIN_CELL]
    totals["activity"], totals["area"] = totals["k"].map(act_name), "All Ajman"
    ltype = act.groupby("k")["licensetypeen"].agg(lambda s: s.mode().iat[0])
    lshare = act.groupby("k")["licensetypeen"].agg(lambda s: round(float((s == s.mode().iat[0]).mean()) * 100))

    out = pd.concat([totals, counts], ignore_index=True)
    out["licence_type"] = out["k"].map(ltype)
    out["licence_type_share_pct"] = out["k"].map(lshare)
    out["register_through"] = through
    out["built"] = date.today().isoformat()
    out = out[["activity", "area", "licences", "licence_type", "licence_type_share_pct", "register_through", "built"]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.sort_values(["activity", "licences"], ascending=[True, False]).to_csv(OUT, index=False, encoding="utf-8")
    print(f"{len(out)} rows, {out['activity'].nunique()} activities, register through {through} -> {OUT}")
    missing = sorted(set(act_name.values()) - set(out["activity"]))
    if missing:
        print("No register match for:", missing)


if __name__ == "__main__":
    main()
