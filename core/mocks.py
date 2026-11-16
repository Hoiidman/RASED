"""Mock implementations of CONTRACT §12 (owner: Agent B).

Same shapes as the real engine. Deterministic (fixed seed) so charts do not jitter.
Numbers follow BUILD_PLAN demo figures (41,316 active licences, 94.3% renewal, etc.).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

SRC_FZ = "Ajman Free Zone (organisers file)"
SRC_DED = "Ajman DED open data"
SRC_DED_ANNUAL = "DED annual (organisers file)"

LAST_FULL = "2026-10"
PARTIAL = "2026-11"
_MONTHS = pd.period_range("2023-01", PARTIAL, freq="M")
_RAMADAN = {"2023-03": 0.85, "2023-04": 0.72, "2024-03": 0.72, "2024-04": 0.85,
            "2025-03": 0.70, "2026-02": 0.85, "2026-03": 0.75}
_HIGH = {"01": 1.10, "10": 1.05, "12": 1.08, "07": 0.90, "08": 0.88}

ACTIVITIES = ["General trading", "Restaurants & cafes", "Construction & contracting",
              "Professional services", "Retail shops", "Real estate", "IT & e-commerce",
              "Manufacturing", "Beauty & personal care", "Logistics & transport"]
_ACT_TREND = [-0.04, 0.40, -0.12, 0.34, -0.02, 0.06, 0.48, 0.12, 0.16, 0.36]
AREAS = ["Al Nuaimia", "Al Jurf", "Al Rashidiya", "Al Rawda", "Industrial Area",
         "Al Hamidiya", "Mushairef", "Al Zahra", "Al Bustan", "Al Mowaihat"]
_AREA_TREND = [0.36, 0.40, -0.04, 0.14, 0.30, 0.46, 0.02, 0.10, -0.06, 0.22]


def _rng(salt: int = 0):
    return np.random.default_rng(2026 + salt)


def _monthly_total(kind: str) -> pd.Series:
    rng = _rng(1 if kind == "mainland" else 2)
    vals = []
    for i, p in enumerate(_MONTHS):
        s = str(p)
        if kind == "mainland":
            v = 560 * (1.03 ** (i / 12))
            if s >= "2026-03":
                months_in = (p - pd.Period("2026-03", "M")).n
                v *= 0.54 + min(months_in, 8) * 0.012
        else:
            v = 760 * (1.10 ** (i / 12))
            if s >= "2026-01":
                v *= 1.0
        v *= _RAMADAN.get(s, 1.0) * _HIGH.get(s[5:], 1.0)
        v *= 1 + rng.normal(0, 0.035)
        vals.append(round(v))
    ser = pd.Series(vals, index=[str(p) for p in _MONTHS], dtype=float)
    if kind == "fz":
        ser[PARTIAL] = 379
    else:
        ser[PARTIAL] = 262
    return ser


_MAIN = _monthly_total("mainland")
_FZ = _monthly_total("fz")


def _row(period, ind, gtype, group, value, unit, source, freq="M", partial=False):
    return {"period": period, "frequency": freq, "indicator": ind, "group_type": gtype,
            "group": group, "value": float(value), "unit": unit, "source": source,
            "is_partial": bool(partial)}


def _build_rows() -> pd.DataFrame:
    rows = []
    for p in _MAIN.index:
        part = p == PARTIAL
        m, f = _MAIN[p], _FZ[p]
        rows.append(_row(p, "new_reg_mainland", "total", "Ajman", m, "registrations", SRC_DED, partial=part))
        rows.append(_row(p, "new_reg_fz", "total", "Ajman", f, "registrations", SRC_FZ, partial=part))
        rows.append(_row(p, "new_reg_total", "total", "Ajman", m + f, "registrations", SRC_DED, partial=part))
        rows.append(_row(p, "new_reg_total", "zone", "Mainland", m, "registrations", SRC_DED, partial=part))
        rows.append(_row(p, "new_reg_total", "zone", "Free Zone", f, "registrations", SRC_FZ, partial=part))
        # virtual office share (FZ): ~35% Jan-2025 -> ~59% Jun-2026
        i = (pd.Period(p, "M") - pd.Period("2025-01", "M")).n
        share = 0.30 + 0.002 * max(i + 24, 0) if i < 0 else min(0.35 + i * 0.0141, 0.61)
        share = round(share * 100, 1)
        rows.append(_row(p, "virtual_office_share", "total", "Free Zone", share, "%", SRC_FZ, partial=part))
        # facility mix for FZ
        rest = 100 - share
        for fac, w in [("Virtual office", None), ("Flexi desk", 0.42), ("Office", 0.33),
                       ("Warehouse", 0.15), ("Land", 0.10)]:
            val = share if w is None else rest * w
            rows.append(_row(p, "new_reg_fz", "facility", fac, round(f * val / 100), "registrations", SRC_FZ, partial=part))
    # activity & area breakdown of total new registrations
    rng = _rng(7)
    base_w_act = np.array([0.22, 0.12, 0.10, 0.11, 0.09, 0.06, 0.08, 0.05, 0.08, 0.09])
    base_w_area = np.array([0.16, 0.12, 0.11, 0.10, 0.09, 0.08, 0.09, 0.08, 0.08, 0.09])
    for p in _MAIN.index:
        part = p == PARTIAL
        t = (pd.Period(p, "M") - pd.Period("2023-01", "M")).n / 12
        tot = _MAIN[p] + _FZ[p]
        for names, base, trend, gtype in [(ACTIVITIES, base_w_act, _ACT_TREND, "activity"),
                                          (AREAS, base_w_area, _AREA_TREND, "area")]:
            w = base * (1 + np.array(trend)) ** t * (1 + rng.normal(0, 0.04, len(base)))
            w = w / w.sum()
            for n, wi in zip(names, w):
                rows.append(_row(p, "new_reg_total", gtype, n, round(tot * wi), "registrations", SRC_DED, partial=part))
    # annual series
    active = {2017: 27410, 2018: 28620, 2019: 29880, 2020: 28150, 2021: 30240,
              2022: 32510, 2023: 34480, 2024: 36725, 2025: 41316}
    renew = {2019: 91.9, 2020: 89.8, 2021: 92.8, 2022: 93.1, 2023: 93.6, 2024: 93.9, 2025: 94.3}
    signal = {2018: 3.9, 2019: 3.4, 2020: -6.1, 2021: 6.8, 2022: 7.4, 2023: 5.9, 2024: 6.4, 2025: 7.1}
    cancelled = {2021: 2410, 2022: 2290, 2023: 2215, 2024: 2240, 2025: 2355}
    for y, v in active.items():
        rows.append(_row(str(y), "active_licences", "total", "Ajman", v, "licences", SRC_DED_ANNUAL, "Y"))
    for y, v in renew.items():
        rows.append(_row(str(y), "renewal_rate", "total", "Ajman", v, "%", SRC_DED_ANNUAL, "Y"))
    for y, v in signal.items():
        rows.append(_row(str(y), "activity_signal", "total", "Ajman", v, "% change", SRC_DED_ANNUAL, "Y"))
    for y, v in cancelled.items():
        rows.append(_row(str(y), "cancelled_licences", "total", "Ajman", v, "licences", SRC_DED_ANNUAL, "Y"))
    return pd.DataFrame(rows)


_ROWS = _build_rows()

_CATALOG = [
    ("new_reg_total", "New registrations (all)", "التسجيلات الجديدة (الكل)", "registrations", "M", "total,zone,activity,area", SRC_DED),
    ("new_reg_mainland", "New registrations – mainland", "التسجيلات الجديدة – البر الرئيسي", "registrations", "M", "total", SRC_DED),
    ("new_reg_fz", "New registrations – Free Zone", "التسجيلات الجديدة – المنطقة الحرة", "registrations", "M", "total,facility", SRC_FZ),
    ("virtual_office_share", "Virtual-office share of FZ registrations", "حصة المكاتب الافتراضية", "%", "M", "total", SRC_FZ),
    ("active_licences", "Active licences", "الرخص السارية", "licences", "Y", "total", SRC_DED_ANNUAL),
    ("renewal_rate", "Renewal rate", "معدل التجديد", "%", "Y", "total", SRC_DED_ANNUAL),
    ("cancelled_licences", "Cancelled licences", "الرخص الملغاة", "licences", "Y", "total", SRC_DED_ANNUAL),
    ("activity_signal", "Licence-implied activity signal", "مؤشر النشاط المستند إلى الرخص", "% change", "Y", "total", SRC_DED_ANNUAL),
]


# ---------------------------------------------------------------- store
def get_catalog() -> pd.DataFrame:
    df = pd.DataFrame(_CATALOG, columns=["id", "name_en", "name_ar", "unit", "frequency", "group_types", "source"])
    df["last_period"] = df["frequency"].map({"M": LAST_FULL, "Y": "2025"})
    return df


def get_series(ids, group_type=None, start=None, end=None) -> pd.DataFrame:
    df = _ROWS[_ROWS["indicator"].isin(list(ids))]
    df = df[df["group_type"] == (group_type or "total")]
    if start:
        df = df[df["period"] >= start]
    if end:
        df = df[df["period"] <= end]
    return df.reset_index(drop=True)


# ---------------------------------------------------------------- analytics
def get_kpis() -> dict:
    fz25 = _FZ[[p for p in _FZ.index if p.startswith("2025")]].sum()
    m25 = _MAIN[[p for p in _MAIN.index if p.startswith("2025")]].sum()
    return {
        "active_licences": {"value": 41316, "change_pct": 12.5, "period": "2025", "source": SRC_DED_ANNUAL},
        "renewal_rate": {"value": 94.3, "change_pct": 0.4, "period": "2025", "source": SRC_DED_ANNUAL},
        "new_businesses": {"value": 18504, "change_pct": 6.2, "period": "2025", "source": f"{SRC_DED} + {SRC_FZ}",
                           "fz_share_pct": 59.0, "mock_split": {"mainland": int(m25), "fz": int(fz25)}},
        "activity_signal": {"value": 7.1, "change_pct": None, "period": "2025", "source": SRC_DED_ANNUAL,
                            "note": "signal, not GDP"},
        "open_alerts": {"value": len([a for a in _ALERTS if a["status"] == "open"]),
                        "by_severity": {s: sum(1 for a in _ALERTS if a["severity"] == s and a["status"] == "open")
                                        for s in ("high", "medium", "low")}},
    }


_SCEN = {"A": (9, 12, 100), "B": (5, 6, 100), "C": (2, 3, 100)}


def get_forecast(indicator: str, recovery_start: int = 6, recovery_len: int = 6, depth_pct: int = 100) -> pd.DataFrame:
    ser = {"new_reg_mainland": _MAIN, "new_reg_fz": _FZ}.get(indicator, _MAIN + _FZ)
    hist = ser.drop(PARTIAL)
    normal = hist[[p for p in hist.index if "2025-04" <= p <= "2026-01"]].mean() * 1.03
    shocked = hist[[p for p in hist.index if "2026-05" <= p <= LAST_FULL]].mean()
    gap = (normal - shocked) * depth_pct / 100
    horizon = pd.period_range(PARTIAL, "2027-12", freq="M")
    out = []
    scen = dict(_SCEN)
    scen["custom"] = (recovery_start, recovery_len, depth_pct)
    for name, (rs, rl, dp) in scen.items():
        g = (normal - shocked) * dp / 100 if name == "custom" else gap
        for h, p in enumerate(horizon):
            prog = 0.0 if h < rs else min((h - rs + 1) / max(rl, 1), 1.0)
            level = (normal - g) + g * prog
            level *= {"2027-02": 0.82, "2027-03": 0.88}.get(str(p), 1.0)  # Ramadan 2027
            level *= _HIGH.get(str(p)[5:], 1.0)
            band = 0.08 + 0.012 * h
            out.append({"period": str(p), "scenario": name, "mean": round(level, 1),
                        "lo": round(level * (1 - band), 1), "hi": round(level * (1 + band), 1)})
    return pd.DataFrame(out)


def simulate_renewal(delta_pts: float) -> dict:
    retained = int(round(370 * delta_pts))
    active = 41316 + retained
    return {"businesses_retained": retained, "active_licences": active,
            "activity_signal_pct": round(7.1 + retained / 41316 * 100 * 0.62, 2),
            "assumptions": ["+1 pt renewal ≈ +370 businesses (DED 2025 renewals base)",
                            "Activity signal elasticity 0.62 to active licences (log-log 2017–2024)",
                            "Indicative: licence data is a signal, not GDP"]}


_DIM_MAP = {"zone": ("new_reg_total", "zone"), "facility": ("new_reg_fz", "facility"),
            "area": ("new_reg_total", "area"), "activity": ("new_reg_total", "activity")}
_STATIC_DIMS = {
    "licence_type": (["Commercial", "Professional", "Industrial", "Free Lancer (FZ)"], [-0.24, 0.05, 0.09, 0.31], [5200, 3900, 950, 1450]),
    "legal_form": (["LLC", "Sole establishment", "FZE", "FZ-LLC", "Branch"], [-0.18, -0.30, 0.12, 0.06, -0.04], [3300, 2600, 2900, 1900, 600]),
}
_FINDINGS = {
    "zone": ("Free Zone up ~7% while mainland fell ~28% (H1 2026 vs H1 2025).",
             "المنطقة الحرة ارتفعت ~7% بينما انخفض البر الرئيسي ~28% (النصف الأول 2026)."),
    "facility": ("Virtual offices rose from ~35% to ~59% of Free Zone registrations.",
                 "ارتفعت المكاتب الافتراضية من ~35% إلى ~59% من تسجيلات المنطقة الحرة."),
    "area": ("Al Hamidiya and Al Jurf grow fastest; Al Bustan and Al Rashidiya are cooling.",
             "الحميدية والجرف الأسرع نمواً؛ البستان والراشدية في تباطؤ."),
    "activity": ("IT & e-commerce and logistics lead growth; construction is contracting.",
                 "تقنية المعلومات والتجارة الإلكترونية واللوجستيات تقود النمو؛ المقاولات في تراجع."),
    "licence_type": ("Free Lancer licences grow fastest (+31%); commercial licences fell 24%.",
                     "رخص العمل الحر الأسرع نمواً (+31%)؛ الرخص التجارية انخفضت 24%."),
    "legal_form": ("Free Zone legal forms (FZE, FZ-LLC) grow; sole establishments fall most.",
                   "الأشكال القانونية في المنطقة الحرة تنمو؛ المؤسسات الفردية الأكثر تراجعاً."),
}


def group_differences(dim: str) -> dict:
    if dim in _DIM_MAP:
        ind, gt = _DIM_MAP[dim]
        df = get_series([ind], group_type=gt)
        h1_25 = df[df["period"].between("2025-01", "2025-06")].groupby("group")["value"].sum()
        h1_26 = df[df["period"].between("2026-01", "2026-06")].groupby("group")["value"].sum()
        if dim == "zone":  # pin to plan figures
            h1_26 = h1_26.copy()
            h1_26["Mainland"] = round(h1_25["Mainland"] * 0.72)
            h1_26["Free Zone"] = round(h1_25["Free Zone"] * 1.07)
        tab = pd.DataFrame({"group": h1_25.index, "H1 2025": h1_25.values, "H1 2026": h1_26.reindex(h1_25.index).values})
    else:
        names, trend, base = _STATIC_DIMS[dim]
        tab = pd.DataFrame({"group": names, "H1 2025": base, "H1 2026": [round(b * (1 + t)) for b, t in zip(base, trend)]})
    tab["change_pct"] = ((tab["H1 2026"] / tab["H1 2025"] - 1) * 100).round(1)
    tab["share_2026_pct"] = (tab["H1 2026"] / tab["H1 2026"].sum() * 100).round(1)
    tab = tab[tab["H1 2025"] >= 5].sort_values("change_pct", ascending=False).reset_index(drop=True)
    en, ar = _FINDINGS[dim]
    if dim in ("area", "activity") and len(tab) >= 4:  # keep the caption consistent with the numbers
        top, bot = tab["group"].tolist()[:2], tab["group"].tolist()[-2:]
        en = f"{top[0]} and {top[1]} grow fastest; {bot[0]} and {bot[1]} are cooling."
        ar = f"{top[0]} و{top[1]} الأسرع نمواً؛ {bot[0]} و{bot[1]} في تباطؤ."
    return {"table": tab, "finding_en": en, "finding_ar": ar}


# ---------------------------------------------------------------- alerts
_ALERTS = [
    {"id": "AL-001", "indicator": "virtual_office_share", "group": "Free Zone · facility", "period": "2026-06",
     "what_happened": "Virtual-office share of Free Zone registrations reached 59% (was 35% in Jan 2025).",
     "expected": "≤ 45%", "actual": "59%", "severity": "high", "rule": "mix_shift",
     "possible_factors": [
         {"text": "Higher office rents push new firms to virtual setups", "source": "Drivers monitor (hypothesis)", "date": "2026"},
         {"text": "Regional disruption since Mar 2026, so firms keep costs flexible", "source": "events.yaml", "date": "2026-03"},
         {"text": "Visa-linked Free Lancer packages", "source": "events.yaml", "date": "2025"}],
     "actions": ["Outreach programme to convert virtual-office firms to physical premises (rent incentive)",
                 "Track the renewal rate of virtual-office firms separately, since they are more likely to lapse",
                 "Bundle co-working space offers with FZ packages"],
     "status": "open"},
    {"id": "AL-002", "indicator": "new_reg_mainland", "group": "Mainland", "period": "2026-06",
     "what_happened": "Mainland new registrations fell 28% from H1 2025, below the 80% forecast band.",
     "expected": "~640 / month", "actual": "~430 / month", "severity": "high", "rule": "off_forecast",
     "possible_factors": [
         {"text": "Regional disruption from Mar 2026", "source": "events.yaml", "date": "2026-03"},
         {"text": "Ramadan & Eid fell in Feb–Mar 2026 (seasonal dip)", "source": "events.yaml", "date": "2026-02"}],
     "actions": ["Fast-track licence issuance campaign for mainland SMEs",
                 "Extend Mar 2026 fee/fine waivers by 3 months",
                 "Weekly monitoring of mainland registrations until recovery"],
     "status": "open"},
    {"id": "AL-003", "indicator": "new_reg_total", "group": "Construction & contracting", "period": "2026-09",
     "what_happened": "Construction registrations are down 31% on last year, an unusually large fall.",
     "expected": "−5% to +12% YoY", "actual": "−31% YoY", "severity": "medium", "rule": "unusual_change",
     "possible_factors": [
         {"text": "Project pipeline slowdown during regional disruption", "source": "news (context only)", "date": "2026-08"}],
     "actions": ["Engage contractors' association on pipeline outlook",
                 "Prioritise permit processing for active construction projects"],
     "status": "open"},
    {"id": "AL-004", "indicator": "renewal_rate", "group": "Virtual-office firms", "period": "2026-09",
     "what_happened": "The renewal rate among virtual-office firms is 91.2%, 1.6 points below its 3-year average.",
     "expected": "≥ 92.8%", "actual": "91.2%", "severity": "medium", "rule": "renewal_pressure",
     "possible_factors": [
         {"text": "Smaller firms more exposed to the 2026 slowdown", "source": "Drivers monitor (hypothesis)", "date": "2026"}],
     "actions": ["Targeted renewal reminders via AI renewal service",
                 "Offer fee instalments for renewals",
                 "Call-centre outreach to firms 30 days before expiry"],
     "status": "open"},
    {"id": "AL-005", "indicator": "new_reg_total", "group": "IT & e-commerce", "period": "2026-10",
     "what_happened": "IT & e-commerce registrations are up 34% on last year, an unusually strong rise.",
     "expected": "+5% to +20% YoY", "actual": "+34% YoY", "severity": "low", "rule": "unusual_change",
     "possible_factors": [{"text": "Shift to online business models", "source": "Drivers monitor (hypothesis)", "date": "2026"}],
     "actions": ["Promote Ajman as a digital-business hub", "Fast-lane e-commerce licences"],
     "status": "open"},
]


def get_alerts(severity=None) -> list[dict]:
    return [a for a in _ALERTS if severity in (None, a["severity"])]


def acknowledge(alert_id: str, user: str) -> None:
    for a in _ALERTS:
        if a["id"] == alert_id:
            a["status"] = "acknowledged"


# ---------------------------------------------------------------- drivers
def get_drivers() -> list[dict]:
    vo = get_series(["virtual_office_share"], start="2025-01")
    return [
        {"id": "policy", "name": "Government policy (fees, discounts, FZ offers)",
         "hypothesis": "Cheaper / promoted licences → more registrations",
         "proxy": "Dated policy events (fee waivers, FZ packages)", "source": "events.yaml (+ news)",
         "test": "Event study: 3 months before vs after, vs same months last year", "status": "ready",
         "result": "Mar 2026 fee/fine waivers: mainland registrations +9% in the 3 months after vs trend (indicative).", "chart": None},
        {"id": "corp_tax", "name": "Corporate tax", "hypothesis": "Tax level changes openings / closures",
         "proxy": "UAE CT fixed at 9% since June 2023; qualifying FZ income 0%", "source": "event date only",
         "test": "Before/after June 2023 on cancellations & legal-form mix", "status": "partial",
         "result": "A one-off event plus a Free Zone advantage, not a setting that moves.", "chart": None},
        {"id": "visa", "name": "Visa / residency rules", "hypothesis": "Easier residency → more freelancers & virtual offices",
         "proxy": "FZ Free Lancer licences, virtual-office share", "source": "fz_monthly",
         "test": "Trend + event dates for visa changes", "status": "ready",
         "result": "Virtual-office share 35% → 59% (Jan 2025 – Jun 2026).",
         "chart": vo[["period", "value"]].reset_index(drop=True)},
        {"id": "rent", "name": "Rent / real-estate prices", "hypothesis": "High rent → virtual offices instead of physical",
         "proxy": "Ajman rent / tenancy indices", "source": "Ajman Open Data (if available)",
         "test": "Correlation & lag vs virtual-office share", "status": "data_needed", "result": None, "chart": None},
        {"id": "infra", "name": "Infrastructure (roads, ports)", "hypothesis": "New infrastructure → factories & warehouses",
         "proxy": "Industrial licences, FZ warehouse/land facilities", "source": "by_area, fz facility + project dates",
         "test": "Event study around project completion dates", "status": "partial",
         "result": "Data ready; project completion dates needed.", "chart": None},
        {"id": "competition", "name": "Competition between emirates", "hypothesis": "Rival FZ fee cuts → Ajman loses registrations",
         "proxy": "Ajman FZ share of new registrations; rival fee events", "source": "fz_monthly + news/events",
         "test": "Alert when Ajman share falls after a rival event", "status": "partial",
         "result": "Needs rival fee events (manual entry).", "chart": None},
        {"id": "population", "name": "Population growth", "hypothesis": "More people → more shops & services",
         "proxy": "Population, retail/services licences", "source": "SCC / Ajman Open Data",
         "test": "Licences per 1,000 residents by activity", "status": "data_needed", "result": None, "chart": None},
    ]


# ---------------------------------------------------------------- sync / context / export
_NOW = datetime(2026, 11, 16, 11, 0)
_CHANGES = [
    {"time": (_NOW - timedelta(minutes=3)).isoformat(timespec="minutes"), "dataset": "ded_licences",
     "rows_added": 412, "indicators": ["new_reg_mainland", "new_reg_total"], "new_alerts": 1},
    {"time": (_NOW - timedelta(hours=26)).isoformat(timespec="minutes"), "dataset": "fz_monthly",
     "rows_added": 96, "indicators": ["new_reg_fz", "virtual_office_share"], "new_alerts": 0},
]


def sync_status() -> list[dict]:
    t = _NOW.isoformat(timespec="minutes")
    return [
        {"source": "Free Zone monthly", "status": "ok", "last_checked": t, "last_changed": "2026-11-15T09:00", "rows": 4120},
        {"source": "DED annual", "status": "ok", "last_checked": t, "last_changed": "2026-10-01T08:00", "rows": 212},
        {"source": "DED licences (open data)", "status": "ok", "last_checked": t, "last_changed": _CHANGES[0]["time"], "rows": 18930},
        {"source": "Ajman Open Data", "status": "stale", "last_checked": t, "last_changed": "2026-11-10T12:00", "rows": 0},
        {"source": "World Bank macro", "status": "ok", "last_checked": t, "last_changed": "2026-07-01T00:00", "rows": 40},
    ]


def run_sync(force: bool = False) -> dict:
    entry = {"time": datetime.now().isoformat(timespec="minutes"), "dataset": "ded_licences",
             "rows_added": 38, "indicators": ["new_reg_total"], "new_alerts": 1}
    _CHANGES.insert(0, entry)
    return {"changed": ["ded_licences"], "new_alerts": 1}


def get_changes(since=None) -> list[dict]:
    return [c for c in _CHANGES if since is None or c["time"] >= since]


def get_context(period: str, sector=None) -> dict:
    return {
        "news": [{"title": "Regional disruption weighs on Gulf trade flows", "source": "GDELT (mock)", "date": "2026-03-12"},
                 {"title": "UAE SMEs shift to flexible office models", "source": "GDELT (mock)", "date": "2026-05-20"}],
        "macro": [{"indicator": "UAE GDP growth", "value": 4.0, "unit": "%", "period": "2025", "source": "World Bank"},
                  {"indicator": "UAE inflation", "value": 2.1, "unit": "%", "period": "2025", "source": "World Bank"}],
        "events": [{"name": "Ramadan", "start": "2026-02-18", "end": "2026-03-19"},
                   {"name": "Regional disruption begins", "start": "2026-03-01", "end": None},
                   {"name": "DED fee & fine waivers", "start": "2026-03-15", "end": "2026-06-30"}],
    }


def export(ids, group_type=None, start=None, end=None, fmt="json") -> bytes:
    df = get_series(ids, group_type, start, end)
    if fmt == "csv":
        return df.to_csv(index=False).encode("utf-8")
    return json.dumps({"generated": datetime.now().isoformat(timespec="seconds"),
                       "rows": df.to_dict(orient="records")}, ensure_ascii=False, indent=2).encode("utf-8")
