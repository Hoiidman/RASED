"""Adapters for the supplied kit without importing day_analysis's plotting side effects."""
from functools import lru_cache
from hashlib import sha256

import numpy as np
import pandas as pd

from core.settings import ROOT, config
from kit import forecast_kit as kit


def kit_paths():
    return [ROOT / "kit/data" / p for p in ["ajman_monthly.csv", "by_activity.csv", "by_area.csv",
            "organisers/ded_annual.xlsx", "organisers/fz_monthly.xlsx"]]


def fingerprint():
    digest = sha256()
    for path in kit_paths():
        digest.update(path.read_bytes())
    return digest.hexdigest()


def annual():
    frame = pd.read_excel(ROOT / "kit/data/organisers/ded_annual.xlsx").replace("-", np.nan)
    frame = frame.apply(pd.to_numeric).set_index("Year")
    frame["Lapsed"] = frame["Active Licenses"].shift(1) + frame["New Licenses"] - frame["Cancelled Licenses"] - frame["Active Licenses"]
    frame["Renewal rate"] = frame["Renewed Licenses"] / (frame["Renewed Licenses"] + frame["Lapsed"])
    return frame


def signal_parameters():
    a = annual()
    train = a.loc[2017:2024].dropna(subset=["GDP", "Active Licenses", "Permits"])
    fits = {x: np.polyfit(np.log(train[x]), np.log(train["GDP"]), 1) for x in ("Active Licenses", "Permits")}
    estimates = [np.exp(slope * np.log(a.loc[2025, x]) + intercept) for x, (slope, intercept) in fits.items()]
    return float((np.mean(estimates) / a.loc[2024, "GDP"] - 1) * 100), float(fits["Active Licenses"][0])


def aggregates():
    rows = []
    def add(period, indicator, value, source, group_type="total", group="Ajman", unit="registrations", partial=False, freq="M"):
        if pd.notna(value):
            rows.append(dict(period=str(period), frequency=freq, indicator=indicator, group_type=group_type,
                             group=group, value=float(value), unit=unit, source=source, is_partial=bool(partial)))
    main = pd.read_csv(ROOT / "kit/data/ajman_monthly.csv").set_index("month")
    fz = pd.read_excel(ROOT / "kit/data/organisers/fz_monthly.xlsx")
    fz.index = pd.to_datetime(fz["Month"]).dt.to_period("M").astype(str)
    ded, zone = "Ajman DED open data (kit aggregate; mainland)", "Ajman Free Zone (organisers file)"
    for period, row in main.iterrows():
        if row.is_gap or pd.isna(row.total):
            continue
        source = ded + "; " + row.source
        add(period, "new_reg_mainland", row.total, source, partial=row.is_partial)
        add(period, "new_reg_total", row.total, source, "zone", "Mainland", partial=row.is_partial)
        for kind in ["professional", "commercial", "industrial", "other"]:
            add(period, "new_reg_total", row[kind], source, "licence_type", "Mainland: " + kind.title(), partial=row.is_partial)
    for period, row in fz.iterrows():
        partial = period == "2026-11"
        add(period, "new_reg_fz", row["Company records"], zone, partial=partial)
        add(period, "new_reg_total", row["Company records"], zone, "zone", "Free Zone", partial=partial)
        add(period, "virtual_office_share", row["Facility: Virtual Office"] / row["Company records"] * 100,
            zone, group="Free Zone", unit="%", partial=partial)
        for col in fz.columns:
            for prefix, dim in [("Facility: ", "facility"), ("License: ", "licence_type"), ("Legal form: ", "legal_form")]:
                if col.startswith(prefix):
                    label = col.removeprefix(prefix)
                    if dim != "facility":
                        label = "Free Zone: " + label
                    add(period, "new_reg_fz" if dim == "facility" else "new_reg_total", row[col], zone,
                        dim, label, partial=partial)
        if period in main.index and pd.notna(main.loc[period, "total"]) and not main.loc[period, "is_gap"]:
            add(period, "new_reg_total", row["Company records"] + main.loc[period, "total"], ded + " + " + zone,
                partial=partial or main.loc[period, "is_partial"])
    for file, dim in [("by_activity.csv", "activity"), ("by_area.csv", "area")]:
        table = pd.read_csv(ROOT / "kit/data" / file).set_index("month")
        for period, row in table.iterrows():
            if period not in main.index or main.loc[period, "is_gap"]:
                continue
            for label, value in row.items():
                add(period, "new_reg_total", value, ded + "; breakdown excludes Free Zone", dim, label,
                    partial=main.loc[period, "is_partial"])
    a = annual()
    for year, row in a.iterrows():
        for col, ind, unit in [("Active Licenses", "active_licences", "licences"),
                               ("Cancelled Licenses", "cancelled_licences", "licences"),
                               ("New Licenses", "new_licences_annual", "licences"),
                               ("Permits", "permits_annual", "permits")]:
            add(year, ind, row[col], "DED annual (organisers file)", unit=unit, freq="Y")
        if pd.notna(row["Renewal rate"]) and 0 <= row["Renewal rate"] <= 1:
            add(year, "renewal_rate", row["Renewal rate"] * 100, "Derived stock-flow; DED annual", unit="%", freq="Y")
    signal, _ = signal_parameters()
    add(2025, "activity_signal", signal, "Kit log-log licence/permit model, 2017-2024; signal, not GDP", unit="% change", freq="Y")
    return pd.DataFrame(rows)


@lru_cache(maxsize=4)
def _fit(indicator, version):
    if indicator == "new_reg_mainland":
        frame = kit.load_monthly(ROOT / "kit/data/ajman_monthly.csv")
        frame.loc[frame["is_partial"].astype(bool), "total"] = np.nan
        frame = frame.loc["2010-01":frame["total"].last_valid_index()]
        cols = [c for c in kit.EXOG_DEFAULT if frame[c].nunique() > 1]
        model = kit.fit_sarimax(frame["total"], frame[cols])
        future = kit.extend_index(frame, config("assumptions")["forecast_end"])
        return model, future, cols, frame.index[-1]
    from hijridate import Gregorian
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    raw = pd.read_excel(ROOT / "kit/data/organisers/fz_monthly.xlsx")
    values = pd.Series(raw["Company records"].values, index=pd.PeriodIndex(raw["Month"], freq="M"), dtype=float)
    # Drop the partial November row before fitting: avoids shifting forecast dates by a month.
    values = values.loc[:"2026-10"]
    idx = pd.period_range(values.index[0], config("assumptions")["forecast_end"], freq="M")
    shares = []
    for p in idx:
        days = pd.date_range(p.start_time, p.end_time, freq="D")
        shares.append(np.mean([Gregorian(d.year, d.month, d.day).to_hijri().month == 9 for d in days]))
    future = pd.DataFrame({"ramadan_share": shares, "disruption": (idx >= pd.Period("2026-03", "M")).astype(float)}, index=idx)
    cols = ["ramadan_share", "disruption"]
    model = SARIMAX(np.log(values), exog=future.loc[values.index], order=(1, 1, 0), trend="n").fit(disp=False)
    return model, future, cols, values.index[-1]


def forecast(indicator, recovery_start, recovery_len, depth_pct):
    if indicator == "new_reg_total":
        main = forecast("new_reg_mainland", recovery_start, recovery_len, depth_pct)
        fz = forecast("new_reg_fz", recovery_start, recovery_len, depth_pct)
        from core.store import get_series
        observed = get_series(["new_reg_fz"])
        observed = observed.loc[~observed["is_partial"]].set_index("period")["value"]
        parts = []
        for scenario, group in main.groupby("scenario"):
            other = fz.loc[fz["scenario"] == scenario].set_index("period")
            group = group.copy()
            for col in ["mean", "lo", "hi"]:
                group[col] += group["period"].map(lambda p: float(other.loc[p, col]) if p in other.index else float(observed[p]))
            parts.append(group)
        # Sum of marginal bounds is a conservative scenario envelope, not an independent joint CI.
        result = pd.concat(parts, ignore_index=True)
        result.attrs["method"] = "Combined kit scenarios; summed marginal uncertainty envelope"
        return result
    model, future, cols, last = _fit(indicator, fingerprint())
    horizon = future.index[future.index > last]
    scenarios = {**config("assumptions")["scenarios"], "custom": [recovery_start, recovery_len, depth_pct]}
    parts = []
    for label, (start, length, depth) in scenarios.items():
        exog = future.loc[horizon, cols].copy()
        progress = np.clip((np.arange(len(horizon)) - start + 1) / length, 0, 1)
        exog["disruption"] = (1 - progress) * depth / 100
        prediction = kit.predict_sarimax(model, exog[cols].astype(float), horizon)
        prediction["period"], prediction["scenario"] = horizon.astype(str), label
        parts.append(prediction.reset_index(drop=True))
    result = pd.concat(parts, ignore_index=True)[["period", "scenario", "mean", "lo", "hi"]]
    if not np.isfinite(result[["mean", "lo", "hi"]]).all().all():
        raise ValueError("Model returned invalid forecast values")
    result.attrs["method"] = "Supplied kit SARIMAX; partial months excluded; scenario assumptions apply"
    return result
