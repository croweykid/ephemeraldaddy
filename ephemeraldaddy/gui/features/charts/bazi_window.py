from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QPlainTextEdit, QVBoxLayout, QWidget, QHBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from ephemeraldaddy.analysis.bazi_getter import BaziChartData, build_bazi_chart_data
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.interpretations import BAZI_ELEMENTS
from ephemeraldaddy.gui.style import (
    CHART_THEME_COLORS,
    STANDARD_NCV_HORIZONTAL_BAR_CHART,
    STANDARD_NCV_PIE_CHART,
)

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


def _build_five_element_counts(bazi_data: BaziChartData) -> dict[str, int]:
    counts = {element: 0 for element in _ELEMENT_CHAR_TO_NAME.values()}
    for pillar in ("year", "month", "day", "hour"):
        wuxing_value = str(bazi_data.five_elements_summary.get(pillar, "") or "")
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
    labels = ["wood", "water", "earth", "fire", "metal"]
    values = [counts[label] for label in labels]
    colors = [BAZI_ELEMENTS[label] for label in labels]

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


def _build_zodiac_bar_canvas(bazi_data: BaziChartData) -> FigureCanvas:
    counts = _build_zodiac_counts(bazi_data)
    labels = list(_ZODIAC_ORDER)
    values = [counts[label] for label in labels]

    figure = Figure(figsize=(3.4, 2.7))
    figure.patch.set_facecolor(CHART_THEME_COLORS["background"])
    ax = figure.add_subplot(111)
    _style_chart_axes(ax)

    bars = ax.bar(labels, values, color="#6fa8dc")
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
    return FigureCanvas(figure)


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
    monospace_font_family: str,
) -> QDialog:
    dt_local = resolve_bazi_birth_datetime(chart)
    bazi_data = build_bazi_chart_data(dt_local)
    chart_name = (getattr(chart, "name", None) or "Chart").strip() or "Chart"
    birth_place = str(getattr(chart, "birth_place", "") or "").strip()

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
    left_layout.addWidget(summary_label, 0)

    details_output = QPlainTextEdit()
    details_output.setReadOnly(True)
    details_font = details_output.font()
    details_font.setFamily(monospace_font_family)
    details_output.setFont(details_font)
    details_output.setPlaceholderText("BaZi chart details unavailable.")
    details_output.setPlainText("\n".join(build_bazi_details_lines(bazi_data)))
    left_layout.addWidget(details_output, 1)

    right_panel = QWidget(dialog)
    right_layout = QVBoxLayout(right_panel)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(6)

    charts_header = QLabel("BaZi Analytics")
    charts_header.setStyleSheet(header_style)
    right_layout.addWidget(charts_header, 0)

    elements_title = QLabel("Five Elements")
    elements_title.setStyleSheet("font-weight: 600; color: #f5f5f5;")
    right_layout.addWidget(elements_title, 0)
    right_layout.addWidget(_build_elements_pie_canvas(bazi_data), 1)

    zodiac_title = QLabel("12 Zodiac Animals")
    zodiac_title.setStyleSheet("font-weight: 600; color: #f5f5f5;")
    right_layout.addWidget(zodiac_title, 0)
    right_layout.addWidget(_build_zodiac_bar_canvas(bazi_data), 1)

    yin_yang_title = QLabel("Yin / Yang Balance")
    yin_yang_title.setStyleSheet("font-weight: 600; color: #f5f5f5;")
    right_layout.addWidget(yin_yang_title, 0)
    right_layout.addWidget(_build_yin_yang_pie_canvas(bazi_data), 1)

    layout.addWidget(left_panel, 3)
    layout.addWidget(right_panel, 2)

    return dialog
