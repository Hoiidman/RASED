# RASED engine contract

## 12. Interface contract (`CONTRACT.md`) — the only thing both agents must agree on

All functions return plain pandas DataFrames / dicts. Periods are strings `YYYY-MM` (monthly) or `YYYY` (annual).

```python
# core/store.py                                         (owner: A)
get_catalog() -> DataFrame[id, name_en, name_ar, unit, frequency, group_types, source, last_period]
get_series(ids: list[str], group_type: str|None=None, start: str|None=None, end: str|None=None)
    -> DataFrame[period, frequency, indicator, group_type, group, value, unit, source, is_partial]

# core/analytics.py                                     (owner: A)
get_kpis() -> dict  # {"active_licences":{"value":41316,"change_pct":12.5,"period":"2025","source":...}, ...}
get_forecast(indicator: str, recovery_start: int=6, recovery_len: int=6, depth_pct: int=100)
    -> DataFrame[period, scenario, mean, lo, hi]        # scenarios "A","B","C","custom"
simulate_renewal(delta_pts: float) -> dict  # {"businesses_retained":int,"active_licences":int,"activity_signal_pct":float,"assumptions":[...]}
group_differences(dim: str) -> {"table": DataFrame, "finding_en": str, "finding_ar": str}
    # dim in {"zone","licence_type","legal_form","facility","area","activity"}

# core/alerts.py                                        (owner: A)
get_alerts(severity: str|None=None) -> list[dict]
    # {"id","indicator","group","period","what_happened","expected","actual","severity":"high|medium|low",
    #  "rule","possible_factors":[{"text","source","date"}],"actions":[str],"status":"open|acknowledged"}
acknowledge(alert_id: str, user: str) -> None

# core/drivers.py                                       (owner: A)
get_drivers() -> list[dict]  # {"id","name","hypothesis","proxy","source","test","status":"ready|partial|data_needed","result":str|None,"chart":DataFrame|None}

# core/sync.py, core/context.py, core/exporter.py       (owner: A)
sync_status() -> list[dict]    # {"source","status":"ok|stale|error","last_checked","last_changed","rows"}
run_sync(force: bool=False) -> dict   # {"changed":[source ids],"new_alerts":int}
get_changes(since: str|None=None) -> list[dict]
get_context(period: str, sector: str|None=None) -> {"news":[...],"macro":[...],"events":[...]}
export(ids, group_type=None, start=None, end=None, fmt="json") -> bytes   # writes audit log

# core/ai.py                                            (owner: B)
advise(mode: str, facts: dict, profile: dict|None=None, lang: str="en") -> {"text": str, "cited_facts": [str], "engine": "claude|template"}
    # mode in {"gov_actions","briefing","investor","theme"}
```
Changing a signature = send a CONTRACT CHANGE message (§13) and wait for "ACK" before pushing.

---

