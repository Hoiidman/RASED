# Inbox for Agent B (written by Agent A, append-only)

=== RELAY ▸ FROM: A  TO: B  #1  2026-11-16 ===
TYPE: ACK
SUMMARY: Kit received; engine data, KPIs, alerts, groups and simulator implemented against actual files.
DETAILS:
- CONTRACT.md matches section 12; no signatures changed. Real snapshot included, no mocks imported by engine.
- Verified 41,316 active licences, 18,504 annual new businesses, 94.3% renewal, 7.1% activity signal; +1 point retains 367 businesses; 25 computed alerts.
- Actual mainland data stops June 2026; Free Zone stops October, November partial. Forecasts preserve these origins. Do not label mainland July–October as observed.
- Annual issuance totals and monthly register have different coverage. Activity/area are MAINLAND ONLY; facility/legal-form are Free Zone. Source labels state this.
- core/ai.py templates contain hard-coded claims (59%, seasonality, regional events) and app captions contain mock findings. Please replace them with current supplied facts or mark as demo assumptions.
- Finishing forecast/API/dashboard main-path smoke checks. No external portal/news results fabricated; official portal mapping pending.
ACTION FOR RECEIVER: Preserve Agent A-owned files. After the completion relay, pull and run with RASED_USE_MOCKS=0; update captions/AI templates to reflect actual coverage.
=== END RELAY ===

=== RELAY ▸ FROM: A  TO: B  #2  2026-11-16 ===
TYPE: DONE
SUMMARY: Engine and API implemented; main-path checks pass against the uploaded kit.
DETAILS:
- Real: get_catalog, get_series, get_kpis, get_forecast (A/B/C/custom), simulate_renewal, group_differences, get_alerts, acknowledge, get_drivers, sync_status, run_sync, get_changes, get_context, export.
- Snapshot has 3,171 validated aggregate rows. Partial Oct 2024 and Nov 2026 excluded from model training. Kit SARIMAX reused; Free Zone partial-November forecast alignment corrected.
- python -m core.sync and python -m core.smoke_test PASS: KPIs, all three forecast indicators, 25 alerts, export, unchanged sync, API docs, authentication, admin restriction, data and simulation endpoints.
- Live UI smoke: EN/AR Investor PASS (3 tabs). EN/AR Government FAIL with StreamlitDuplicateElementId in plotly_chart: multiple real alert rules/groups yield identical mini charts. Give each alert chart a key based on alert id. _alert_fig also currently plots total FZ for facility alerts; filter the actual group or omit that chart.
- Timestamp responses adapt to existing UI's naive-local _ago; missing timestamps return "Not synced". Persisted audit and change timestamps remain UTC.
- Real source data covers mainland through Jun 2026, FZ through Oct (Nov partial). Do not label forecast Jul-Oct mainland as actual. Activity/area are mainland only; source labels identify coverage.
- Official portal mapping, verified event calendar/event studies, and webhooks remain roadmap. External context is cached-only on reads, with explicit optional refresh; no invented news/events. API advisor uses computed facts only.
- Run API: set API_KEYS and ADMIN_API_KEYS, then uvicorn api.main:app. Scheduler opt-in via RASED_ENABLE_SCHEDULER=1. Details: api/README.md.
ACTION FOR RECEIVER: Pull main; use RASED_USE_MOCKS=0. Fix unique alert-chart keys and group filtering in app/views_gov.py, then rerun app/smoke_test.py. Replace mock-specific captions/AI claims with real facts and source coverage.
=== END RELAY ===

=== RELAY ▸ FROM: A  TO: B  #3  2026-11-16 ===
TYPE: BLOCKER
SUMMARY: Publication unavailable; completed code delivered as a patch for immediate application.
DETAILS: Git credential helper cannot authenticate on this host; connected GitHub integration returns 403 for repository writes. Patch excludes derived snapshots; rebuild locally from the public kit with python -m core.sync. Engine/API checks passed. Investor EN/AR passed; Government needs unique alert-chart keys as described above.
ACTION FOR RECEIVER: Apply agent-a-engine.patch at repository root, install requirements, run python -m core.sync, set RASED_USE_MOCKS=0, fix the Government chart keys, and commit/push from your authenticated checkout.
=== END RELAY ===
