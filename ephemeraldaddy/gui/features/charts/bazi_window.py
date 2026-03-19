from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPlainTextEdit, QVBoxLayout

from ephemeraldaddy.analysis.bazi_getter import BaziChartData, build_bazi_chart_data
from ephemeraldaddy.core.chart import Chart

BAZI_INCOMPLETE_BIRTH_INFO_MESSAGE = (
    "BaZi calculation is not possible without complete birth info (date, time, and place)."
)

_HEAVENLY_STEM_TRANSLATIONS: dict[str, str] = {
    "甲": "Jia (Yang Wood)",
    "乙": "Yi (Yin Wood)",
    "丙": "Bing (Yang Fire)",
    "丁": "Ding (Yin Fire)",
    "戊": "Wu (Yang Earth)",
    "己": "Ji (Yin Earth)",
    "庚": "Geng (Yang Metal)",
    "辛": "Xin (Yin Metal)",
    "壬": "Ren (Yang Water)",
    "癸": "Gui (Yin Water)",
}

_EARTHLY_BRANCH_TRANSLATIONS: dict[str, str] = {
    "子": "Zi (Rat)",
    "丑": "Chou (Ox)",
    "寅": "Yin (Tiger)",
    "卯": "Mao (Rabbit)",
    "辰": "Chen (Dragon)",
    "巳": "Si (Snake)",
    "午": "Wu (Horse)",
    "未": "Wei (Goat)",
    "申": "Shen (Monkey)",
    "酉": "You (Rooster)",
    "戌": "Xu (Dog)",
    "亥": "Hai (Pig)",
}

_ZODIAC_TRANSLATIONS: dict[str, str] = {
    "鼠": "Rat",
    "牛": "Ox",
    "虎": "Tiger",
    "兔": "Rabbit",
    "龙": "Dragon",
    "龍": "Dragon",
    "蛇": "Snake",
    "马": "Horse",
    "馬": "Horse",
    "羊": "Goat",
    "猴": "Monkey",
    "鸡": "Rooster",
    "雞": "Rooster",
    "狗": "Dog",
    "猪": "Pig",
    "豬": "Pig",
}

_ELEMENT_TRANSLATIONS: dict[str, str] = {
    "木": "Wood",
    "火": "Fire",
    "土": "Earth",
    "金": "Metal",
    "水": "Water",
}

_TEN_GODS_TRANSLATIONS: dict[str, str] = {
    "比肩": "Friend (Peer)",
    "劫财": "Rob Wealth (Rival)",
    "劫財": "Rob Wealth (Rival)",
    "食神": "Eating God (Output)",
    "伤官": "Hurting Officer (Expression)",
    "傷官": "Hurting Officer (Expression)",
    "偏财": "Indirect Wealth",
    "偏財": "Indirect Wealth",
    "正财": "Direct Wealth",
    "正財": "Direct Wealth",
    "七杀": "Seven Killings",
    "七殺": "Seven Killings",
    "正官": "Direct Officer",
    "偏印": "Indirect Resource",
    "正印": "Direct Resource",
}


def _normalize_bazi_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple, set)):
        parts = [str(part).strip() for part in value if str(part).strip()]
        return ", ".join(parts)
    return str(value).strip()


def _english_gloss(value: Any) -> str:
    normalized = _normalize_bazi_value(value)
    if not normalized:
        return ""
    if normalized in _TEN_GODS_TRANSLATIONS:
        return _TEN_GODS_TRANSLATIONS[normalized]
    if normalized in _HEAVENLY_STEM_TRANSLATIONS:
        return _HEAVENLY_STEM_TRANSLATIONS[normalized]
    if normalized in _EARTHLY_BRANCH_TRANSLATIONS:
        return _EARTHLY_BRANCH_TRANSLATIONS[normalized]
    if normalized in _ZODIAC_TRANSLATIONS:
        return _ZODIAC_TRANSLATIONS[normalized]
    if normalized in _ELEMENT_TRANSLATIONS:
        return _ELEMENT_TRANSLATIONS[normalized]
    if len(normalized) == 2:
        left = _HEAVENLY_STEM_TRANSLATIONS.get(normalized[0])
        right = _EARTHLY_BRANCH_TRANSLATIONS.get(normalized[1])
        if left and right:
            return f"{left} + {right}"
    translated_parts: list[str] = []
    for char in normalized:
        translated = (
            _HEAVENLY_STEM_TRANSLATIONS.get(char)
            or _EARTHLY_BRANCH_TRANSLATIONS.get(char)
            or _ZODIAC_TRANSLATIONS.get(char)
            or _ELEMENT_TRANSLATIONS.get(char)
        )
        if translated:
            translated_parts.append(translated)
    return ", ".join(translated_parts)


def _bilingual(value: Any) -> str:
    normalized = _normalize_bazi_value(value)
    gloss = _english_gloss(normalized)
    if not gloss:
        return normalized
    return f"{normalized} ({gloss})"


def validate_chart_for_bazi(chart: Chart | None) -> str | None:
    if chart is None:
        return "Please select a chart first."
    if bool(getattr(chart, "is_placeholder", False)):
        return BAZI_INCOMPLETE_BIRTH_INFO_MESSAGE
    if bool(getattr(chart, "birthtime_unknown", False)):
        return BAZI_INCOMPLETE_BIRTH_INFO_MESSAGE
    birth_place = str(getattr(chart, "birth_place", "") or "").strip()
    if not birth_place:
        return BAZI_INCOMPLETE_BIRTH_INFO_MESSAGE
    if getattr(chart, "dt", None) is None and getattr(chart, "dt_local", None) is None:
        return BAZI_INCOMPLETE_BIRTH_INFO_MESSAGE
    return None


def resolve_bazi_birth_datetime(chart: Chart) -> datetime:
    dt_local = getattr(chart, "dt_local", None)
    if dt_local is not None:
        return dt_local
    chart_dt = getattr(chart, "dt")
    if chart_dt.tzinfo is not None:
        return chart_dt.astimezone(chart_dt.tzinfo).replace(tzinfo=None)
    return chart_dt


def build_bazi_details_lines(bazi_data: BaziChartData) -> list[str]:
    return [
        "BAZI CHART DETAILS",
        "",
        "Heavenly Stems:",
        f"  Year : {_bilingual(bazi_data.heavenly_stems['year'])}",
        f"  Month: {_bilingual(bazi_data.heavenly_stems['month'])}",
        f"  Day  : {_bilingual(bazi_data.heavenly_stems['day'])}",
        f"  Hour : {_bilingual(bazi_data.heavenly_stems['hour'])}",
        "",
        "Earthly Branches:",
        f"  Year : {_bilingual(bazi_data.earthly_branches['year'])}",
        f"  Month: {_bilingual(bazi_data.earthly_branches['month'])}",
        f"  Day  : {_bilingual(bazi_data.earthly_branches['day'])}",
        f"  Hour : {_bilingual(bazi_data.earthly_branches['hour'])}",
        "",
        "Five Elements / Na Yin:",
        f"  Year : {_bilingual(str(bazi_data.five_elements_summary['year']))}",
        f"  Month: {_bilingual(str(bazi_data.five_elements_summary['month']))}",
        f"  Day  : {_bilingual(str(bazi_data.five_elements_summary['day']))}",
        f"  Hour : {_bilingual(str(bazi_data.five_elements_summary['hour']))}",
        f"  Na Yin (Year): {_bilingual(str(bazi_data.five_elements_summary['na_yin']['year']))}",
        f"  Na Yin (Month): {_bilingual(str(bazi_data.five_elements_summary['na_yin']['month']))}",
        f"  Na Yin (Day): {_bilingual(str(bazi_data.five_elements_summary['na_yin']['day']))}",
        f"  Na Yin (Hour): {_bilingual(str(bazi_data.five_elements_summary['na_yin']['hour']))}",
        "",
        "Ten Gods (relative to Day Master):",
        f"  Year stem : {_bilingual(bazi_data.ten_gods_summary['year'])}",
        f"  Month stem: {_bilingual(bazi_data.ten_gods_summary['month'])}",
        f"  Hour stem : {_bilingual(bazi_data.ten_gods_summary['hour'])}",
        f"  Day branch main: {_bilingual(bazi_data.ten_gods_summary['day_branch_main'])}",
    ]


def create_bazi_window_dialog(
    parent: Any,
    chart: Chart,
    *,
    header_style: str,
    monospace_font_family: str,
) -> QDialog:
    dt_local = resolve_bazi_birth_datetime(chart)
    bazi_data = build_bazi_chart_data(dt_local)
    chart_name = (getattr(chart, "name", None) or "Chart").strip() or "Chart"
    birth_place = str(getattr(chart, "birth_place", "") or "").strip()

    dialog = QDialog(parent)
    dialog.setAttribute(Qt.WA_DeleteOnClose)
    dialog.setWindowTitle(f"Bazi Window • {chart_name}")
    dialog.resize(700, 760)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)

    summary_label = QLabel(
        "\n".join(
            [
                f"Chart: {chart_name}",
                f"Birth place: {birth_place}",
                f"Birth datetime (local civil): {dt_local.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Lunar date: {_bilingual(bazi_data.lunar_date_str)}",
                f"Year zodiac: {_bilingual(bazi_data.zodiac_animal)}",
                (
                    "Four Pillars: "
                    f"{_bilingual(bazi_data.year_pillar)} / {_bilingual(bazi_data.month_pillar)} / "
                    f"{_bilingual(bazi_data.day_pillar)} / {_bilingual(bazi_data.hour_pillar)}"
                ),
            ]
        )
    )
    summary_label.setStyleSheet(header_style)
    summary_font = summary_label.font()
    summary_font.setFamily(monospace_font_family)
    summary_label.setFont(summary_font)
    layout.addWidget(summary_label, 0)

    details_output = QPlainTextEdit()
    details_output.setReadOnly(True)
    details_font = details_output.font()
    details_font.setFamily(monospace_font_family)
    details_output.setFont(details_font)
    details_output.setPlaceholderText("BaZi chart details unavailable.")
    details_output.setPlainText("\n".join(build_bazi_details_lines(bazi_data)))
    layout.addWidget(details_output, 1)

    return dialog
