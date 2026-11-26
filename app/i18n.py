"""Arabic for pages and charts (owner: Agent B).

- lang() reads this visitor's own choice from session state, so two visitors never share a language.
- tr(en, ar) picks the text for the current language; the English stays next to the Arabic in the code.
- name(x) translates data names (areas, activities, licence types, zones, scenarios) for display only.
  Data keeps its English values, which the app uses for lookups.

Area, activity, licence-type and legal-form names are the official Arabic spellings from DED's public
register (data/reference/names_ar.csv, built by scripts/build_names_ar.py).
"""
from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd
import streamlit as st

MONTHS_AR = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر",
             "نوفمبر", "ديسمبر"]
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# Bidi controls. A signed number ("+7%", "-28%") is kept left-to-right with an embedding, so its sign
# stays in front; Arabic chart text gets a right-to-left base, since Plotly draws SVG text left-to-right.
LRE, RLE, PDF = "‪", "‫", "‬"

# names that are not on the DED register: zones, Free Zone categories, scenarios and a few labels
FIXED = {
    "Mainland": "البر الرئيسي", "Free Zone": "المنطقة الحرة", "Other": "أخرى", "Unknown": "غير معروف",
    "All Ajman": "عجمان كلها", "Ajman": "عجمان", "Total": "الإجمالي",
    "Virtual Office": "مكتب افتراضي", "Office": "مكتب", "Flexi Desk": "مكتب مرن",
    # Free Zone licence types and legal forms (Ajman Free Zone)
    "Free Lancer": "عمل حر", "Services": "خدمات", "Commercial": "تجارية", "E-Commerce": "تجارة إلكترونية",
    "General Trading": "تجارة عامة", "Industrial": "صناعية", "Professional": "مهنية",
    "Sole Proprietor": "مؤسسة فردية", "Free Zone Company - F.Z.C": "شركة منطقة حرة (ش.م.ح)",
    "Free Zone Entity - F.Z.E": "مؤسسة منطقة حرة (م.م.ح)",
}


def lang() -> str:
    """'ar' or 'en' for this visitor (main.py keeps st.session_state.lang as 'EN' or 'ع')."""
    try:
        return "ar" if st.session_state.get("lang") == "ع" else "en"
    except Exception:  # noqa: BLE001 - no session (tests, API)
        return "en"


def is_ar() -> bool:
    return lang() == "ar"


def tr(en: str, ar: str) -> str:
    return ar if is_ar() else en


def _norm(s) -> str:  # same rule as scripts/build_competitors.norm
    return re.sub(r"[^a-z0-9]", "", str(s).lower().replace("zone", ""))


@lru_cache(maxsize=1)
def _register() -> dict:
    from core.settings import ROOT
    try:
        d = pd.read_csv(ROOT / "data" / "reference" / "names_ar.csv")
    except (OSError, ValueError):
        return {}
    # retail spelling difference in the register, as in build_competitors.ALIASES
    out = {}
    for r in d.itertuples():
        out.setdefault(r.key, r.ar)
    out.setdefault("retaisaleofwomenreadymadeclothes", out.get("retailsaleofwomenreadymadeclothes"))
    return out


def name_ar(x) -> str:
    s = str(x)
    if s in FIXED:
        return FIXED[s]
    if ": " in s:  # 'Free Zone: Commercial', 'Mainland: Professional'
        a, b = s.split(": ", 1)
        return f"{name_ar(a)}: {name_ar(b)}"
    return _register().get(_norm(s)) or s


def name(x) -> str:
    """Display name in the current language (English data value -> official Arabic where known)."""
    return name_ar(x) if is_ar() else str(x)


def month(period, short: bool = True) -> str:
    """'2026-03' -> 'Mar 2026' / 'مارس 2026'. A year-only period ('2025', annual data) stays '2025'."""
    if len(str(period).strip()) == 4:
        return str(period).strip()
    try:
        p = pd.Period(str(period)[:7], "M")
    except (ValueError, TypeError):
        return str(period)
    if is_ar():
        return f"{MONTHS_AR[p.month - 1]} {p.year}"
    return f"{MONTHS_EN[p.month - 1]} {p.year}" if short else p.strftime("%B %Y")


def count(n: int, sing: str, plural: str, acc: str | None = None, dual: str | None = None) -> str:
    """Arabic counted noun: 3 to 10 take the plural ('5 رخص'), 11 to 99 the singular accusative
    ('14 فئة', '25 إنذاراً'), and 1, 0 and round hundreds the singular or plural as shown below."""
    n = int(n)
    r = n % 100
    if n == 2 and dual:
        return dual
    if n == 0:
        return f"0 {plural}"
    if 3 <= r <= 10:
        return f"{n:,} {plural}"
    if 11 <= r <= 99:
        return f"{n:,} {acc or sing}"
    return f"{n:,} {sing}"


def sig(text: str) -> str:
    """A signed number such as '+7%' kept left to right inside Arabic text (unchanged in English)."""
    return f"{LRE}{text}{PDF}" if is_ar() else text


def rtl(text: str) -> str:
    """Right-to-left base direction for Arabic text drawn by Plotly (unchanged in English)."""
    return f"{RLE}{text}{PDF}" if is_ar() and text else text
