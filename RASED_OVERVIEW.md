# RASED (راصد) — Project Overview

*RASED — sees the change before it happens · يرصد التغيير قبل حدوثه*

**Event:** Ajman Business Hackathon 2026 · **Demo:** 16 Nov 2026, 12:30

> This document explains the whole project in plain language. Use it to build the presentation, or share it with anyone who asks what RASED is. The technical build details are in `BUILD_PLAN.md`.

---

## 1. One-line pitch

**RASED is an early-warning and decision dashboard for Ajman's economy.** It turns open business-licence data into clear signals, forecasts and recommended actions for government officials, and gives investors simple advice about where to open a business.

---

## 2. The problem

### Problem statement

**One line (hook):**
> Ajman's economy is changing fast, but decision-makers only see the change months after it has happened.

**Short version (problem slide):**
> In 2026, Ajman's business landscape shifted sharply. Mainland registrations fell about 28% while Free Zone registrations rose about 7%, and virtual offices grew from 35% to 59% of new Free Zone setups. The data to spot these shifts already exists, but it is spread across separate files and portals, reviewed manually, and reaches officials months late. By the time DED sees a decline, businesses have already closed or gone elsewhere. Investors face the same gap from the other side: there is no simple way to tell which sectors and areas in Ajman are growing, crowded or at risk.

**Structured version (bullets):**
- **What's happening:** Since March 2026, a regional disruption has split Ajman's economy. Mainland registrations are down about 28%, Free Zone registrations are up about 7%, and businesses are moving to virtual offices.
- **Why it matters:** Every business that doesn't renew is lost activity, jobs and revenue for Ajman. One point of renewal rate is worth about 370 businesses.
- **The gap:**
  1. Data is fragmented and reviewed late.
  2. There is no early warning when something changes.
  3. There is no clear link from a change to its likely causes and the right action.
  4. Licence data is often misread as GDP or foreign investment.
- **Who is affected:** DED officials, who react too late, and investors, who decide without guidance.
- **The question we answer:** *How can Ajman see economic change as it happens, understand why, and act before it becomes a loss?*

**Lead-in to the solution:** *"RASED sees the change before it happens. It warns, explains and recommends."*

*(Check the figures against the real data before the slides are final.)*

### Details

- **Ajman's business activity changed sharply in 2026.** After a regional disruption that began in March 2026, Free Zone and mainland registrations moved in opposite directions: in H1 2026, Free Zone registrations were up about 7% while mainland registrations were down about 28%.
- **How businesses set up is changing.** Virtual-office setups grew from about 35% to 59% of Free Zone registrations.
- **Officials see these changes months late.** The data exists, but it sits in separate files and portals, and nobody is watching it continuously.
- **Investors have no simple guide.** Someone opening a restaurant or trading company can't easily see which sectors and areas are growing or crowded.
- **Licence data is often misread.** Licence counts aren't GDP or foreign investment (FDI), and treating them that way leads to wrong conclusions.

---

## 3. The solution

RASED is **one app with two portals**:

| | **Government portal** | **Investor portal** |
|---|---|---|
| Who | DED officials and analysts | Entrepreneurs and investors |
| Access | Password login | Public, no login |
| Purpose | See changes early, understand them, act | Find opportunities, avoid risks |

RASED also has an **API** (a data connection that other systems can plug into), so the same numbers can feed other government systems.

---

## 4. What users can do

### 4.1 Government portal (6 pages)

1. **Overview — "What's changing"**
   - Headline numbers: Active licences (**41,316**, +12.5%), Renewal rate (**94.3%**), New businesses in 2025 (**18,504**, 59% in the Free Zone), Activity signal (**+7.1%**), and open alerts.
   - A chart of mainland vs Free Zone registrations, month by month.
   - An alerts feed showing the top 5 warnings.

2. **Outlook — "What may happen next"**
   - Forecasts under 3 scenarios (slow, middle and fast recovery), labelled A/B/C.
   - A **scenario dial**: officials choose when recovery starts, how long it lasts and how deep the shock is, and the chart updates.
   - An assumptions panel that shows exactly what the forecast assumes.

3. **Actions — "What DED should do"**
   - **Policy simulator:** for example, raising the renewal rate by **1 point keeps about 370 more businesses** open in Ajman.
   - AI recommendations, each with *why* (the facts behind it) and *how to measure* success.

4. **Sectors & groups**
   - Which business activities and areas are growing or shrinking.
   - How groups differ: mainland vs Free Zone, licence type, legal form, office type (the virtual-office shift) and area.

5. **Impact & measurement**
   - How Ajman benefits, with a KPI table showing the baseline, the target and how each KPI is measured (e.g. renewal rate from 94.3% to 95.3%).

6. **Export & API**
   - Pick metrics and dates, and download them as JSON or CSV.
   - Shows the matching API link so IT teams can automate it.
   - Every export is recorded in an audit log.

**Drivers page:** tracks possible causes of change, such as fees and policy, corporate tax, visa rules, rent, infrastructure, competition from other emirates and population. Each one is shown as a *hypothesis being monitored*, with what data we have and what's still missing.

### 4.2 Investor portal (3 pages)

1. **Opportunities** — the fastest-growing activities and areas, how crowded each one is, and mainland vs Free Zone.
2. **Watch-outs** — sectors that are cooling or crowded, seasonal effects (Ramadan/Eid) and the current outlook in plain words.
3. **My business advisor** — the investor enters their activity, area, zone and plans, and gets a sector and area outlook, the competition level, risks and 3 tailored suggestions.
   *Indicative, based on public data; not financial advice.*

---

## 5. The early-warning system (key innovation)

RASED watches every indicator every month and raises an alert when something unusual happens.

**It detects four things:**
1. **Off-forecast:** the actual number falls outside the expected range.
2. **Unusual change:** a year-on-year change bigger than anything normal in the history.
3. **Mix shift:** a share changes by more than 10 points in 6 months (e.g. virtual offices).
4. **Renewal pressure:** the renewal rate drops below its recent average.

**It explains:** each alert shows *possible contributing factors*, such as Ramadan/Eid, fee waivers, policy changes and regional disruption, and optionally related news headlines. These are labelled "context only — analyst to confirm", not stated as proven causes.

**It suggests actions:** each alert type comes with 2–3 suggested DED actions. For example, renewal pressure → targeted renewal reminders, fee instalments, and outreach to virtual-office companies.

Each alert card shows: what happened · the actual vs expected number · severity · possible factors · suggested actions · an Acknowledge button.

---

## 6. The AI layer

- RASED uses Claude (Anthropic's AI model) to write recommendations, briefings and investor advice.
- **Grounded AI:** the AI only receives numbers RASED has already calculated and must cite them. It can't make numbers up.
- **It never fails during the demo:** with no internet or no API key, RASED switches to pre-written templates built from the same facts.
- The AI receives only totals and averages, never company names or licence numbers.

---

## 7. Data

| Source | What it gives us |
|---|---|
| Organisers' Free Zone file | Monthly registrations by licence type, legal form and facility |
| Organisers' DED annual file | GDP, inflation, and new, renewed, cancelled and active licences |
| Ajman DED open data | New licences by activity, area and type (Jan 2025 – Jun 2026) |
| Ajman Open Data portal (data.ajman.ae) | Extra datasets (population, tourism, real estate) if available |
| World Bank (optional) | UAE-wide economic context |
| GDELT news (optional) | Headlines to give alerts context |
| Curated event calendar | Ramadan/Eid, fee waivers, policy changes, regional disruption |

**Updates itself automatically:** RASED checks the open-data portals on a schedule. When a dataset changes, it downloads the new data, checks it, updates the forecasts and alerts, and shows a banner such as *"Updated 3 min ago · 2 datasets changed · 1 new alert."*

**Works offline:** if a source is down or the wifi fails, RASED keeps showing the last good copy of the data and marks it as "stale".

**Easy to extend:** any new dataset becomes a new card or metric without rewriting the app.

---

## 8. Honest about what the data can and can't say

This is a deliberate strength. We tell judges this directly:

- Licence data is **not GDP**. We show a **"licence-implied activity signal"** instead.
- Licence data is **not FDI**. We show no FDI number.
- Foreign-owner share is shown only where data exists, and is labelled *"proxy, incomplete"*.
- The investor advisor forecasts the investor's **sector and area**, not their individual business.
- Current months with incomplete data are greyed out and left out of the forecasts.

---

## 9. How accurate are the forecasts? (back-tested on past data)

| Output | Typical error in normal years |
|---|---|
| Mainland yearly registrations | ~10% |
| Active licences | ~0.9% |
| Licence-implied activity signal | ~2.3% (8.7% in 2020) |
| Free Zone registrations | Hard to predict, so shown as scenarios only |

Other findings:
- New licences move about **2.4×** as much as GDP growth.
- Renewals follow the economy with about a **1-year delay**.
- **+1 point of renewal rate ≈ +370 businesses.**

---

## 10. Security & governance

**Built today:**
- Separate access: a password for government users, public access for investors.
- API keys are stored in a secure settings file, never in the code.
- Only totals and averages are shown. Any group with fewer than 5 records is hidden.
- No company names or licence numbers are shown.
- An audit log records who exported data, who ran a data sync and who acknowledged an alert.

**Roadmap:** UAE Pass login for officials, hosting on UAE government cloud, HTTPS, alignment with the UAE Personal Data Protection Law (Federal Decree-Law No. 45 of 2021) and UAE Information Assurance standards, access by department, and a penetration test before launch.

---

## 11. Impact for Ajman

- **Faster decisions:** officials see changes in weeks instead of months.
- **More businesses kept open:** the renewal lever shows exactly how many businesses each policy could keep (~370 per renewal point).
- **Better targeting:** DED sees which sectors, areas and setup types need support.
- **More investors:** clearer guidance helps them choose Ajman, and choose well.
- **Measurable:** every KPI has a baseline, a target, a data source and an update frequency.
- **Sustainable:** it updates automatically from official open data and can grow with new datasets.

---

## 12. Technology (for technical questions)

- **Dashboard:** Streamlit (Python), styled with the UAE Design System colours (AE Gold `#B68A35`, AE Black `#232528`, UAE Green `#006B48`, UAE Red `#C8102E`).
- **API:** FastAPI with automatic documentation at `/docs`.
- **Models:** SARIMAX time-series forecasting, a stock-flow model for active licences and scenario modelling.
- **AI:** Claude API, with a template fallback.
- **Data:** one standard table for all sources, plus a cache and an offline snapshot.
- **Languages:** English and Arabic labels.

---

## 13. Judging criteria — where we score

| Criterion (weight) | Our strength |
|---|---|
| Innovation & Originality (20%) | Two portals, early warning with factors and actions, renewal lever, investor advisor |
| Problem Understanding (15%) | 2026 shock, Free Zone vs mainland split, virtual-office shift, honest data limits |
| Feasibility & Implementation (20%) | Uses official open data, runs offline, exports and an API, extensible |
| Impact & Sustainability (20%) | KPI framework with targets, automatic updates, expandable sectors |
| Analytical Approach & Prototype (15%) | Back-tested models, visible assumptions, scenarios, working prototype |
| Presentation (10%) | Clear 4-minute story and live demo |

---

## 14. Suggested presentation outline (≈8 slides)

1. **Title:** RASED | راصد — sees the change before it happens
2. **The problem:** the 2026 shock, Free Zone vs mainland diverging, officials seeing data months late
3. **The solution:** one app, two portals, plus an API (diagram)
4. **Live demo:** Government portal (Overview → Alert → Outlook → Actions)
5. **Live demo:** Investor advisor
6. **Why trust it:** back-test accuracy, grounded AI, honest data limits
7. **Impact & security:** KPI targets, data protection, audit log
8. **Roadmap & ask:** UAE Pass, government cloud, more datasets, pilot with DED

## 15. 4-minute demo script

1. **(30 s) Problem:** the shock in 2026, Free Zone and mainland diverging, officials seeing data months late.
2. **(60 s) Government → Overview → Alerts:** open the virtual-office alert and show its factors and actions.
3. **(45 s) Outlook:** move the scenario dial. **Actions:** +1 point renewal ≈ 370 businesses kept.
4. **(30 s) Export:** pick 3 metrics and download JSON, then show the API docs. Click "Sync now" and the update banner appears.
5. **(45 s) Investor → Advisor:** type a business (e.g. restaurant, mainland, Al Nuaimia) and show the tailored outlook.
6. **(30 s) Close:** security, roadmap, and "licence data is a signal, not GDP or FDI."

---

## 16. Likely questions & answers

- **"Is this real data?"** Yes. It comes from DED and Free Zone files supplied by the organisers and from Ajman's open-data portals. If the internet fails, it runs from a saved copy.
- **"Can the AI make things up?"** No. It only sees numbers RASED calculated and must cite them. Without AI, templates give the same facts.
- **"Why not show GDP or FDI?"** Licence counts can't measure them honestly, so we show an activity *signal* and say so.
- **"How accurate are the forecasts?"** We tested them on past years. Active licences are within about 1% and mainland registrations within about 10% in normal years. For uncertain series, we show scenarios instead of one number.
- **"How does it stay up to date?"** It checks the open-data portals on a schedule and updates the data, forecasts and alerts automatically.
- **"Can DED's other systems use it?"** Yes, through the API, with exports in JSON or CSV.
- **"Is it secure?"** Government access needs a login, only totals and averages are shown, small groups are hidden and actions are logged. UAE Pass and government-cloud hosting are next.
- **"What's next?"** A pilot with DED, more datasets (population, tourism, real estate), UAE Pass, full Arabic, and live news on every alert.
