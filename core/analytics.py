"""Calculations from complete observed aggregates; no embedded demo figures."""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.settings import DataUnavailable, config
from core.store import get_series


def _series(indicator):
    frame = get_series([indicator])
    frame = frame.loc[~frame["is_partial"].astype(bool)].sort_values("period")
    if frame.empty:
        raise DataUnavailable(f"No complete observations for {indicator}")
    if frame["period"].duplicated().any():
        raise DataUnavailable(f"Ambiguous total groups for {indicator}")
    return frame


def _latest(indicator):
    frame = _series(indicator)
    row = frame.iloc[-1]
    previous_period = str(int(row.period[:4]) - 1) + row.period[4:]
    prev = frame.loc[frame["period"] == previous_period, "value"]
    change = None
    if not prev.empty and prev.iloc[0] != 0:
        change = float(row.value - prev.iloc[0]) if row.unit == "%" else float((row.value / prev.iloc[0] - 1) * 100)
    value = round(float(row.value), 1) if row.unit.startswith("%") else int(row.value)
    return {"value": value, "change_pct": round(change, 1) if change is not None else None, "period": row.period, "source": row.source}


def get_kpis() -> dict:
    from core.alerts import get_alerts
    result = {key: _latest(key) for key in ("active_licences", "renewal_rate", "activity_signal")}
    monthly = _series("new_reg_total")
    full_years = [(year, group) for year, group in monthly.groupby(monthly["period"].str[:4])
                  if len(group) == 12 and group["frequency"].eq("M").all()]
    if not full_years:
        raise DataUnavailable("New-business KPI requires a complete calendar year")
    year, frame = full_years[-1]
    value = float(frame["value"].sum())
    prior = next((g for y, g in full_years if int(y) == int(year) - 1), None)
    fz = get_series(["new_reg_fz"], start=year, end=year)
    if len(fz) != 12 or fz["is_partial"].any():
        raise DataUnavailable("Free Zone share requires 12 complete months")
    result["new_businesses"] = {"value": value, "period": year,
        "change_pct": float((value / prior["value"].sum() - 1) * 100) if prior is not None and prior["value"].sum() else None,
        "fz_share_pct": float(fz["value"].sum() / value * 100) if value else 0,
        "source": "; ".join(sorted(frame["source"].unique()))}
    # Organiser annual issuance totals are authoritative for the annual headline;
    # the open-data monthly register has different coverage and must not replace them.
    annual_rows = get_series(["new_licences_annual"])
    annual_match = annual_rows.loc[annual_rows["period"] == year]
    if not annual_match.empty:
        value = float(annual_match.iloc[0]["value"] + fz["value"].sum())
        prev_year = str(int(year) - 1)
        prior_main = annual_rows.loc[annual_rows["period"] == prev_year]
        prior_fz = get_series(["new_reg_fz"], start=prev_year, end=prev_year)
        change = None
        if not prior_main.empty and len(prior_fz) == 12 and not prior_fz["is_partial"].any():
            previous_total = float(prior_main.iloc[0]["value"] + prior_fz["value"].sum())
            change = (value / previous_total - 1) * 100 if previous_total else None
        result["new_businesses"].update(value=value, change_pct=change,
            fz_share_pct=float(fz["value"].sum() / value * 100) if value else 0,
            source="DED annual + Free Zone organisers files; annual and monthly series have different coverage")
    result["activity_signal"]["note"] = "Licence-implied signal, not GDP or FDI"
    alerts = [a for a in get_alerts() if a["status"] == "open"]
    result["open_alerts"] = {"value": len(alerts), "by_severity": {s: sum(a["severity"] == s for a in alerts) for s in ("high", "medium", "low")}}
    return result


def get_forecast(indicator: str, recovery_start: int = 6, recovery_len: int = 6, depth_pct: int = 100):
    if indicator not in {"new_reg_mainland", "new_reg_fz", "new_reg_total"}:
        raise ValueError("Forecast supports registration indicators only")
    if not 0 <= recovery_start <= 36 or not 1 <= recovery_len <= 36 or not 0 <= depth_pct <= 150:
        raise ValueError("Invalid recovery parameters")
    settings = config("assumptions")
    if settings.get("forecast_method") == "kit":
        from core.kit_adapter import forecast
        return forecast(indicator, recovery_start, recovery_len, depth_pct)
    frame = _series(indicator)
    hist = frame.set_index("period")["value"]
    if len(hist) < 24 or not frame["frequency"].eq("M").all():
        raise DataUnavailable("Seasonal baseline requires 24 complete monthly observations")
    periods = pd.period_range(hist.index[0], hist.index[-1], freq="M").astype(str)
    if list(hist.index) != list(periods):
        raise DataUnavailable("Missing months: cannot fit a baseline across data gaps")
    normal = hist.iloc[-24:-12].groupby(hist.iloc[-24:-12].index.str[5:]).mean()
    recent = hist.iloc[-3:].mean()
    residual = hist.iloc[12:].to_numpy() - hist.iloc[:-12].to_numpy()
    scale = float(np.sqrt(np.mean(residual ** 2)))
    start = pd.Period(hist.index[-1], freq="M") + 1
    horizon = pd.period_range(start, settings["forecast_end"], freq="M")
    if not len(horizon):
        raise DataUnavailable("Forecast horizon is before the last observation")
    scenarios = {**settings["scenarios"], "custom": [recovery_start, recovery_len, depth_pct]}
    rows = []
    for scenario, (rs, rl, depth) in scenarios.items():
        for i, period in enumerate(horizon):
            target = float(normal[str(period)[5:]])
            progress = min(max((i - rs + 1) / rl, 0), 1)
            gap = (target - recent) * depth / 100
            mean = max(0, target - gap * (1 - progress))
            band = 1.28155 * scale * np.sqrt(1 + i / 12)
            rows.append({"period": str(period), "scenario": scenario, "mean": round(mean, 2),
                         "lo": round(max(0, mean - band), 2), "hi": round(mean + band, 2)})
    result = pd.DataFrame(rows)
    result.attrs["method"] = "Seasonal baseline scenarios; approximate 80% residual band, not a validated SARIMAX forecast"
    return result


def simulate_renewal(delta_pts: float) -> dict:
    if not np.isfinite(delta_pts) or not 0 <= delta_pts <= 3:
        raise ValueError("Renewal improvement must be between 0 and 3 percentage points")
    settings = config("assumptions")
    base, elasticity = settings.get("renewal_base"), settings.get("activity_elasticity")
    if settings.get("forecast_method") == "kit":
        from core.kit_adapter import annual, signal_parameters
        data = annual().loc[2025]
        base = float(data["Renewed Licenses"] / data["Renewal rate"])
        _, elasticity = signal_parameters()
    if base is None or elasticity is None:
        raise DataUnavailable("Verified renewal exposure and activity elasticity have not been loaded")
    active, rate, signal = (_latest(key)["value"] for key in ("active_licences", "renewal_rate", "activity_signal"))
    if active <= 0 or base < 0 or not np.isfinite([base, elasticity]).all():
        raise ValueError("Invalid simulation assumptions")
    applied = min(delta_pts, 100 - rate)
    retained = round(base * applied / 100)
    return {"businesses_retained": retained, "active_licences": round(active + retained),
            "activity_signal_pct": round(signal + retained / active * 100 * elasticity, 2),
            "assumptions": [f"Renewal exposure base: {base:,.0f}; improvement capped at 100% renewal",
                            f"Activity elasticity: {elasticity}; all other factors held constant",
                            "Scenario only; licence activity is not GDP or FDI"]}


def group_differences(dim: str) -> dict:
    if dim not in {"zone", "licence_type", "legal_form", "facility", "area", "activity"}:
        raise ValueError("Unknown group dimension")
    ind = "new_reg_fz" if dim == "facility" else "new_reg_total"
    frame = get_series([ind], dim, "2025-01", "2026-06")
    frame = frame[~frame["is_partial"].astype(bool)]
    rows = []
    for group, cells in frame.groupby("group"):
        first = cells[cells["period"].between("2025-01", "2025-06")]
        second = cells[cells["period"].between("2026-01", "2026-06")]
        # Do not compare an incomplete half-year with a complete one.
        if len(first) != 6 or len(second) != 6:
            continue
        a, b = float(first["value"].sum()), float(second["value"].sum())
        if not a:
            continue
        rows.append({"group": group, "H1 2025": a, "H1 2026": b, "change_pct": (b / a - 1) * 100})
    table = pd.DataFrame(rows, columns=["group", "H1 2025", "H1 2026", "change_pct"])
    total = table["H1 2026"].sum()
    table["share_2026_pct"] = table["H1 2026"] / total * 100 if total else 0.0
    table = table.sort_values("change_pct", ascending=False).reset_index(drop=True)
    finding = "Comparable complete half-years are not available."
    finding_ar = "لا تتوفر أنصاف سنوات كاملة قابلة للمقارنة."
    if not table.empty:
        leader = table.iloc[0]
        fell, n = int((table["change_pct"] < 0).sum()), len(table)
        if fell * 2 > n:  # most groups shrank: the top one is the most resilient, not "growing"
            verb = "still grew" if leader["change_pct"] >= 0 else "fell least"
            finding = (f"{fell} of {n} groups fell. Most resilient: {leader['group']}, which {verb} "
                       f"({leader['change_pct']:+.1f}% in H1 2026 versus H1 2025).")
            finding_ar = (f"تراجعت {fell} من أصل {n} فئات. الأكثر صموداً: {leader['group']} "
                          f"(‪{leader['change_pct']:+.1f}%‬ في النصف الأول 2026 مقارنة بالنصف الأول 2025).")
        else:
            finding = f"{leader['group']}: {leader['change_pct']:+.1f}% in H1 2026 versus H1 2025 (comparable observed groups)."
            finding_ar = f"{leader['group']}: ‪{leader['change_pct']:+.1f}%‬ في النصف الأول 2026 مقارنة بالنصف الأول 2025."
    return {"table": table, "finding_en": finding, "finding_ar": finding_ar,
            "mostly_shrinking": bool(not table.empty and (table["change_pct"] < 0).sum() * 2 > len(table))}
