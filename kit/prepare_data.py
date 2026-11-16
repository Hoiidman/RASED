"""
prepare_data.py — builds the clean monthly dataset the notebook uses.

Inputs  (data/raw/, extracted from Ajman DED open data, ajmanded.ae/en/open-data/ajded-open-data):
  new_licences_by_type_2023_2026.csv        issuance records, Jan 2023 – Jun 2026
  new_licences_by_type_snapshot_2010_2024.csv  licences on the register by start month (long history)
  new_licences_by_area_2023_2026.csv
  new_licences_by_activity_2024_2026.csv
  permits_by_type_2023_2026.csv

Output (data/):
  ajman_monthly.csv   one row per month, 2010-01 … 2026-06, with gaps left as NaN
"""
from pathlib import Path
import numpy as np
import pandas as pd
from hijridate import Hijri, Gregorian

RAW = Path(__file__).parent / "data" / "raw"
OUT = Path(__file__).parent / "data"
TYPES = ["Professional", "Commercial", "Industrial", "Other"]

# Months missing from DED's published files (zero rows = not published, NOT zero licences)
GAPS = ["2022-07", "2022-08", "2022-09", "2022-10", "2022-11", "2022-12", "2024-11", "2024-12"]
PARTIAL = ["2024-10"]  # DED's Jul–Dec 2024 files were published 20 Oct 2024, so October is incomplete


def load(name):
    df = pd.read_csv(RAW / name)
    df["month"] = pd.PeriodIndex(df["month"], freq="M")
    return df.set_index("month")


def consistency_checks(iss, area, act):
    t_type = iss[TYPES].sum(axis=1)
    t_area = area.sum(axis=1)
    t_act = act.sum(axis=1)
    bad_area = (t_type.loc[t_area.index] != t_area).sum()
    bad_act = (t_type.loc[t_act.index] != t_act).sum()
    print(f"Check: by-type vs by-area monthly totals mismatches: {bad_area}")
    print(f"Check: by-type vs by-activity monthly totals mismatches: {bad_act}")
    q1_26 = t_type.loc["2026-01":"2026-03"].sum()
    h1_25 = t_type.loc["2025-01":"2025-06"].sum()
    h1_24 = t_type.loc["2024-01":"2024-06"].sum()
    print(f"Check: Q1 2026 new licences = {q1_26} (DED press release: 1,617)")
    print(f"Check: H1 2025 vs H1 2024 = {h1_25} vs {h1_24} ({h1_25 / h1_24 - 1:+.1%}; DED reported +24%)")


def ramadan_eid_features(months):
    """Share of each month's days that fall in Ramadan, and whether Eid holidays fall in the month.
    Uses the Umm al-Qura calendar (hijridate); official UAE dates can differ by a day."""
    rows = []
    for p in months:
        days = pd.date_range(p.start_time, p.end_time, freq="D")
        hij = [Gregorian(d.year, d.month, d.day).to_hijri() for d in days]
        ram = np.mean([h.month == 9 for h in hij])
        eid_fitr = any(h.month == 10 and h.day <= 3 for h in hij)
        eid_adha = any(h.month == 12 and 9 <= h.day <= 12 for h in hij)
        rows.append((p, ram, int(eid_fitr), int(eid_adha)))
    return pd.DataFrame(rows, columns=["month", "ramadan_share", "eid_fitr", "eid_adha"]).set_index("month")


def main():
    iss = load("new_licences_by_type_2023_2026.csv")
    snap = load("new_licences_by_type_snapshot_2010_2024.csv")
    area = load("new_licences_by_area_2023_2026.csv")
    act = load("new_licences_by_activity_2024_2026.csv")
    permits = load("permits_by_type_2023_2026.csv")

    gaps = pd.PeriodIndex(GAPS, freq="M")
    consistency_checks(iss.drop(gaps, errors="ignore"), area.drop(gaps, errors="ignore"), act.drop(gaps, errors="ignore"))

    # Splice: long history from the register snapshot (2010-01 … 2022-12), issuance records from 2023-01.
    idx = pd.period_range("2010-01", "2026-06", freq="M")
    df = pd.DataFrame(index=idx)
    df.index.name = "month"
    for t in TYPES:
        df[t.lower()] = np.nan
        df.loc[snap.index[snap.index < "2023-01"], t.lower()] = snap.loc[snap.index < "2023-01", t]
        df.loc[iss.index, t.lower()] = iss[t]
    df["source"] = np.where(df.index < pd.Period("2023-01", "M"), "register_snapshot", "issuance_records")
    df.loc[gaps, [t.lower() for t in TYPES]] = np.nan
    df["is_gap"] = df.index.isin(gaps).astype(int)
    df["is_partial"] = df.index.isin(pd.PeriodIndex(PARTIAL, freq="M")).astype(int)
    df.loc[df["is_partial"] == 1, [t.lower() for t in TYPES]] = np.nan  # don't train on a part-month
    df["total"] = df[[t.lower() for t in TYPES]].sum(axis=1, min_count=4)

    # Permits (2023+)
    p = permits.drop(gaps, errors="ignore").sum(axis=1)
    df["permits"] = np.nan
    df.loc[p.index, "permits"] = p
    df.loc[gaps, "permits"] = np.nan
    df.loc[pd.PeriodIndex(PARTIAL, freq="M"), "permits"] = np.nan

    # Calendar & shock features
    df = df.join(ramadan_eid_features(df.index))
    df["covid"] = ((df.index >= pd.Period("2020-04", "M")) & (df.index <= pd.Period("2020-06", "M"))).astype(int)
    df["disruption"] = (df.index >= pd.Period("2026-03", "M")).astype(int)  # regional disruption from 28 Feb 2026
    df["month_num"] = df.index.month

    out = df.reset_index()
    out["month"] = out["month"].astype(str)
    out.to_csv(OUT / "ajman_monthly.csv", index=False)
    print(f"Wrote data/ajman_monthly.csv: {len(out)} months, {int(out['total'].isna().sum())} missing")

    # Tidy copies of the breakdowns (gap months removed) for the dashboard
    for name, frame in [("by_area", area), ("by_activity", act), ("permits_by_type", permits)]:
        f = frame.drop(gaps, errors="ignore").copy()
        f.index = f.index.astype(str)
        f.to_csv(OUT / f"{name}.csv")


if __name__ == "__main__":
    main()
