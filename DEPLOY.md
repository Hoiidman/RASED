# Deploying RASED online (Streamlit Community Cloud)

A backup copy of the dashboard at a public link. The laptop stays the main demo.

## One-time setup (about 5 minutes)

1. Go to https://share.streamlit.io and sign in with the GitHub account that owns `Hoiidman/RASED`.
2. **Create app** → **Deploy a public app from GitHub**:
   - Repository: `Hoiidman/RASED`
   - Branch: `main`
   - Main file path: `app/main.py`
   - App URL: pick a name, e.g. `rased-ajman`
3. **Advanced settings**:
   - Python version: **3.12** (tested with a clean copy; 3.14 also works locally)
   - Secrets (TOML). Streamlit exposes these as environment variables, which the app already reads:
     ```toml
     ANTHROPIC_API_KEY = "sk-ant-..."     # optional: without it the advisor uses templates
     GOV_PASSWORD = "choose-a-password"   # required online, or anyone with the link enters the Government portal
     ```
4. **Deploy**. The first start installs packages and builds the data from `kit/data` (about 1 to 3 minutes).

## Before the meeting

- Open the link 5 minutes early: free apps sleep after a period without visitors and take about a minute to wake.
- Set a monthly spending limit on the Anthropic key in the Anthropic console, since the advisor is public.

## How it works

- `data/cache` is not in git, so a fresh copy has no processed data. `backend.ensure_data()` runs one sync
  on first start, from the kit files in the repo. Without it the app would silently show mock numbers.
- The footer must read `Live engine: 11 real, 0 on mock`. If it names mock functions, check the app logs
  (Manage app → logs).
- Every push to `main` redeploys automatically.
- The integration API (`api/main.py`) is not part of this deploy; Community Cloud runs only the dashboard.

## Ajman Open Data portal API

`https://data.ajman.ae/api/explore/v2.1/` is an Opendatasoft portal. Public datasets need **no API key**;
there is nothing to apply for. Relevant datasets: `license-in-ajman-area` and `license-in-ajman-activities`
(DED, record level, updated 2026-09-28, start dates up to June 2026). Their monthly counts match the kit's
mainland figures exactly, so the portal is the kit's source. Only aggregated counts should enter RASED
(the API can group server side, e.g. `group_by=date_format(startdate, 'yyyy-MM')`), never trade names or
licence numbers.
