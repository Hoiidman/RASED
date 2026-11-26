"""Build data/reference/names_ar.csv: official Arabic names for the areas, activities, licence types and
legal forms the app shows. Run offline, by hand:

    python scripts/build_names_ar.py

Names come from DED's public register on the Ajman Open Data portal, which publishes each field in English
and Arabic (areaen/areaar, activitiyen/activitiyar, ...). The script asks the portal for grouped name pairs
only (no licence numbers, trade names or other record-level fields) and keeps the most common Arabic
spelling for each English name. The app matches names with the same normaliser as build_competitors.py.
"""
from __future__ import annotations

import io
import re
from datetime import date
from pathlib import Path

import httpx
import pandas as pd

from build_competitors import ALIASES, BASE, norm

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "reference" / "names_ar.csv"
PAIRS = [  # (kind, dataset, english field, arabic field)
    ("area", "license-in-ajman-area", "areaen", "areaar"),
    ("activity", "license-in-ajman-activities", "activitiyen", "activitiyar"),
    ("licence_type", "license-in-ajman-area", "licensetypeen", "licensetypear"),
    ("legal_form", "license-in-ajman-area", "legalformen", "legalformar"),
]


def grouped(dataset: str, en: str, ar: str) -> pd.DataFrame:
    r = httpx.get(f"{BASE}/{dataset}/exports/csv", timeout=120,
                  params={"select": f"{en},{ar},count(*) as n", "group_by": f"{en},{ar}", "delimiter": ","},
                  headers={"User-Agent": "RASED/1.0 (aggregate build)"})
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.content.decode("utf-8-sig"))).dropna()
    return d.rename(columns={en: "en", ar: "ar"})


def tidy_ar(s: str) -> str:
    s = re.sub(r"\s+", " ", str(s)).strip()
    return re.sub(r"(?<=[؀-ۿ])(\d+)$", r" \1", s)  # 'الجرف2' -> 'الجرف 2'


def main():
    rows = []
    for kind, ds, en, ar in PAIRS:
        d = grouped(ds, en, ar)
        d["key"] = d["en"].map(norm).replace(ALIASES)
        best = d.sort_values("n", ascending=False).drop_duplicates("key")
        for _, r in best.iterrows():
            if r["key"]:
                rows.append({"kind": kind, "key": r["key"], "en": re.sub(r"\s+", " ", r["en"]).strip(),
                             "ar": tidy_ar(r["ar"])})
    out = pd.DataFrame(rows)
    # activities: only those the app shows (the register lists over 1,500)
    kit_acts = pd.read_csv(ROOT / "kit/data/by_activity.csv", nrows=0, encoding="utf-8").columns[1:]
    keep = {ALIASES.get(norm(a), norm(a)) for a in kit_acts}
    out = out[(out["kind"] != "activity") | out["key"].isin(keep)]
    out["built"] = date.today().isoformat()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False, encoding="utf-8")
    print(out.groupby("kind").size().to_string(), f"\n-> {OUT}")


if __name__ == "__main__":
    main()
