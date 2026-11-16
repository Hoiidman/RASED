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
    return os.environ.get("RASED_USE_MOCKS", "1") != "0"


def engine_summary() -> str:
    if use_mocks():
        return "Mock data"
    real = sorted(k for k, v in ENGINE_USED.items() if v == "real")
    mock = sorted(k for k, v in ENGINE_USED.items() if v != "real")
    return f"Live engine: {len(real)} real, {len(mock)} on mock" + (f" ({', '.join(mock)})" if mock else "")


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


# Caching: the real engine may fit models (slow). Reads are cached so sliders and page switches stay
# instant during the demo; anything that changes state clears the cache.
_SLOW, _FAST = 600, 15  # seconds


@st.cache_data(ttl=_SLOW, show_spinner=False)
def get_catalog(): return _call("get_catalog")


@st.cache_data(ttl=_SLOW, show_spinner=False)
def get_series(ids, group_type=None, start=None, end=None): return _call("get_series", list(ids), group_type, start, end)


@st.cache_data(ttl=_SLOW, show_spinner=False)
def get_kpis(): return _call("get_kpis")


@st.cache_data(ttl=_SLOW, show_spinner="Running the forecast")
def get_forecast(indicator, recovery_start=6, recovery_len=6, depth_pct=100):
    return _call("get_forecast", indicator, recovery_start, recovery_len, depth_pct)


@st.cache_data(ttl=_SLOW, show_spinner=False)
def simulate_renewal(delta_pts): return _call("simulate_renewal", delta_pts)


@st.cache_data(ttl=_SLOW, show_spinner=False)
def group_differences(dim): return _call("group_differences", dim)


@st.cache_data(ttl=_FAST, show_spinner=False)
def get_alerts(severity=None): return _call("get_alerts", severity)


@st.cache_data(ttl=_SLOW, show_spinner=False)
def get_drivers(): return _call("get_drivers")


@st.cache_data(ttl=_FAST, show_spinner=False)
def sync_status(): return _call("sync_status")


@st.cache_data(ttl=_FAST, show_spinner=False)
def get_changes(since=None): return _call("get_changes", since)


@st.cache_data(ttl=_SLOW, show_spinner=False)
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
    """Warm the on-disk news cache for several alerts in parallel, so the page doesn't wait on each."""
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
