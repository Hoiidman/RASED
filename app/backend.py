"""Single data gateway for the UI (owner: Agent B).

Each CONTRACT function resolves independently: if RASED_USE_MOCKS=0 and the real
function imports and runs, use it; otherwise fall back to core.mocks so a page
never goes blank while Agent A is still building.
"""
from __future__ import annotations

import importlib
import os

import pandas as pd
import streamlit as st

from core import mocks

_REAL = {
    "get_catalog": "core.store", "get_series": "core.store",
    "get_kpis": "core.analytics", "get_forecast": "core.analytics",
    "simulate_renewal": "core.analytics", "group_differences": "core.analytics",
    "get_alerts": "core.alerts", "acknowledge": "core.alerts",
    "get_drivers": "core.drivers",
    "sync_status": "core.sync", "run_sync": "core.sync", "get_changes": "core.sync",
    "get_context": "core.context", "export": "core.exporter",
}

ENGINE_USED: dict[str, str] = {}  # function name -> "real" | "mock"


def use_mocks() -> bool:
    # Real engine by default (per-function mock fallback). Set RASED_USE_MOCKS=1 to force mocks.
    return os.environ.get("RASED_USE_MOCKS", "0") == "1"


def engine_summary() -> str:
    if use_mocks():
        return "Mock data"
    real = sorted(k for k, v in ENGINE_USED.items() if v == "real")
    mock = sorted(k for k, v in ENGINE_USED.items() if v != "real")
    from i18n import tr
    return (tr(f"Live engine: {len(real)} real, {len(mock)} on mock", f"المحرك المباشر: {len(real)} فعلية، {len(mock)} تجريبية")
            + (f" ({', '.join(mock)})" if mock else ""))


_ALERT_KEYS = {"id", "indicator", "group", "period", "what_happened", "expected", "actual", "severity",
               "rule", "possible_factors", "actions", "status"}
_COLS = {
    "get_catalog": {"id", "name_en", "unit", "frequency"},
    "get_series": {"period", "indicator", "group_type", "group", "value", "is_partial"},
    "get_forecast": {"period", "scenario", "mean", "lo", "hi"},
}


def _shape_ok(name, r) -> bool:
    """Reject results the pages can't draw, so a contract mismatch falls back to the mock, not a crash."""
    if name in _COLS:
        return isinstance(r, pd.DataFrame) and _COLS[name] <= set(r.columns) and not r.empty
    if name == "group_differences":
        return (isinstance(r, dict) and isinstance(r.get("table"), pd.DataFrame)
                and {"group", "H1 2025", "H1 2026", "change_pct"} <= set(r["table"].columns) and "finding_en" in r)
    if name == "get_kpis":
        return isinstance(r, dict) and {"active_licences", "renewal_rate", "new_businesses",
                                        "activity_signal", "open_alerts"} <= set(r)
    if name == "get_alerts":
        return isinstance(r, list) and all(_ALERT_KEYS <= set(a) for a in r)
    if name == "simulate_renewal":
        return isinstance(r, dict) and {"businesses_retained", "active_licences", "activity_signal_pct"} <= set(r)
    if name == "sync_status":
        return isinstance(r, list) and all({"source", "status", "last_changed"} <= set(s) for s in r)
    if name == "get_changes":
        return isinstance(r, list) and all({"time", "dataset", "rows_added"} <= set(c) for c in r)
    return True


def _call(name, *args, **kwargs):
    if not use_mocks():
        try:
            mod = importlib.import_module(_REAL[name])
            result = getattr(mod, name)(*args, **kwargs)
            if _shape_ok(name, result):
                ENGINE_USED[name] = "real"
                return result
            ENGINE_USED[name] = "mock (real returned an unexpected shape)"
        except Exception as e:  # noqa: BLE001 - demo must never break
            ENGINE_USED[name] = f"mock (real failed: {type(e).__name__})"
    else:
        ENGINE_USED.setdefault(name, "mock")
    return getattr(mocks, name)(*args, **kwargs)


@st.cache_resource(show_spinner="Preparing the data (first start only)")
def ensure_data() -> bool:
    """A fresh copy (e.g. a cloud deploy) has no processed snapshot, because data/cache is not in git.
    Build it once per server process from the kit files in the repo, so the app shows real data, not mocks."""
    if use_mocks():
        return False
    try:
        from core import store, sync
        if store.load_table().empty:
            sync.run_sync(force=True)
        return True
    except Exception:  # never block the app: pages fall back to mocks per function
        return False


# Caching. The licence data only changes when a sync stores a new snapshot, so results are keyed on the
# data version (the snapshot manifest's timestamp) and kept for a day: every visitor, tab and page reuses
# them, and a sync from any process (dashboard, API scheduler) changes the key, so nothing goes stale.
# The cache is shared by all users of one server process. Actions that change state also clear it.
_DAY, _HOUR, _FAST = 24 * 3600, 3600, 60  # seconds


def data_version() -> str:
    if use_mocks():
        return "mock"
    try:
        from core.settings import data_dir
        return str((data_dir() / "cache" / "manifest.json").stat().st_mtime_ns)
    except OSError:
        return "none"


def _tagged(name, *args):
    """Run a contract function and keep which engine answered, so a cached result still counts in the footer."""
    result = _call(name, *args)
    return result, ENGINE_USED.get(name, "mock")


def _untag(name, pair):
    result, mode = pair
    ENGINE_USED[name] = mode
    return result


@st.cache_data(ttl=_DAY, show_spinner=False)
def _catalog(v): return _tagged("get_catalog")


@st.cache_data(ttl=_DAY, show_spinner=False)
def _series(v, ids, group_type, start, end): return _tagged("get_series", list(ids), group_type, start, end)


@st.cache_data(ttl=_DAY, show_spinner=False)
def _kpis(v): return _tagged("get_kpis")


@st.cache_data(ttl=_DAY, show_spinner=False)  # spinner shown by get_forecast, in the visitor's language
def _forecast(v, indicator, recovery_start, recovery_len, depth_pct):
    return _tagged("get_forecast", indicator, recovery_start, recovery_len, depth_pct)


@st.cache_data(ttl=_DAY, show_spinner=False)
def _renewal(v, delta_pts): return _tagged("simulate_renewal", delta_pts)


@st.cache_data(ttl=_DAY, show_spinner=False)
def _groups(v, dim): return _tagged("group_differences", dim)


@st.cache_data(ttl=_HOUR, show_spinner=False)  # also changes on acknowledge, which clears the cache
def _alerts(v, severity): return _tagged("get_alerts", severity)


@st.cache_data(ttl=_DAY, show_spinner=False)
def _drivers(v): return _tagged("get_drivers")


def get_catalog(): return _untag("get_catalog", _catalog(data_version()))
def get_series(ids, group_type=None, start=None, end=None): return _untag("get_series", _series(data_version(), tuple(ids), group_type, start, end))
def get_kpis(): return _untag("get_kpis", _kpis(data_version()))
def get_forecast(indicator, recovery_start=6, recovery_len=6, depth_pct=100):
    from i18n import tr
    with st.spinner(tr("Running the forecast", "جارٍ حساب التوقعات")):
        return _untag("get_forecast", _forecast(data_version(), indicator, recovery_start, recovery_len, depth_pct))
def simulate_renewal(delta_pts): return _untag("simulate_renewal", _renewal(data_version(), delta_pts))
def group_differences(dim): return _untag("group_differences", _groups(data_version(), dim))
def get_alerts(severity=None): return _untag("get_alerts", _alerts(data_version(), severity))
def get_drivers(): return _untag("get_drivers", _drivers(data_version()))


@st.cache_data(ttl=_FAST, show_spinner=False)  # small file reads; short so the status panel stays current
def sync_status(): return _call("sync_status")


@st.cache_data(ttl=_FAST, show_spinner=False)
def get_changes(since=None): return _call("get_changes", since)


@st.cache_data(ttl=6 * _HOUR, show_spinner=False)
def _official_check(our_latest: str) -> dict:
    """Latest month published on the official Ajman Open Data portal (DED licences), via its public API.
    Raises on failure, so a failed check is not cached and is retried on the next visit."""
    import httpx
    from datetime import datetime
    r = httpx.get("https://data.ajman.ae/api/explore/v2.1/catalog/datasets/license-in-ajman-area/records",
                  params={"select": "max(startdate) as latest"}, timeout=6,
                  headers={"User-Agent": "RASED/1.0 (aggregate data check)"})
    r.raise_for_status()
    portal = str(r.json()["results"][0]["latest"])[:7]
    return {"portal_latest": portal, "ours": our_latest, "up_to_date": our_latest >= portal,
            "checked": datetime.now().isoformat(timespec="seconds")}


def official_check() -> dict | None:
    """Compares our mainland series with the official portal. None if the portal can't be reached."""
    try:
        cat = get_catalog().set_index("id")
        return _official_check(str(cat.loc["new_reg_mainland", "last_period"]))
    except Exception:  # noqa: BLE001 - offline or portal down: say so, don't block the page
        return None


@st.cache_data(ttl=_DAY, show_spinner=False)
def _competitors_table():
    """Counts per activity x area from DED's public register, built offline (scripts/build_competitors.py)."""
    from core.settings import ROOT
    return pd.read_csv(ROOT / "data" / "reference" / "competitors.csv")


def get_competitors(activity: str, area: str) -> dict | None:
    """Registered businesses in this activity and area, the area's rank, and the usual licence type.
    None if the activity isn't on the register. Counts under 5 are not published (in_area = None)."""
    try:
        d = _competitors_table()
    except (OSError, ValueError):
        return None
    d = d[d["activity"] == activity]
    if d.empty:
        return None
    total = d[d["area"] == "All Ajman"]
    areas = d[d["area"] != "All Ajman"].sort_values("licences", ascending=False).reset_index(drop=True)
    hit = areas.index[areas["area"] == area]
    rank = int(hit[0]) + 1 if len(hit) else None
    n = len(areas)
    if rank is None:
        level = "low"
    else:
        level = "high" if rank <= max(1, round(n * 0.25)) else "moderate" if rank <= round(n * 0.75) else "low"
    first = d.iloc[0]
    return {"in_area": int(areas.loc[hit[0], "licences"]) if rank else None,
            "ajman": int(total["licences"].iat[0]) if not total.empty else None,
            "rank": rank, "areas": n, "level": level,
            "licence_type": str(first["licence_type"]), "licence_type_share": int(first["licence_type_share_pct"]),
            "through": str(first["register_through"])}


@st.cache_data(ttl=_HOUR, show_spinner=False)
def get_context(period, sector=None):
    """Live context (core/context.py) even in mock mode: it doesn't depend on the engine.
    No live headlines -> mock sample headlines, labelled as samples."""
    try:
        from core import context as live
        ctx = live.get_context(period, sector)
        ENGINE_USED["get_context"] = "real"
    except Exception as e:  # noqa: BLE001
        ENGINE_USED["get_context"] = f"mock (real failed: {type(e).__name__})"
        return mocks.get_context(period, sector)
    if not ctx.get("news"):
        ctx["news"], ctx["news_live"] = mocks.get_context(period, sector)["news"], False
    return ctx


def prefetch_context(pairs):
    """Warm the news cache for several alerts in parallel, once an hour (not on every click)."""
    _prefetch(tuple(sorted(set(pairs))))


@st.cache_data(ttl=_HOUR, show_spinner=False)
def _prefetch(pairs):
    try:
        from concurrent.futures import ThreadPoolExecutor
        from core import context as live
        with ThreadPoolExecutor(max_workers=6) as ex:
            list(ex.map(lambda p: live.get_context(*p), set(pairs), timeout=20))
    except Exception:  # noqa: BLE001 - best effort
        pass


def acknowledge(alert_id, user):
    out = _call("acknowledge", alert_id, user)
    st.cache_data.clear()
    return out


def run_sync(force=False):
    out = _call("run_sync", force)
    st.cache_data.clear()
    return out


def export(ids, group_type=None, start=None, end=None, fmt="json"):  # not cached: writes the audit log
    return _call("export", list(ids), group_type, start, end, fmt)
