"""Config-driven hypotheses with availability derived from loaded observations."""
from core.settings import config
from core.store import get_series


def get_drivers() -> list[dict]:
    result = []
    for driver in config("drivers"):
        rows = get_series([driver["indicator"]], driver.get("group_type"))
        rows = rows.loc[~rows["is_partial"].astype(bool)]
        available = not rows.empty
        # Trend data alone does not establish the hypothesis or constitute an event study.
        status = "partial" if available else "data_needed"
        chart = rows[["period", "value"]].copy() if available and rows["group"].nunique() == 1 else None
        result.append({**{k: driver[k] for k in ("id", "name", "hypothesis", "proxy", "source", "test")},
                       "status": status, "result": "Observed proxy available; hypothesis testing and verified event context pending." if available else None,
                       "chart": chart})
    return result
