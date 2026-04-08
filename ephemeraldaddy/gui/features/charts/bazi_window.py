from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from ephemeraldaddy.analysis.bazi_getter import (
    BaziChartData,
    UNKNOWN_BAZI_VALUE,
    build_bazi_chart_data,
)
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.interpretations import BAZI_ELEMENTS, BAZI_ZODIAC
from ephemeraldaddy.gui.style import (
    CHART_DATA_HIGHLIGHT_COLOR,
    CHART_THEME_COLORS,
    STANDARD_NCV_HORIZONTAL_BAR_CHART,
    STANDARD_NCV_PIE_CHART,
    configure_share_export_icon_button,
)

BAZI_INCOMPLETE_BIRTH_INFO_MESSAGE = (
    "BaZi calculation is not possible without date/time and place."
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

_ELEMENT_CHAR_TO_NAME: dict[str, str] = {
    "木": "wood",
    "火": "fire",
    "土": "earth",
    "金": "metal",
    "水": "water",
}

_ZODIAC_ORDER: list[str] = [
    "Rat",
    "Ox",
    "Tiger",
    "Rabbit",
    "Dragon",
    "Snake",
    "Horse",
    "Goat",
    "Monkey",
    "Rooster",
    "Dog",
    "Pig",
]

_BRANCH_TO_ZODIAC: dict[str, str] = {
    "子": "Rat",
    "丑": "Ox",
    "寅": "Tiger",
    "卯": "Rabbit",
    "辰": "Dragon",
    "巳": "Snake",
    "午": "Horse",
    "未": "Goat",
    "申": "Monkey",
    "酉": "Rooster",
    "戌": "Dog",
    "亥": "Pig",
}

_YANG_STEMS: set[str] = {"甲", "丙", "戊", "庚", "壬"}
_YIN_STEMS: set[str] = {"乙", "丁", "己", "辛", "癸"}
_YANG_BRANCHES: set[str] = {"子", "寅", "辰", "午", "申", "戌"}
_YIN_BRANCHES: set[str] = {"丑", "卯", "巳", "未", "酉", "亥"}

_STEM_ROMANIZATION: dict[str, str] = {
    "甲": "Jia",
    "乙": "Yi",
    "丙": "Bing",
    "丁": "Ding",
    "戊": "Wu",
    "己": "Ji",
    "庚": "Geng",
    "辛": "Xin",
    "壬": "Ren",
    "癸": "Gui",
}

_BRANCH_ROMANIZATION: dict[str, str] = {
    "子": "Zi",
    "丑": "Chou",
    "寅": "Yin",
    "卯": "Mao",
    "辰": "Chen",
    "巳": "Si",
    "午": "Wu",
    "未": "Wei",
    "申": "Shen",
    "酉": "You",
    "戌": "Xu",
    "亥": "Hai",
}

_STEM_ELEMENT: dict[str, str] = {
    "甲": "wood",
    "乙": "wood",
    "丙": "fire",
    "丁": "fire",
    "戊": "earth",
    "己": "earth",
    "庚": "metal",
    "辛": "metal",
    "壬": "water",
    "癸": "water",
}

_BRANCH_ELEMENT: dict[str, str] = {
    "子": "water",
    "丑": "earth",
    "寅": "wood",
    "卯": "wood",
    "辰": "earth",
    "巳": "fire",
    "午": "fire",
    "未": "earth",
    "申": "metal",
    "酉": "metal",
    "戌": "earth",
    "亥": "water",
}

_BAZI_ELEMENT_PIE_ORDER: list[str] = ["wood", "fire", "earth", "metal", "water"]


def _color_from_bazi_element(element_key: str, fallback: str | None = None) -> str:
    element_data = BAZI_ELEMENTS.get(element_key, {})
    if isinstance(element_data, dict):
        color = str(element_data.get("color", "") or "").strip()
        if color:
            return color
    return fallback or CHART_THEME_COLORS["text"]


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
    birth_place = str(getattr(chart, "birth_place", "") or "").strip()
    if not birth_place:
        return BAZI_INCOMPLETE_BIRTH_INFO_MESSAGE
    if getattr(chart, "dt", None) is None and getattr(chart, "dt_local", None) is None:
        return BAZI_INCOMPLETE_BIRTH_INFO_MESSAGE
    return None


def resolve_bazi_birth_datetime(chart: Chart) -> datetime:
    dt_local = getattr(chart, "dt_local", None)
    use_retcon_time = (
        bool(getattr(chart, "birthtime_unknown", False))
        and bool(getattr(chart, "retcon_time_used", False))
        and getattr(chart, "retcon_hour", None) is not None
        and getattr(chart, "retcon_minute", None) is not None
    )
    if dt_local is not None and use_retcon_time:
        return dt_local.replace(
            hour=int(getattr(chart, "retcon_hour")),
            minute=int(getattr(chart, "retcon_minute")),
            second=0,
            microsecond=0,
        )
    if dt_local is not None:
        return dt_local
    chart_dt = getattr(chart, "dt")
    if chart_dt.tzinfo is not None:
        return chart_dt.astimezone(chart_dt.tzinfo).replace(tzinfo=None)
    return chart_dt


def _safe_html(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _build_bazi_export_payload(
    *,
    chart_name: str,
    birth_place: str,
    dt_local: datetime,
    hour_note: str,
    bazi_data: BaziChartData,
) -> tuple[str, str]:
    year_element = _bilingual(bazi_data.five_elements_summary.get("year"))
    year_zodiac = _bilingual(bazi_data.zodiac_animal)
    year_summary = " • ".join(part for part in (year_element, year_zodiac) if part)
    details_lines = [
        f"Chart of {chart_name}",
        f"Place: {birth_place}",
        f"Date & Time: {dt_local.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Hour Pillar: {hour_note.split(':', 1)[-1].strip()}",
        f"Lunar Date: {_bilingual(bazi_data.lunar_date_str)}",
        f"Year: {year_summary or UNKNOWN_BAZI_VALUE}",
        "",
        "BAZI CHART DETAILS",
    ]
    for pillar in ("year", "month", "day", "hour"):
        details_lines.append(
            f"- {pillar.capitalize()}: "
            f"Stem={_bilingual(bazi_data.heavenly_stems.get(pillar, UNKNOWN_BAZI_VALUE))}; "
            f"Branch={_bilingual(bazi_data.earthly_branches.get(pillar, UNKNOWN_BAZI_VALUE))}"
        )
    details_lines.extend(
        [
            "",
            "Five Elements / Na Yin",
            f"- Year: {_bilingual(bazi_data.five_elements_summary.get('year', UNKNOWN_BAZI_VALUE))}",
            f"- Month: {_bilingual(bazi_data.five_elements_summary.get('month', UNKNOWN_BAZI_VALUE))}",
            f"- Day: {_bilingual(bazi_data.five_elements_summary.get('day', UNKNOWN_BAZI_VALUE))}",
            f"- Hour: {_bilingual(bazi_data.five_elements_summary.get('hour', UNKNOWN_BAZI_VALUE))}",
            "",
            "Ten Gods (relative to Day Master)",
            f"- Year stem: {_bilingual(bazi_data.ten_gods_summary.get('year', UNKNOWN_BAZI_VALUE))}",
            f"- Month stem: {_bilingual(bazi_data.ten_gods_summary.get('month', UNKNOWN_BAZI_VALUE))}",
            f"- Hour stem: {_bilingual(bazi_data.ten_gods_summary.get('hour', UNKNOWN_BAZI_VALUE))}",
            f"- Day branch main: {_bilingual(bazi_data.ten_gods_summary.get('day_branch_main', UNKNOWN_BAZI_VALUE))}",
            "",
        ]
    )
    txt_payload = "\n".join(details_lines)
    md_payload = (
        f"# Chart of {chart_name}\n\n"
        f"- **Place:** {birth_place}\n"
        f"- **Date & Time:** {dt_local.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"- **Hour Pillar:** {hour_note.split(':', 1)[-1].strip()}\n"
        f"- **Lunar Date:** {_bilingual(bazi_data.lunar_date_str)}\n"
        f"- **Year:** {year_summary or UNKNOWN_BAZI_VALUE}\n\n"
        "## BAZI CHART DETAILS\n\n"
        f"- **Year:** Stem={_bilingual(bazi_data.heavenly_stems.get('year', UNKNOWN_BAZI_VALUE))}; "
        f"Branch={_bilingual(bazi_data.earthly_branches.get('year', UNKNOWN_BAZI_VALUE))}\n"
        f"- **Month:** Stem={_bilingual(bazi_data.heavenly_stems.get('month', UNKNOWN_BAZI_VALUE))}; "
        f"Branch={_bilingual(bazi_data.earthly_branches.get('month', UNKNOWN_BAZI_VALUE))}\n"
        f"- **Day:** Stem={_bilingual(bazi_data.heavenly_stems.get('day', UNKNOWN_BAZI_VALUE))}; "
        f"Branch={_bilingual(bazi_data.earthly_branches.get('day', UNKNOWN_BAZI_VALUE))}\n"
        f"- **Hour:** Stem={_bilingual(bazi_data.heavenly_stems.get('hour', UNKNOWN_BAZI_VALUE))}; "
        f"Branch={_bilingual(bazi_data.earthly_branches.get('hour', UNKNOWN_BAZI_VALUE))}\n\n"
        "## Five Elements / Na Yin\n\n"
        f"- **Year:** {_bilingual(bazi_data.five_elements_summary.get('year', UNKNOWN_BAZI_VALUE))}\n"
        f"- **Month:** {_bilingual(bazi_data.five_elements_summary.get('month', UNKNOWN_BAZI_VALUE))}\n"
        f"- **Day:** {_bilingual(bazi_data.five_elements_summary.get('day', UNKNOWN_BAZI_VALUE))}\n"
        f"- **Hour:** {_bilingual(bazi_data.five_elements_summary.get('hour', UNKNOWN_BAZI_VALUE))}\n\n"
        "## Ten Gods (relative to Day Master)\n\n"
        f"- **Year stem:** {_bilingual(bazi_data.ten_gods_summary.get('year', UNKNOWN_BAZI_VALUE))}\n"
        f"- **Month stem:** {_bilingual(bazi_data.ten_gods_summary.get('month', UNKNOWN_BAZI_VALUE))}\n"
        f"- **Hour stem:** {_bilingual(bazi_data.ten_gods_summary.get('hour', UNKNOWN_BAZI_VALUE))}\n"
        f"- **Day branch main:** {_bilingual(bazi_data.ten_gods_summary.get('day_branch_main', UNKNOWN_BAZI_VALUE))}\n"
    )
    return txt_payload, md_payload


def _stem_english_name(stem_char: str) -> str:
    mapping = {
        "甲": "Yang Wood",
        "乙": "Yin Wood",
        "丙": "Yang Fire",
        "丁": "Yin Fire",
        "戊": "Yang Earth",
        "己": "Yin Earth",
        "庚": "Yang Metal",
        "辛": "Yin Metal",
        "壬": "Yang Water",
        "癸": "Yin Water",
    }
    return mapping.get(stem_char, UNKNOWN_BAZI_VALUE)


def _branch_english_name(branch_char: str) -> str:
    return _BRANCH_TO_ZODIAC.get(branch_char, UNKNOWN_BAZI_VALUE)


def _yin_yang_label(char: str) -> str:
    if char in _YANG_STEMS or char in _YANG_BRANCHES:
        return "Yang"
    if char in _YIN_STEMS or char in _YIN_BRANCHES:
        return "Yin"
    return UNKNOWN_BAZI_VALUE


def _pillar_display_row(pillar: str, bazi_data: BaziChartData) -> str:
    stem_char = str(bazi_data.heavenly_stems.get(pillar, "") or "").strip()
    branch_char = str(bazi_data.earthly_branches.get(pillar, "") or "").strip()
    label = pillar.capitalize()
    if stem_char == UNKNOWN_BAZI_VALUE or branch_char == UNKNOWN_BAZI_VALUE:
        muted = CHART_THEME_COLORS["muted_text"]
        return (
            f"<tr><td style='padding:3px 8px;color:{muted};'><b>{label}</b>:</td>"
            f"<td style='padding:3px 8px;color:{muted};'>Unknown</td>"
            f"<td style='padding:3px 8px;color:{muted};'>Unknown</td></tr>"
        )

    stem_english = _stem_english_name(stem_char)
    branch_english = _branch_english_name(branch_char)
    stem_yin_yang = _yin_yang_label(stem_char)
    branch_yin_yang = _yin_yang_label(branch_char)
    stem_roman = _STEM_ROMANIZATION.get(stem_char, UNKNOWN_BAZI_VALUE)
    branch_roman = _BRANCH_ROMANIZATION.get(branch_char, UNKNOWN_BAZI_VALUE)
    stem_element_key = _STEM_ELEMENT.get(stem_char, "earth")
    branch_element_key = _BRANCH_ELEMENT.get(branch_char, "earth")
    stem_color = _color_from_bazi_element(stem_element_key)
    branch_color = _color_from_bazi_element(branch_element_key)
    stem_link = (
        f"<a href='bazi-element:{stem_element_key}' "
        f"style='color:{stem_color}; text-decoration: none;'>"
        f"{_safe_html(stem_english)}</a>"
    )
    zodiac_key = str(branch_english or "").strip().lower()
    branch_link = (
        f"<a href='bazi-zodiac:{zodiac_key}' "
        f"style='color:{branch_color}; text-decoration: none;'>"
        f"{_safe_html(branch_english)}</a>"
    )

    stem_cell = (
        f"{stem_link} "
        f"(<span style='color:{CHART_THEME_COLORS['muted_text']};'>{_safe_html(stem_char)}; "
        f"{_safe_html(stem_yin_yang)} {_safe_html(stem_roman)}</span>)"
    )
    branch_cell = (
        f"{branch_link} "
        f"(<span style='color:{CHART_THEME_COLORS['muted_text']};'>{_safe_html(branch_char)}; "
        f"{_safe_html(branch_yin_yang)} {_safe_html(branch_roman)}</span>)"
    )

    return (
        f"<tr>"
        f"<td style='padding:3px 8px;color:{CHART_THEME_COLORS['text']};'><b>{label}</b>:</td>"
        f"<td style='padding:3px 8px;color:{stem_color};'>{stem_cell}</td>"
        f"<td style='padding:3px 8px;color:{branch_color};'>{branch_cell}</td>"
        f"</tr>"
    )


def build_bazi_details_html(bazi_data: BaziChartData) -> str:
    header_color = CHART_DATA_HIGHLIGHT_COLOR
    text_color = CHART_THEME_COLORS["text"]
    rows = [
        _pillar_display_row("year", bazi_data),
        _pillar_display_row("month", bazi_data),
        _pillar_display_row("day", bazi_data),
        _pillar_display_row("hour", bazi_data),
    ]
    five_elements = [
        f"<b>Year</b>: {_safe_html(_bilingual(str(bazi_data.five_elements_summary['year'])))}",
        f"<b>Month</b>: {_safe_html(_bilingual(str(bazi_data.five_elements_summary['month'])))}",
        f"<b>Day</b>: {_safe_html(_bilingual(str(bazi_data.five_elements_summary['day'])))}",
        f"<b>Hour</b>: {_safe_html(_bilingual(str(bazi_data.five_elements_summary['hour'])))}",
    ]
    ten_gods = [
        f"<b>Year stem</b>: {_safe_html(_bilingual(bazi_data.ten_gods_summary['year']))}",
        f"<b>Month stem</b>: {_safe_html(_bilingual(bazi_data.ten_gods_summary['month']))}",
        f"<b>Hour stem</b>: {_safe_html(_bilingual(bazi_data.ten_gods_summary['hour']))}",
        f"<b>Day branch main</b>: {_safe_html(_bilingual(bazi_data.ten_gods_summary['day_branch_main']))}",
    ]
    return (
        f"<div style='color:{text_color};'>"
        f"<div style='font-weight:700;color:{header_color};margin-bottom:6px;'>BAZI CHART DETAILS</div>"
        "<table style='border-collapse:collapse;width:100%;'>"
        f"<tr><th align='left' style='padding:4px 8px;color:{header_color};font-weight:700;'>Pillar</th>"
        f"<th align='left' style='padding:4px 8px;color:{header_color};font-weight:700;'>Heavenly Stem</th>"
        f"<th align='left' style='padding:4px 8px;color:{header_color};font-weight:700;'>Earthly Branch</th></tr>"
        f"{''.join(rows)}"
        "</table>"
        f"<div style='margin-top:10px;font-weight:700;color:{header_color};'>Five Elements / Na Yin</div>"
        f"<div>{'<br>'.join(five_elements)}</div>"
        f"<div style='margin-top:10px;font-weight:700;color:{header_color};'>Ten Gods (relative to Day Master)</div>"
        f"<div>{'<br>'.join(ten_gods)}</div>"
        "</div>"
    )


def _build_five_element_counts(bazi_data: BaziChartData) -> dict[str, int]:
    counts = {element: 0 for element in _ELEMENT_CHAR_TO_NAME.values()}
    for pillar in ("year", "month", "day", "hour"):
        wuxing_value = str(bazi_data.five_elements_summary.get(pillar, "") or "")
        if wuxing_value == UNKNOWN_BAZI_VALUE:
            continue
        for char in wuxing_value:
            element = _ELEMENT_CHAR_TO_NAME.get(char)
            if element:
                counts[element] += 1
    return counts


def _build_zodiac_counts(bazi_data: BaziChartData) -> dict[str, int]:
    counts = {animal: 0 for animal in _ZODIAC_ORDER}
    for branch in bazi_data.earthly_branches.values():
        zodiac = _BRANCH_TO_ZODIAC.get(str(branch))
        if zodiac:
            counts[zodiac] += 1
    return counts


def _build_yin_yang_counts(bazi_data: BaziChartData) -> dict[str, int]:
    yin = 0
    yang = 0
    for stem in bazi_data.heavenly_stems.values():
        if stem in _YANG_STEMS:
            yang += 1
        elif stem in _YIN_STEMS:
            yin += 1
    for branch in bazi_data.earthly_branches.values():
        if branch in _YANG_BRANCHES:
            yang += 1
        elif branch in _YIN_BRANCHES:
            yin += 1
    return {"yin": yin, "yang": yang}


def _style_chart_axes(ax: Any) -> None:
    ax.set_facecolor(CHART_THEME_COLORS["background"])
    for spine in ax.spines.values():
        spine.set_color(CHART_THEME_COLORS["spine"])


def _build_elements_pie_canvas(bazi_data: BaziChartData) -> FigureCanvas:
    counts = _build_five_element_counts(bazi_data)
    labels = list(_BAZI_ELEMENT_PIE_ORDER)
    values = [counts[label] for label in labels]
    colors = [_color_from_bazi_element(label, CHART_THEME_COLORS["accent"]) for label in labels]

    figure = Figure(figsize=(3.4, 2.4))
    figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
    ax = figure.add_subplot(111)
    _style_chart_axes(ax)
    total = sum(values)
    if total <= 0:
        ax.text(0.5, 0.5, "No element data", ha="center", va="center", color=CHART_THEME_COLORS["text"])
        ax.set_axis_off()
    else:
        ax.pie(
            values,
            colors=colors,
            startangle=STANDARD_NCV_PIE_CHART["start_angle"],
            wedgeprops={"edgecolor": STANDARD_NCV_PIE_CHART["wedge_edge_color"]},
        )
        legend_handles = [
            Patch(
                facecolor=color,
                label=STANDARD_NCV_PIE_CHART["legend_label_format"].format(
                    percent=(value / total) * 100,
                    label=label.capitalize(),
                ),
            )
            for label, color, value in zip(labels, colors, values, strict=True)
        ]
        # Keep this legend in two rows (2 items on top, 3 on bottom) so all
        # keys remain visible in the right-hand BaZi panel.
        top_row_legend = ax.legend(
            handles=legend_handles[:2],
            loc="upper center",
            bbox_to_anchor=(0.5, -0.03),
            frameon=False,
            labelcolor=STANDARD_NCV_PIE_CHART["legend_label_color"],
            fontsize=STANDARD_NCV_PIE_CHART["legend_font_size"],
            ncol=2,
        )
        ax.add_artist(top_row_legend)
        ax.legend(
            handles=legend_handles[2:],
            loc="upper center",
            bbox_to_anchor=(0.5, -0.12),
            frameon=False,
            labelcolor=STANDARD_NCV_PIE_CHART["legend_label_color"],
            fontsize=STANDARD_NCV_PIE_CHART["legend_font_size"],
            ncol=3,
        )
        ax.figure.subplots_adjust(left=0.12, right=0.88, bottom=0.36, top=0.92)
    return FigureCanvas(figure)


def _build_zodiac_bar_canvas(
    bazi_data: BaziChartData,
    *,
    on_zodiac_selected: Callable[[str], None] | None = None,
) -> FigureCanvas:
    counts = _build_zodiac_counts(bazi_data)
    labels = list(_ZODIAC_ORDER)
    values = [counts[label] for label in labels]

    figure = Figure(figsize=(3.4, 2.7))
    figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
    ax = figure.add_subplot(111)
    _style_chart_axes(ax)

    zodiac_colors = [
        str(BAZI_ZODIAC.get(label.lower(), {}).get("color", CHART_THEME_COLORS["accent"]))
        for label in labels
    ]
    bars = ax.bar(labels, values, color=zodiac_colors)
    ax.set_ylim(0, max(1, (max(values) if values else 0) + 1))
    ax.margins(x=STANDARD_NCV_HORIZONTAL_BAR_CHART["x_margin"])
    ax.tick_params(
        axis="x",
        labelrotation=90,
        labelsize=7,
        colors=CHART_THEME_COLORS["text"],
        pad=STANDARD_NCV_HORIZONTAL_BAR_CHART["x_tick_pad"],
    )
    ax.tick_params(axis="y", labelsize=7, colors=CHART_THEME_COLORS["text"])
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + (bar.get_width() / 2),
            height + 0.05,
            f"{int(height)}",
            ha="center",
            va="bottom",
            color=CHART_THEME_COLORS["text"],
            fontsize=6.5,
        )
    ax.figure.subplots_adjust(
        left=STANDARD_NCV_HORIZONTAL_BAR_CHART["left"],
        bottom=0.38,
        top=STANDARD_NCV_HORIZONTAL_BAR_CHART["top"],
        right=STANDARD_NCV_HORIZONTAL_BAR_CHART["right"],
    )
    canvas = FigureCanvas(figure)
    if callable(on_zodiac_selected):
        def _on_click(event: Any) -> None:
            if event is None or event.inaxes is not ax:
                return
            for index, bar in enumerate(bars):
                contains, _ = bar.contains(event)
                if contains:
                    on_zodiac_selected(labels[index].lower())
                    return
        canvas.mpl_connect("button_press_event", _on_click)
    return canvas


def _build_yin_yang_pie_canvas(bazi_data: BaziChartData) -> FigureCanvas:
    counts = _build_yin_yang_counts(bazi_data)
    labels = ["yang", "yin"]
    values = [counts["yang"], counts["yin"]]
    colors = ["#ff0000", "#00aa00"]

    figure = Figure(figsize=(3.4, 2.3))
    figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
    ax = figure.add_subplot(111)
    _style_chart_axes(ax)
    total = sum(values)
    if total <= 0:
        ax.text(0.5, 0.5, "No yin/yang data", ha="center", va="center", color=CHART_THEME_COLORS["text"])
        ax.set_axis_off()
    else:
        non_zero_pairs = [
            (label, color, value)
            for label, color, value in zip(labels, colors, values, strict=True)
            if value > 0
        ]
        pie_values = [value for _, _, value in non_zero_pairs]
        pie_colors = [color for _, color, _ in non_zero_pairs]
        pie_wedge_edge_color = (
            "none"
            if len(non_zero_pairs) == 1
            else STANDARD_NCV_PIE_CHART["wedge_edge_color"]
        )
        ax.pie(
            pie_values,
            colors=pie_colors,
            startangle=STANDARD_NCV_PIE_CHART["start_angle"],
            wedgeprops={"edgecolor": pie_wedge_edge_color},
        )
        legend_handles = [
            Patch(
                facecolor=color,
                label=STANDARD_NCV_PIE_CHART["legend_label_format"].format(
                    percent=(value / total) * 100,
                    label=label.capitalize(),
                ),
            )
            for label, color, value in zip(labels, colors, values, strict=True)
        ]
        ax.legend(
            handles=legend_handles,
            loc=STANDARD_NCV_PIE_CHART["legend_loc"],
            bbox_to_anchor=STANDARD_NCV_PIE_CHART["legend_anchor"],
            frameon=False,
            labelcolor=STANDARD_NCV_PIE_CHART["legend_label_color"],
            fontsize=STANDARD_NCV_PIE_CHART["legend_font_size"],
            ncol=STANDARD_NCV_PIE_CHART["legend_ncol"],
        )
        ax.figure.subplots_adjust(**STANDARD_NCV_PIE_CHART["subplots_adjust"])
    return FigureCanvas(figure)


def create_bazi_window_dialog(
    parent: Any,
    chart: Chart,
    *,
    header_style: str,
    share_icon_path: str | None = None,
) -> QDialog:
    dt_local = resolve_bazi_birth_datetime(chart)
    has_known_birth_hour = (
        not bool(getattr(chart, "birthtime_unknown", False))
        or (
            bool(getattr(chart, "retcon_time_used", False))
            and getattr(chart, "retcon_hour", None) is not None
            and getattr(chart, "retcon_minute", None) is not None
        )
    )
    bazi_data = build_bazi_chart_data(dt_local, include_hour=has_known_birth_hour)
    chart_name = (getattr(chart, "name", None) or "Chart").strip() or "Chart"
    birth_place = str(getattr(chart, "birth_place", "") or "").strip()
    hour_note = (
        "Hour pillar source: Rectified time"
        if bool(getattr(chart, "birthtime_unknown", False))
        and bool(getattr(chart, "retcon_time_used", False))
        and has_known_birth_hour
        else (
            "Hour pillar source: Unknown birth time (hour-dependent values shown as Unknown)"
            if not has_known_birth_hour
            else "Hour pillar source: Birth time"
        )
    )

    dialog = QDialog(parent)
    dialog.setAttribute(Qt.WA_DeleteOnClose)
    dialog.setWindowTitle(f"Bazi Window • {chart_name}")
    dialog.resize(1080, 760)

    layout = QHBoxLayout(dialog)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(10)

    left_panel = QWidget(dialog)
    left_layout = QVBoxLayout(left_panel)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(8)

    year_element = _bilingual(bazi_data.five_elements_summary.get("year"))
    year_zodiac = _bilingual(bazi_data.zodiac_animal)
    year_summary = " • ".join(part for part in (year_element, year_zodiac) if part)

    summary_label = QLabel(
        "<br>".join(
            [
                f"<span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Chart of </span>"
                f"<span style='font-weight:400;color:{CHART_THEME_COLORS['text']};'>{_safe_html(chart_name)}</span>",
                f"<span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Place:</span> "
                f"<span style='font-weight:400;color:{CHART_THEME_COLORS['text']};'>{_safe_html(birth_place)}</span>",
                f"<span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Date & Time:</span> "
                f"<span style='font-weight:400;color:{CHART_THEME_COLORS['text']};'>{dt_local.strftime('%Y-%m-%d %H:%M:%S')}</span>",
                f"<span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Hour Pillar:</span> "
                f"<span style='font-weight:400;color:{CHART_THEME_COLORS['text']};'>{_safe_html(hour_note.split(':', 1)[-1].strip())}</span>",
                f"<span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Lunar Date:</span> "
                f"<span style='font-weight:400;color:{CHART_THEME_COLORS['text']};'>{_safe_html(_bilingual(bazi_data.lunar_date_str))}</span>",
                f"<span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Year:</span> "
                f"<span style='font-weight:400;color:{CHART_THEME_COLORS['text']};'>{_safe_html(year_summary or UNKNOWN_BAZI_VALUE)}</span>",
            ]
        )
    )
    summary_label.setStyleSheet(header_style)
    summary_label.setTextFormat(Qt.RichText)
    summary_label.setWordWrap(True)
    left_layout.addWidget(summary_label, 0)

    txt_payload, md_payload = _build_bazi_export_payload(
        chart_name=chart_name,
        birth_place=birth_place,
        dt_local=dt_local,
        hour_note=hour_note,
        bazi_data=bazi_data,
    )

    def _on_export_bazi() -> None:
        default_stem = "".join(ch.lower() if ch.isalnum() else "_" for ch in chart_name).strip("_") or "chart"
        default_name = f"{default_stem}-bazi.md"
        file_path, selected_filter = QFileDialog.getSaveFileName(
            dialog,
            "Export BaZi chart",
            default_name,
            "Markdown (*.md);;Text (*.txt)",
        )
        if not file_path:
            return
        chosen_filter = (selected_filter or "").lower()
        wants_txt = "text" in chosen_filter
        path_lower = file_path.lower()
        if path_lower.endswith(".md"):
            output_text = md_payload
        elif path_lower.endswith(".txt"):
            output_text = txt_payload
        elif wants_txt:
            file_path = f"{file_path}.txt"
            output_text = txt_payload
        else:
            file_path = f"{file_path}.md"
            output_text = md_payload
        try:
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write(output_text)
        except Exception as exc:
            QMessageBox.critical(dialog, "Export failed", f"Could not export BaZi chart:\n{exc}")
            return
        QMessageBox.information(dialog, "Export complete", f"Saved BaZi chart to:\n{file_path}")

    details_output = QTextBrowser()
    details_output.setReadOnly(True)
    details_output.setPlaceholderText("BaZi chart details unavailable.")
    details_output.setOpenExternalLinks(False)
    details_output.setOpenLinks(False)
    details_output.setHtml(build_bazi_details_html(bazi_data))
    left_layout.addWidget(details_output, 1)

    chart_info_header = QLabel("Chart Info")
    chart_info_header.setStyleSheet(header_style)
    left_layout.addWidget(chart_info_header, 0)

    chart_info_panel = QLabel(
        "\n".join(
            [
                f"Birthtime unknown: {bool(getattr(chart, 'birthtime_unknown', False))}",
                f"Rectified time used: {bool(getattr(chart, 'retcon_time_used', False))}",
                f"Hour included in BaZi: {has_known_birth_hour}",
                f"Timezone fallback used: {bool(getattr(chart, 'used_utc_fallback', False))}",
            ]
        )
    )
    chart_info_panel.setStyleSheet(
        f"color: {CHART_THEME_COLORS['text']}; "
        f"border: 1px solid {CHART_THEME_COLORS['spine']}; "
        "padding: 8px;"
    )
    chart_info_panel.setWordWrap(True)
    left_layout.addWidget(chart_info_panel, 0)

    default_chart_info_text = chart_info_panel.text()

    def _set_chart_info_panel_content(title: str, body: str) -> None:
        chart_info_panel.setText(
            "<div>"
            f"<span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>{_safe_html(title)}</span><br>"
            f"<span style='font-weight:400;color:{CHART_THEME_COLORS['text']};'>{_safe_html(body)}</span>"
            "</div>"
        )

    def _show_zodiac_info(zodiac_key: str) -> None:
        normalized_key = str(zodiac_key or "").strip().lower()
        zodiac_data = BAZI_ZODIAC.get(normalized_key, {})
        if not isinstance(zodiac_data, dict):
            chart_info_panel.setText(default_chart_info_text)
            return
        summary = str(zodiac_data.get("one_liner", "") or "").strip()
        if not summary:
            chart_info_panel.setText(default_chart_info_text)
            return
        _set_chart_info_panel_content(f"Zodiac: {normalized_key.capitalize()}", summary)

    def _on_details_link_clicked(url: QUrl) -> None:
        raw_target = str(url.toString() or "").strip()
        target_type, _, target_key = raw_target.partition(":")
        normalized_type = target_type.strip().lower()
        normalized_key = target_key.strip().lower()
        summary = ""
        info_title = ""
        if normalized_type == "bazi-element":
            element_data = BAZI_ELEMENTS.get(normalized_key, {})
            if isinstance(element_data, dict):
                summary = str(element_data.get("one_liner", "") or "").strip()
                info_title = f"Element: {normalized_key.capitalize()}"
        elif normalized_type == "bazi-zodiac":
            _show_zodiac_info(normalized_key)
            return
        if not summary or not info_title:
            chart_info_panel.setText(default_chart_info_text)
            return
        _set_chart_info_panel_content(info_title, summary)

    details_output.anchorClicked.connect(_on_details_link_clicked)

    right_panel = QWidget(dialog)
    right_layout = QVBoxLayout(right_panel)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(6)

    right_header_row = QHBoxLayout()
    right_header_row.setContentsMargins(0, 0, 0, 0)
    right_header_row.setSpacing(4)

    charts_header = QLabel("BaZi Analytics")
    charts_header.setStyleSheet(header_style)
    right_header_row.addWidget(charts_header, 0, Qt.AlignLeft | Qt.AlignTop)
    right_header_row.addStretch(1)

    export_button = QToolButton(dialog)
    configure_share_export_icon_button(
        export_button,
        share_icon_path=share_icon_path,
        tooltip="Export BaZi chart as Markdown or text",
    )
    export_button.clicked.connect(_on_export_bazi)
    right_header_row.addWidget(export_button, 0, Qt.AlignRight | Qt.AlignTop)
    right_layout.addLayout(right_header_row, 0)

    elements_title = QLabel("Five Elements")
    elements_title.setStyleSheet(header_style)
    right_layout.addWidget(elements_title, 0)
    right_layout.addWidget(_build_elements_pie_canvas(bazi_data), 1)

    zodiac_title = QLabel("12 Zodiac Animals")
    zodiac_title.setStyleSheet(header_style)
    right_layout.addWidget(zodiac_title, 0)
    right_layout.addWidget(
        _build_zodiac_bar_canvas(
            bazi_data,
            on_zodiac_selected=_show_zodiac_info,
        ),
        1,
    )

    yin_yang_title = QLabel("Yin / Yang Balance")
    yin_yang_title.setStyleSheet(header_style)
    right_layout.addWidget(yin_yang_title, 0)
    right_layout.addWidget(_build_yin_yang_pie_canvas(bazi_data), 1)

    layout.addWidget(left_panel, 3)
    layout.addWidget(right_panel, 4)

    return dialog
