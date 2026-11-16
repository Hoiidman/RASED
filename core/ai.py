"""Grounded AI layer (owner: Agent B).

advise(mode, facts, profile, lang) -> {"text", "cited_facts", "engine"}
- Claude (claude-opus-5-5) when ANTHROPIC_API_KEY is set and the `anthropic` SDK is installed.
- Deterministic templates otherwise (or on any error / refusal) so the demo never fails.
The model only sees FACTS_JSON (aggregates, no trade names / licence numbers).
"""
from __future__ import annotations

import json
import os

MODEL = "claude-haiku-5-5"  # fastest model for live demo answers; on refusal/error the template is used

SYSTEM = (
    "You are RASED, an economic early-warning analyst for Ajman's Department of Economic Development. "
    "Use only the facts in FACTS_JSON. Quote numbers exactly with their source and period. "
    "If a fact is missing, say so. Licence data is not GDP or FDI; call it a 'licence-implied activity signal'. "
    "Give suggestions as options with trade-offs, not orders. Use neutral language on regional events "
    "('regional disruption'). Write plain, direct prose a non-specialist can read, at most about 180 words. "
    "Use a short numbered list only for suggestions. No emoji, no em dashes, no 'Label:' bullet patterns. "
    "Answer in {lang}."
)

MODE_TASK = {
    "gov_actions": "Recommend 3 actions DED could take now. For each: the action, why (cite facts), how to measure it.",
    "briefing": "Write a monthly briefing for DED leadership: what changed, why it may have changed, what to watch.",
    "investor": "Advise this investor (PROFILE) on their sector and area: outlook, competition, risks, 3 tailored suggestions. "
                "This forecasts their sector and area, not their business. End with 'Indicative, not financial advice.'",
    "theme": "Explain what the facts mean for Ajman under the given theme in 3 bullets.",
}


def _claude(mode: str, facts: dict, profile: dict | None, lang: str) -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    client = anthropic.Anthropic(api_key=key, timeout=25.0, max_retries=1)
    user = (f"TASK: {MODE_TASK.get(mode, MODE_TASK['theme'])}\n\n"
            f"FACTS_JSON:\n{json.dumps(facts, ensure_ascii=False, default=str)}\n\n"
            + (f"PROFILE:\n{json.dumps(profile, ensure_ascii=False)}\n" if profile else ""))
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        output_config={"effort": "low"},  # fast replies for a live demo
        system=SYSTEM.format(lang="Arabic" if lang == "ar" else "English"),
        messages=[{"role": "user", "content": user}],
    )
    if resp.stop_reason == "refusal":
        return None
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
    return text or None


def _fmt(v):
    if isinstance(v, (int, float)):
        return f"{v:,.1f}" if isinstance(v, float) and not float(v).is_integer() else f"{int(v):,}"
    return str(v)


def _template(mode: str, facts: dict, profile: dict | None, lang: str) -> tuple[str, list[str]]:
    f = facts
    cited: list[str] = []

    def c(key, label):
        if key in f:
            cited.append(f"{label}: {_fmt(f[key])}")
            return _fmt(f[key])
        return "n/a"

    if mode == "investor":
        p = profile or {}
        act, area, zone = p.get("activity", "your activity"), p.get("area", "your area"), p.get("zone", "Mainland")
        g = c("sector_growth_pct", f"{act} growth (H1 2026 vs H1 2025, %)")
        comp = c("area_competition", f"New businesses in {area} (last 12 months)")
        lvl = f.get("competition_level", "moderate")
        zone_note = c("zone_change_pct", f"{zone} registrations change (H1 2026, %)")
        growing = f.get("sector_growth_pct", 0) >= 0
        text = (
            f"#### {act} in {area}, {zone}\n\n"
            f"{act} registrations changed {g}% in the first half of 2026 compared with a year earlier, "
            f"{'so demand is growing' if growing else 'so the segment is cooling and you will need a clear point of difference'}. "
            f"{comp} new businesses registered in {area} over the last 12 months, which means {lvl} competition. "
            f"{zone} registrations as a whole changed {zone_note}% over the same period.\n\n"
            f"The main risk is that the regional disruption since March 2026 is still holding back mainland demand. "
            f"Ramadan, Eid and the summer months are usually slower for new registrations.\n\n"
            f"What you could do:\n\n"
            f"1. {'Consider a Free Zone virtual-office setup to keep fixed costs low while demand recovers' if zone == 'Mainland' else 'Start with a flexi-desk or virtual office' + (f', as {f["virtual_office_share_fz_pct"]:.0f}% of new Free Zone firms now do' if f.get('virtual_office_share_fz_pct') else '')}.\n"
            f"2. {'Look for a spot in ' + area + ' with fewer direct competitors nearby' if lvl == 'high' else area + ' still has room for new entrants, so opening early helps'}.\n"
            f"3. Open outside Ramadan and keep cash aside for the slow summer months.\n\n"
            f"Indicative, based on public data. Not financial advice."
        )
        return text, cited

    if mode == "gov_actions":
        rr = c("renewal_rate", "Renewal rate 2025 (%)")
        lever = c("retained_per_pt", "Businesses retained per +1 pt renewal")
        vo = c("virtual_office_share", "Virtual-office share of FZ registrations (%)")
        ml = c("mainland_change_pct", "Mainland registrations H1 2026 vs H1 2025 (%)")
        text = (
            f"1. **Protect renewals.** This has the largest effect. The renewal rate is {rr}%, and each extra point "
            f"keeps about {lever} businesses. Targeted reminders, fee instalments and calls 30 days before expiry "
            "would help. Track the monthly renewal rate against the 95.3% target.\n"
            f"2. **Support the mainland recovery.** Mainland registrations changed {ml}% in the first half of 2026. "
            "Extending the fee and fine waivers by 3 months and fast-tracking SME licences are two options. "
            "Track monthly mainland registrations against scenario B.\n"
            f"3. **Turn virtual offices into physical premises.** Virtual offices are {vo}% of new Free Zone "
            "registrations, which means a smaller local footprint. Rent incentives or co-working bundles could "
            "encourage firms to move. Track the virtual-office share and these firms' renewal rate.\n\n"
            "These are options for DED to weigh, each with costs. Licence data is a signal, not GDP."
        )
        return text, cited

    # briefing / theme
    text = "**Briefing**\n\n" + "\n".join(f"- **{k.replace('_', ' ').capitalize()}:** {_fmt(v)}" for k, v in f.items()
                                          if not isinstance(v, (dict, list)))
    cited = [f"{k}: {_fmt(v)}" for k, v in f.items() if not isinstance(v, (dict, list))]
    return text, cited


def advise(mode: str, facts: dict, profile: dict | None = None, lang: str = "en") -> dict:
    tpl_text, cited = _template(mode, facts, profile, lang)
    try:
        text = _claude(mode, facts, profile, lang)
    except Exception:  # noqa: BLE001 - offline / bad key / API error -> template
        text = None
    if text:
        return {"text": text, "cited_facts": cited, "engine": "claude"}
    return {"text": tpl_text, "cited_facts": cited, "engine": "template"}
