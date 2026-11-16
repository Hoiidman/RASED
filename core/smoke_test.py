"""Main-path checks against the supplied kit; run after python -m core.sync."""
import json
import os

import numpy as np

from core import analytics, alerts, exporter, store, sync


def main():
    assert not store.get_catalog().empty
    kpis = analytics.get_kpis()
    assert kpis["active_licences"]["value"] == 41316
    assert kpis["new_businesses"]["value"] == 18504
    simulation = analytics.simulate_renewal(1)
    assert 360 <= simulation["businesses_retained"] <= 380
    print("KPIs and renewal simulation OK", flush=True)
    for indicator in ("new_reg_mainland", "new_reg_fz", "new_reg_total"):
        frame = analytics.get_forecast(indicator)
        assert set(frame["scenario"]) == {"A", "B", "C", "custom"}
        assert np.isfinite(frame[["mean", "lo", "hi"]]).all().all()
        assert (frame["lo"] <= frame["mean"]).all() and (frame["mean"] <= frame["hi"]).all()
        if indicator == "new_reg_fz":
            assert frame["period"].min() == "2026-11"
        print(indicator, len(frame), "forecast rows OK", flush=True)
    assert len(alerts.get_alerts()) >= 3
    payload = json.loads(exporter.export(["new_reg_mainland"]))
    assert payload["rows"]
    assert sync.run_sync()["changed"] == []
    print("Alerts, export and unchanged sync OK", flush=True)
    os.environ["API_KEYS"] = "smoke-read-key"
    os.environ["ADMIN_API_KEYS"] = "smoke-admin-key"
    from fastapi.testclient import TestClient
    from api.main import app
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 200
        assert client.get("/v1/health").status_code == 401
        headers = {"X-API-Key": "smoke-read-key"}
        assert client.get("/v1/indicators/data?ids=active_licences", headers=headers).status_code == 200
        assert client.post("/v1/sync", headers=headers).status_code == 403
        assert client.post("/v1/simulate/renewal", headers=headers, json={"delta_pts": 1}).status_code == 200
    print("API docs, authentication and main endpoints OK", flush=True)


if __name__ == "__main__":
    main()
