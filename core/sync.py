"""Validated snapshot updates with fingerprints, health, changelog and offline retention."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import httpx

from core.connectors import fetch
from core.security import LOCK, audit
from core.settings import config, data_dir, now, read_json, write_json
from core.store import KEY, load_table, validate


def sync_status() -> list[dict]:
    state = read_json(data_dir() / "cache/status.json", {})
    rows = [state.get(s["id"], {"source": s["id"], "status": "stale", "last_checked": None,
                               "last_changed": None, "rows": 0,
                               "message": "Not synced" if s.get("enabled", True) else "Not configured"})
            for s in config("sources")["sources"]]
    # Existing UI computes age with datetime.now() (naive local wall time).
    return [{**r, "last_checked": _display_time(r.get("last_checked")),
             "last_changed": _display_time(r.get("last_changed"))} for r in rows]


def _display_time(value):
    if not value:
        return "Not synced"
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone().replace(tzinfo=None).isoformat(timespec="seconds") if parsed.tzinfo else value


def _instant(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc)


def get_changes(since=None) -> list[dict]:
    entries = read_json(data_dir() / "cache/changelog.json", [])
    cutoff = _instant(since) if since else None
    return [{**c, "time": _display_time(c["time"])} for c in reversed(entries)
            if cutoff is None or _instant(c["time"]) > cutoff]


def run_sync(force: bool = False) -> dict:
    from core.alerts import get_alerts

    with LOCK:
        cache = data_dir() / "cache"
        manifest = read_json(cache / "manifest.json", {})
        state = read_json(cache / "status.json", {})
        for source in config("sources")["sources"]:
            state.setdefault(source["id"], {"source": source["id"], "status": "stale",
                "last_checked": None, "last_changed": None, "rows": 0})
        fingerprints = read_json(cache / "fingerprints.json", {})
        changes = read_json(cache / "changelog.json", [])
        before = {a["id"] for a in get_alerts()}
        changed, pending = [], []
        for source in config("sources")["sources"]:
            sid = source["id"]
            if not source.get("enabled", True):
                continue
            previous = state[sid]
            checked = now()
            try:
                frame, fingerprint = fetch(source)
                # Force rechecks content; it never manufactures a change event.
                old_path = data_dir() / manifest.get(sid, f"snapshot/{sid}.json")
                old = pd.DataFrame(read_json(old_path, []))
                if not old.empty and len(frame) < len(old) * 0.5:
                    raise ValueError("Row count fell below 50% of the last good snapshot")
                other = []
                for other_source in config("sources")["sources"]:
                    oid = other_source["id"]
                    if oid != sid:
                        records = read_json(data_dir() / manifest.get(oid, f"snapshot/{oid}.json"), [])
                        if records:
                            other.append(pd.DataFrame(records))
                validate(pd.concat([frame, *other], ignore_index=True))
                if fingerprint != fingerprints.get(sid) or not old_path.exists():
                    filename = f"cache/snapshots/{sid}-{fingerprint}.json"
                    write_json(data_dir() / filename, frame.to_dict("records"))
                    manifest[sid] = filename
                    write_json(cache / "manifest.json", manifest)
                    fingerprints[sid] = fingerprint
                    old_keys = set(map(tuple, old[KEY].values.tolist())) if not old.empty else set()
                    added = sum(tuple(row) not in old_keys for row in frame[KEY].values.tolist())
                    pending.append({"time": checked, "dataset": sid, "rows_added": added,
                                    "indicators": sorted(frame["indicator"].unique()), "new_alerts": 0})
                    changed.append(sid)
                state[sid] = {"source": sid, "status": "ok", "last_checked": checked,
                              "last_changed": checked if sid in changed else previous.get("last_changed"),
                              "rows": len(frame), "failures": 0, "message": "Validated aggregate snapshot"}
            except (ValueError, OSError, KeyError, TypeError, httpx.HTTPError) as exc:
                failures = previous.get("failures", 0) + 1
                state[sid] = {**previous, "last_checked": checked, "failures": failures,
                              "status": "stale" if failures >= 3 or previous.get("rows", 0) else "error",
                              "message": str(exc)}
        write_json(cache / "status.json", state)
        write_json(cache / "fingerprints.json", fingerprints)
        after = {a["id"] for a in get_alerts()}
        count = len(after - before)
        # Attach the batch's new-alert count once, avoiding duplicate counts across datasets.
        if pending:
            pending[-1]["new_alerts"] = count
            changes.extend(pending)
            write_json(cache / "changelog.json", changes)
        audit("sync", changed=changed, new_alerts=count, force=force)
        return {"changed": changed, "new_alerts": count}


if __name__ == "__main__":
    print(run_sync())
    print(sync_status())
