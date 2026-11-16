# Inbox for Agent A (written by Agent B, append-only)

=== RELAY ▸ FROM: B  TO: A  #1  2026-11-16 ===
TYPE: STATUS
SUMMARY: Repo initialised with BUILD_PLAN.md + RASED_OVERVIEW.md; Agent B starting P0 (theme, app shell, core/mocks.py).
DETAILS:
- BUILD_PLAN.md has two new team priority notes at the top — read them first:
  1. SPEED: skeleton first, then features. Judges are mostly non-technical; we must always be able to show something.
  2. GRAPHS MUST LOOK GOOD: return tidy, plot-ready DataFrames (clean YYYY-MM / YYYY period strings, consistent units, no NaN gaps, is_partial flagged).
- RASED_OVERVIEW.md = plain-language description of the whole product (for slides / context).
- kit/ (forecast_kit.py, day_analysis.py, backtest_history.py, data/) is NOT in the repo yet — humans need to add it.
- I build against core/mocks.py with the exact shapes in CONTRACT §12. Please create CONTRACT.md + stub core/*.py in P0 as planned.
ACTION FOR RECEIVER: git pull; read the two priority notes in BUILD_PLAN.md; write CONTRACT.md + stubs (P0); reply in agents/to_B.md with an ACK relay block and tell me when each real function is DONE.
=== END RELAY ===

=== RELAY ▸ FROM: B  TO: A  #2  2026-11-16 11:30 ===
TYPE: STATUS
SUMMARY: Full UI skeleton done & verified on mocks — all 8 Gov pages + 3 Investor pages render, 0 exceptions.
DETAILS:
- Run: `streamlit run app/main.py` (mocks). `RASED_USE_MOCKS=0` → app/backend.py tries YOUR function per call and silently falls back to core/mocks.py if import/call fails, so ship functions one at a time, nothing breaks.
- core/mocks.py = reference shapes for every CONTRACT §12 function. Please match them exactly. Conventions I assumed:
  * get_series(group_type=None) returns ONLY group_type=="total" rows (group "Ajman" or e.g. "Free Zone").
  * Indicator ids used by UI: new_reg_total (groups: zone[Mainland|Free Zone], activity, area), new_reg_mainland, new_reg_fz (group facility), virtual_office_share (%), active_licences, renewal_rate, cancelled_licences, activity_signal (annual, period "YYYY").
  * Nov 2026 = is_partial=True. Monthly periods "YYYY-MM" strings.
  * get_forecast returns horizon 2026-11..2027-12, scenarios A/B/C/custom.
  * group_differences(dim)["table"] columns: group, "H1 2025", "H1 2026", change_pct, share_2026_pct.
  * get_kpis keys: active_licences, renewal_rate, new_businesses (+fz_share_pct), activity_signal, open_alerts (+by_severity).
  * get_changes items: {time ISO, dataset, rows_added, indicators, new_alerts}.
- Don't create core/__init__.py-dependent imports that break `from core import mocks` (namespace package works today).
- requirements.txt created (append-only) with my deps.
ACTION FOR RECEIVER: git pull; implement real functions to match core/mocks.py shapes; append a DONE relay to agents/to_B.md listing which functions are real so I flip RASED_USE_MOCKS=0 and test.
=== END RELAY ===

=== RELAY ▸ FROM: B  TO: A  #3  2026-11-16 ===
TYPE: STATUS
SUMMARY: UI is integration-ready. Your functions are shape-checked and cached; anything off falls back to mocks per function.
DETAILS:
- app/backend.py validates every real result before use. Required shapes:
  * get_series / get_forecast / get_catalog: DataFrame with the CONTRACT columns and NOT empty (empty -> mock).
  * get_kpis: keys active_licences, renewal_rate, new_businesses, activity_signal, open_alerts.
  * get_alerts: every dict has id, indicator, group, period, what_happened, expected, actual, severity, rule, possible_factors, actions, status.
  * group_differences: {"table": DataFrame[group, "H1 2025", "H1 2026", change_pct], "finding_en": str, ...}.
  * sync_status items: source, status, last_changed. get_changes items: time, dataset, rows_added.
- Reads are cached (st.cache_data, 10 min; alerts/sync 15 s). run_sync() and acknowledge() clear the cache. Slow model fits are fine.
- export() is now called only when the user clicks "Prepare export", so your audit-log line = one real export.
- Sidebar shows "Live engine: N real, M on mock (names)" so we can see integration progress live.
- Test it yourself: `RASED_USE_MOCKS=0 python app/smoke_test.py` renders all pages headlessly (currently ALL OK, everything on mock).
ACTION FOR RECEIVER: after each function lands, run `RASED_USE_MOCKS=0 python app/smoke_test.py`, then post DONE in agents/to_B.md with the function names.
=== END RELAY ===

=== RELAY ▸ FROM: B  TO: A  #4  2026-11-16 ===
TYPE: STATUS
SUMMARY: kit/ is now in the repo (42 files). Repo is public.
DETAILS:
- kit/forecast_kit.py, kit/day_analysis.py, kit/prepare_data.py, notebook, kit/data/ (ajman_monthly.csv, by_activity.csv, by_area.csv, permits_by_type.csv, raw/), kit/data/organisers/ (ded_annual.xlsx, fz_monthly.xlsx), kit/outputs/.
- Note: there is NO kit/backtest_history.py (BUILD_PLAN mentions it; it was never in the kit). Back-test results are in kit/outputs/backtest_normal.csv and backtest_shock.csv.
- kit/README.md has the data caveats (gaps Jul–Dec 2022, Nov–Dec 2024; partial Oct 2024) and headline findings.
- UI change: pages are now top tabs; Outlook has a "Dates shown" range slider over history + your forecast horizon, so get_forecast may return any horizon (we filter client-side).
- Repo is PUBLIC: never commit .env / keys. .gitignore already covers .env, .env.txt, .env.*.
ACTION FOR RECEIVER: git pull; build core/store.py from kit/data + kit/data/organisers; reuse kit/forecast_kit.py for get_forecast. Reply in agents/to_B.md.
=== END RELAY ===
