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
    "('regional disruption'). When most sectors or areas fell, call only the top-ranked ones 'the most resilient', "
    "never 'growing' or 'fastest-growing'. In Arabic, use the official Arabic names given in PROFILE "
    "(activity_ar, area_ar) and Western digits. Write plain, direct prose a non-specialist can read, at most about 180 words. "
    "Use a short numbered list only for suggestions. No emoji, no em dashes, no 'Label:' bullet patterns. "
    "Answer in {lang}."
)

MODE_TASK = {
    "gov_actions": "Recommend 3 actions DED could take now. For each: the action, why (cite facts), how to measure it.",
    "briefing": "Write a monthly briefing for DED leadership: what changed, why it may have changed, what to watch.",
    "investor": "Advise this investor (PROFILE) on their sector and area: outlook, competition, risks, 3 tailored suggestions. "
                "This forecasts their sector and area, not their business. End with 'Indicative, not financial advice.' "
                "(in Arabic: 'استرشادي، وليس نصيحة مالية.')",
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
        # Room for a full answer: Arabic takes more tokens than English, and a 1,500 cap cut Arabic answers off.
        max_tokens=4000,
        # Thinking off (Haiku 5.5 allows it at effort high or below): faster replies for a live demo, and no
        # thinking tokens eating into the answer's budget.
        thinking={"type": "disabled"},
        output_config={"effort": "low"},
        system=SYSTEM.format(lang="Arabic" if lang == "ar" else "English"),
        messages=[{"role": "user", "content": user}],
    )
    if resp.stop_reason in ("refusal", "max_tokens"):  # declined, or cut off mid-sentence: use the template
        import logging
        logging.getLogger("rased.ai").warning("Claude answer unusable (%s), using the template", resp.stop_reason)
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

    if mode == "investor" and lang == "ar":
        return _template_investor_ar(f, profile or {}, c), cited
    if mode == "gov_actions" and lang == "ar":
        return _template_gov_ar(c), cited

    if mode == "investor":
        p = profile or {}
        act, area, zone = p.get("activity", "your activity"), p.get("area", "your area"), p.get("zone", "Mainland")
        g = c("sector_growth_pct", f"{act} growth (H1 2026 vs H1 2025, %)")
        comp = c("new_businesses_all_sectors_in_area_last_12_months", f"New businesses of all kinds in {area} (last 12 months)")
        lvl = f.get("competition_level", "moderate")
        zone_note = c("zone_change_pct", f"{zone} registrations change (H1 2026, %)")
        growing = (f.get("sector_growth_pct") or 0) >= 0
        fell, n_sec = (str(f.get("sectors_that_fell_h1_2026", "")).split(" of ") + [""])[:2]
        rank = str(f.get("sector_rank_by_change", "")).split(" of ")[0]
        if growing:
            trend = "so demand is growing"
        elif fell.isdigit() and n_sec.isdigit() and int(fell) * 2 > int(n_sec) and rank.isdigit() and int(rank) * 2 <= int(n_sec):
            trend = (f"but {fell} of {n_sec} sectors fell, and this one held up better than most, "
                     f"so it is among the more resilient sectors right now")
        else:
            trend = "so the segment is cooling and you will need a clear point of difference"
        reg_key = next((k for k in f if k.startswith("same_activity_licences_in_area")), None)
        if reg_key:  # saturation from DED's public register (relative, not an exact count of active firms)
            here = c(reg_key, f"{act} licences in {area} on DED's register (to Mar 2024)")
            rank = c("area_rank_for_this_activity", f"{area} rank for {act}")
            competition = (f"DED's public register lists {here} {act.lower()} licences in {area}, ranking it {rank} "
                           f"for this activity, so the risk of a crowded market there is {lvl}. ")
        else:
            competition = f"{comp} new businesses registered in {area} over the last 12 months, which means {lvl} competition. "
        text = (
            f"#### {act} in {area}, {zone}\n\n"
            f"{act} registrations changed {g}% in the first half of 2026 compared with a year earlier, "
            f"{trend}. "
            f"{competition}"
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


LRE, PDF = "\u202a", "\u202c"  # keeps a signed number such as -20.2 left to right inside Arabic text


def _count_ar(n, sing: str, plural: str) -> str:
    """Arabic counted noun: plural for 3 to 10 ('5 رخص'), singular otherwise ('14 رخصة')."""
    import re
    digits = re.findall(r"\d+", str(n).replace(",", ""))  # 'أقل من 5' counts as 5
    if not digits:
        return f"{n} {sing}"
    k = int(digits[-1])
    return f"{n} {plural}" if 3 <= k % 100 <= 10 else f"{n} {sing}"


def _template_investor_ar(f: dict, p: dict, c) -> str:
    """Arabic fallback for the investor advisor (used when Claude is unavailable)."""
    act = p.get("activity_ar") or p.get("activity", "نشاطك")
    area = p.get("area_ar") or p.get("area", "منطقتك")
    zone = p.get("zone_ar") or ("المنطقة الحرة" if p.get("zone") == "Free Zone" else "البر الرئيسي")
    g = c("sector_growth_pct", f"نمو {act} (النصف الأول 2026 مقارنة بـ 2025، %)")
    zone_note = c("zone_change_pct", f"تغير تسجيلات {zone} (النصف الأول 2026، %)")
    lvl = {"high": "مرتفع", "moderate": "متوسط", "low": "منخفض"}.get(f.get("competition_level"), "متوسط")
    growing = (f.get("sector_growth_pct") or 0) >= 0
    fell, n_sec = (str(f.get("sectors_that_fell_h1_2026", "")).split(" of ") + [""])[:2]
    sec_rank = str(f.get("sector_rank_by_change", "")).split(" of ")[0]
    if growing:
        trend = "أي أن الطلب في نمو"
    elif fell.isdigit() and n_sec.isdigit() and int(fell) * 2 > int(n_sec) and sec_rank.isdigit() \
            and int(sec_rank) * 2 <= int(n_sec):
        trend = f"لكن {fell} من {_count_ar(n_sec, 'قطاع', 'قطاعات')} تراجعت، وصمد هذا القطاع أفضل من معظمها"
    else:
        trend = "أي أن القطاع يتباطأ وستحتاج إلى ميزة واضحة تميزك"
    reg_key = next((k for k in f if k.startswith("same_activity_licences_in_area")), None)
    if reg_key:
        here = c(reg_key, f"رخص {act} في {area} في سجل الدائرة (حتى مارس 2024)").replace("fewer than 5", "أقل من 5")
        rank = c("area_rank_for_this_activity", f"ترتيب {area} في {act}").replace(
            "not in the top areas", "خارج المناطق الأعلى")
        rank = (lambda a: f"{a[0]} من {_count_ar(a[1].replace(' areas', ''), 'منطقة', 'مناطق')}" if len(a) == 2
                else a[0])(rank.split(" of "))
        competition = f"يسجل السجل العام للدائرة {_count_ar(here, 'رخصة', 'رخص')} ({act}) في {area} (الترتيب {rank})، لذا فخطر ازدحام السوق هناك {lvl}. "
    else:
        n = c("new_businesses_all_sectors_in_area_last_12_months", f"المنشآت الجديدة في {area} (آخر 12 شهراً)")
        competition = f"سُجلت {_count_ar(n, 'منشأة جديدة', 'منشآت جديدة')} في {area} خلال آخر 12 شهراً، والمنافسة {lvl}. "
    vo = f.get("virtual_office_share_fz_pct")
    first = ("فكّر في مكتب افتراضي في المنطقة الحرة لإبقاء التكاليف الثابتة منخفضة حتى يتعافى الطلب"
             if p.get("zone", "Mainland") == "Mainland" else
             "ابدأ بمكتب مرن أو افتراضي" + (f"، كما تفعل {vo:.0f}% من الشركات الجديدة في المنطقة الحرة" if vo else ""))
    second = (f"ابحث عن موقع في {area} بعدد أقل من المنافسين المباشرين" if lvl == "مرتفع"
              else f"ما زال في {area} متسع لمنشآت جديدة، والافتتاح المبكر يساعد")
    return (
        f"#### {act} في {area}، {zone}\n\n"
        f"تغيرت تسجيلات {act} بنسبة {LRE}{g}%{PDF} في النصف الأول من 2026 مقارنة بالعام السابق، {trend}. "
        f"{competition}"
        f"وتغيرت تسجيلات {zone} كلها بنسبة {LRE}{zone_note}%{PDF} في الفترة نفسها.\n\n"
        "الخطر الرئيسي أن الاضطراب الإقليمي منذ مارس 2026 ما زال يكبح الطلب في البر الرئيسي. "
        "وعادةً ما تكون أشهر رمضان والعيد والصيف أبطأ في التسجيلات الجديدة.\n\n"
        "ما يمكنك فعله:\n\n"
        f"1. {first}.\n"
        f"2. {second}.\n"
        "3. افتتح خارج رمضان، واحتفظ بسيولة لأشهر الصيف البطيئة.\n\n"
        "استرشادي، مبني على بيانات عامة. ليس نصيحة مالية."
    )


def _template_gov_ar(c) -> str:
    """Arabic fallback for the government recommendations (used when Claude is unavailable)."""
    rr = c("renewal_rate", "معدل التجديد 2025 (%)")
    lever = c("retained_per_pt", "منشآت يُحتفظ بها لكل نقطة تجديد إضافية")
    vo = c("virtual_office_share", "حصة المكاتب الافتراضية من تسجيلات المنطقة الحرة (%)")
    ml = c("mainland_change_pct", "تسجيلات البر الرئيسي، النصف الأول 2026 مقارنة بـ 2025 (%)")
    return (
        f"1. **حماية التجديدات.** هذا الإجراء الأكبر أثراً. معدل التجديد {rr}%، وكل نقطة إضافية تحافظ على نحو "
        f"{lever} منشأة. تساعد رسائل التذكير الموجهة وتقسيط الرسوم والاتصال قبل 30 يوماً من الانتهاء. "
        "يُقاس بمعدل التجديد الشهري مقابل المستهدف 95.3%.\n"
        f"2. **دعم تعافي البر الرئيسي.** تغيرت تسجيلات البر الرئيسي بنسبة {LRE}{ml}%{PDF} في النصف الأول من 2026. "
        "من الخيارات تمديد الإعفاء من الرسوم والغرامات 3 أشهر وتسريع رخص المنشآت الصغيرة والمتوسطة. "
        "يُقاس بالتسجيلات الشهرية للبر الرئيسي مقابل السيناريو ب.\n"
        f"3. **تحويل المكاتب الافتراضية إلى مقرات فعلية.** تمثل المكاتب الافتراضية {vo}% من التسجيلات الجديدة "
        "في المنطقة الحرة، ما يعني حضوراً محلياً أقل. قد تشجع حوافز الإيجار أو باقات العمل المشترك على الانتقال. "
        "يُقاس بحصة المكاتب الافتراضية ومعدل تجديد هذه الشركات.\n\n"
        "هذه خيارات تقيّمها الدائرة، ولكل منها تكلفة. بيانات الرخص مؤشر وليست الناتج المحلي."
    )


def advise(mode: str, facts: dict, profile: dict | None = None, lang: str = "en") -> dict:
    tpl_text, cited = _template(mode, facts, profile, lang)
    try:
        text = _claude(mode, facts, profile, lang)
    except Exception as e:  # noqa: BLE001 - offline / bad key / API error -> template
        import logging  # the error type only, never the key or the prompt
        logging.getLogger("rased.ai").warning("Claude unavailable, using the template: %s", type(e).__name__)
        text = None
    if text:
        return {"text": text, "cited_facts": cited, "engine": "claude"}
    return {"text": tpl_text, "cited_facts": cited, "engine": "template"}
