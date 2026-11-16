# Engine and API quick start

```sh
python -m pip install -r requirements.txt
python -m core.sync
python -m core.smoke_test
uvicorn api.main:app
```

Set `RASED_USE_MOCKS=0` for Streamlit. Set comma-separated `API_KEYS` and separate
`ADMIN_API_KEYS` in `.env`. Missing keys deny access; `/docs` remains public.
The scheduler is opt-in (`RASED_ENABLE_SCHEDULER=1`); run one API worker when enabled.
Default interval is 30 minutes; `RASED_DEMO_SYNC=1` changes it to one minute.
Only configured sources are read. Ajman portal ingestion is disabled until an
official endpoint, aggregate mapping and permission are confirmed.

`GET /v1/indicators/data?ids=new_reg_mainland&from=2025-01&to=2026-06`
requires `X-API-Key`. `group` selects the group type (zone, area, activity, etc.).
`POST /v1/sync` requires an admin key. Context reads are offline; optional network
refresh is explicit via `core.context.refresh_context(period, include_news=True)`.

## Coverage and interpretation

- Mainland monthly observations end June 2026; Free Zone ends October, with
  November flagged partial. Mainland forecasts begin July; Free Zone begins
  November. Combined forecasts use observed Free Zone counts where available.
- Annual KPI issuance counts use the organiser annual file, which has different
  coverage from the monthly open-data register. Never present modelled July–October
  mainland values as actuals.
- Activity/area breakdowns cover mainland only; facility/legal-form breakdowns
  cover Free Zone. Source labels preserve this distinction.
- The activity signal reuses the kit's log-log estimation, labelled as a licence
  signal, never as measured GDP or FDI. Renewal exposure is derived from the annual
  stock-flow balance; +1 point retains about 367 businesses.
- Forecasts reuse the supplied SARIMAX functions. Combined bounds are a summed
  uncertainty envelope. Free Zone projections are scenarios, not validated causal
  estimates. The kit's partial November alignment is corrected before fitting.
- Alerts use historical year-on-year percentiles, seasonal-naive residual bands,
  six-month share shifts, and three-year renewal means. No invented news or events.
- Cells with counts below five are excluded. Comparisons require complete matched
  half-years after suppression; missing data is never silently replaced with zero.

The portal connector, webhook delivery, verified event studies and external-source
live verification remain roadmap items. `core/ai.py` and the UI remain Agent B-owned.
