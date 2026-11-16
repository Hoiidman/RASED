"""Deterministic alerts from complete observed series, with persistent acknowledgements."""
from __future__ import annotations

from hashlib import sha256

import numpy as np
import pandas as pd

from core.security import LOCK, audit, suppress
from core.settings import config, data_dir, now, read_json, write_json
from core.store import load_table


def _factors(period):
    return [{"text": e["name"] + " (possible context; analyst review required)",
             "source": e["source"], "date": e["start"]}
            for e in config("events") if e["start"][:len(period)] <= period
            and (not e.get("end") or e["end"][:len(period)] >= period)]


def get_alerts(severity=None) -> list[dict]:
    if severity not in (None, "high", "medium", "low"):
        raise ValueError("Unknown severity")
    frame = suppress(load_table())
    frame = frame.loc[~frame["is_partial"].astype(bool)]
    acknowledged = read_json(data_dir() / "cache/acknowledged.json", {})
    playbook, out = config("playbook"), []

    def add(ind, group, period, rule, actual, expected, message, level, group_type="total"):
        key = "|".join([ind, group_type, group, period, rule])
        alert_id = "AL-" + sha256(key.encode()).hexdigest()[:12]
        out.append({"id": alert_id, "indicator": ind, "group": group, "period": period,
                    "what_happened": message, "expected": expected, "actual": actual,
                    "severity": level, "rule": rule, "possible_factors": _factors(period),
                    "actions": playbook[rule], "status": "acknowledged" if alert_id in acknowledged else "open"})

    for (ind, group_type, group), cells in frame.groupby(["indicator", "group_type", "group"]):
        cells = cells.sort_values("period")
        s = cells.set_index("period")["value"]
        period, value = str(s.index[-1]), float(s.iloc[-1])
        freq = cells["frequency"].iloc[0]
        if freq == "M":
            # Reindex only for calculations; missing observations never become zero.
            regular = s.reindex(pd.period_range(s.index[0], s.index[-1], freq="M").astype(str))
            yoy = regular.pct_change(12, fill_method=None).replace([np.inf, -np.inf], np.nan).dropna() * 100
            if len(yoy) >= 13 and yoy.index[-1] == period:
                low, high = np.quantile(yoy.iloc[:-1], [0.05, 0.95])
                actual = float(yoy.iloc[-1])
                if actual < low or actual > high:
                    add(ind, group, period, "unusual_change", f"{actual:+.1f}% YoY", f"{low:+.1f}% to {high:+.1f}% YoY",
                        f"Year-on-year change of {actual:+.1f}% is outside the historical 5th–95th percentile range.",
                        "medium" if actual < low else "low", group_type)
            if len(regular) >= 25 and cells["unit"].iloc[0] in ("registrations", "licences"):
                residuals = (regular - regular.shift(12)).iloc[:-1].dropna()
                baseline = regular.iloc[-13]
                if len(residuals) >= 12 and pd.notna(baseline):
                    band = 1.28155 * float(np.sqrt(np.mean(residuals ** 2)))
                    lo, hi = max(0, baseline - band), baseline + band
                    if value < lo or value > hi:
                        add(ind, group, period, "off_forecast", f"{value:,.0f}", f"{lo:,.0f} to {hi:,.0f}",
                            "Latest complete month is outside the seasonal-naive approximate 80% band.",
                            "high" if abs(value - baseline) > max(band * 2, 1) else "medium", group_type)
            if ind == "virtual_office_share":
                prior = str(pd.Period(period, "M") - 6)
                if prior in s and abs(value - s[prior]) > 10:
                    change = value - float(s[prior])
                    add(ind, group, period, "mix_shift", f"{value:.1f}%", f"{s[prior]:.1f}% six months earlier",
                        f"Virtual-office share changed {change:+.1f} percentage points in six months.", "high", group_type)
        if ind == "renewal_rate":
            current = pd.Period(period, freq="M" if freq == "M" else "Y")
            needed = [str(current - n) for n in range(1, 37 if freq == "M" else 4)]
            if all(p in s for p in needed):
                mean = float(s.loc[needed].mean())
                if value < mean - 1:
                    add(ind, group, period, "renewal_pressure", f"{value:.1f}%", f"3-year mean {mean:.1f}%",
                        f"Renewal rate is {mean - value:.1f} points below its previous three-year mean.", "medium", group_type)
    statuses = read_json(data_dir() / "cache/status.json", {})
    for sid, state in statuses.items():
        if state.get("status") in ("error", "stale") and state.get("failures", 0):
            add("data_quality", sid, state["last_checked"][:10], "data_quality", "Refresh failed",
                "Validated source update", "Source refresh failed; the last good snapshot is retained if available.", "medium")
    rank = {"high": 0, "medium": 1, "low": 2}
    return sorted([a for a in out if severity is None or a["severity"] == severity], key=lambda a: (rank[a["severity"]], a["id"]))


def acknowledge(alert_id: str, user: str) -> None:
    if not user.strip():
        raise ValueError("Acknowledgement requires a user")
    with LOCK:
        if alert_id not in {a["id"] for a in get_alerts()}:
            raise ValueError("Unknown alert id")
        path = data_dir() / "cache/acknowledged.json"
        state = read_json(path, {})
        if alert_id not in state:
            state[alert_id] = {"user": user, "time": now()}
            write_json(path, state)
            audit("acknowledge", user=user, alert_id=alert_id)
