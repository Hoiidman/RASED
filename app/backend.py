"""Single data gateway for the UI (owner: Agent B).

Each CONTRACT function resolves independently: if RASED_USE_MOCKS=0 and the real
function imports and runs, use it; otherwise fall back to core.mocks so a page
never goes blank while Agent A is still building.
"""
from __future__ import annotations

import importlib
import os

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


def _call(name, *args, **kwargs):
    if not use_mocks():
        try:
            mod = importlib.import_module(_REAL[name])
            result = getattr(mod, name)(*args, **kwargs)
            ENGINE_USED[name] = "real"
            return result
        except Exception as e:  # noqa: BLE001 - demo must never break
            ENGINE_USED[name] = f"mock (real failed: {type(e).__name__})"
    else:
        ENGINE_USED.setdefault(name, "mock")
    return getattr(mocks, name)(*args, **kwargs)


def get_catalog(): return _call("get_catalog")
def get_series(ids, group_type=None, start=None, end=None): return _call("get_series", ids, group_type, start, end)
def get_kpis(): return _call("get_kpis")
def get_forecast(indicator, recovery_start=6, recovery_len=6, depth_pct=100):
    return _call("get_forecast", indicator, recovery_start, recovery_len, depth_pct)
def simulate_renewal(delta_pts): return _call("simulate_renewal", delta_pts)
def group_differences(dim): return _call("group_differences", dim)
def get_alerts(severity=None): return _call("get_alerts", severity)
def acknowledge(alert_id, user): return _call("acknowledge", alert_id, user)
def get_drivers(): return _call("get_drivers")
def sync_status(): return _call("sync_status")
def run_sync(force=False): return _call("run_sync", force)
def get_changes(since=None): return _call("get_changes", since)
def get_context(period, sector=None): return _call("get_context", period, sector)
def export(ids, group_type=None, start=None, end=None, fmt="json"):
    return _call("export", ids, group_type, start, end, fmt)
