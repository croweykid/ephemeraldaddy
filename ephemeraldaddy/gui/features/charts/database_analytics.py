"""Database View analytics chart rendering helpers."""

from __future__ import annotations

import copy
import hashlib
import datetime
import csv
import html
import json
import logging
import math
import re
import statistics
import textwrap
import time
import warnings
from collections import Counter
from typing import Any, Callable, Mapping, Sequence

from matplotlib import font_manager as mpl_font_manager
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QEvent, QPoint, QSize, Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLayout,
    QScrollArea,
    QMessageBox,
    QSizePolicy,
    QTextEdit,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.gui.features.charts.dnd_predictions import DND_STAT_KEYS

DATABASE_METRICS_SECTION_ORDER: tuple[str, ...] = (
    "planetary_sign_prevalence",
    "sentiment_prevalence",
    "relationship_prevalence",
    "alignment_summary",
    "matched_expectations_summary",
    "sign_prevalence",
    "dominant_signs",
    "decans",
    "nakshatras",
    "cumulativedom_factors",
    "enneagram",
    "species_distribution",
    "birth_time",
    "age",
    "birth_month",
    "birthplace",
    "tag_distribution",
    "traits_distribution",
    "gender",
    "human_design",
    "bazi",
)
TRAITS_DISTRIBUTION_LIKELIHOOD_CACHE_VERSION = 2
TRAITS_DISTRIBUTION_LIKELIHOOD_CACHE_FILENAME = ".traits_distribution_likelihood_cache.json"
TRAITS_DISTRIBUTION_LIKELIHOOD_CACHE_MAX_ENTRIES = 100_000
TRAITS_DISTRIBUTION_SCORING_TIME_BUDGET_SECONDS = 8.0
TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD = 5.0
DATABASE_METRICS_BIRTH_DATA_SECTIONS: frozenset[str] = frozenset(
    {
        "planetary_sign_prevalence",
        "sign_prevalence",
        "dominant_signs",
        "decans",
        "nakshatras",
        "cumulativedom_factors",
        "enneagram",
        "species_distribution",
        "birth_time",
        "age",
        "birth_month",
        "birthplace",
        "gender",
        "human_design",
        "bazi",
    }
)
DATABASE_METRICS_SUBJECTIVE_SECTION_DEPENDENCIES: dict[str, frozenset[str]] = {
    "sentiments": frozenset({"sentiment_prevalence"}),
    "relationship_types": frozenset({"relationship_prevalence"}),
    "alignment": frozenset({"alignment_summary"}),
    "matched_expectations": frozenset({"matched_expectations_summary"}),
    "gender": frozenset({"gender"}),
    "tags": frozenset({"tag_distribution"}),
    "traits": frozenset({"traits_distribution"}),
}


def database_metrics_sections_for_changed_fields(
    changed_fields: set[str] | frozenset[str] | None,
) -> frozenset[str]:
    """Return the Database Analytics sections affected by edited chart fields."""
    if changed_fields is None:
        return frozenset(DATABASE_METRICS_SECTION_ORDER)
    if not changed_fields:
        return frozenset()
    sections: set[str] = set()
    for field in changed_fields:
        if field == "birth_data":
            sections.update(DATABASE_METRICS_BIRTH_DATA_SECTIONS)
            continue
        sections.update(
            DATABASE_METRICS_SUBJECTIVE_SECTION_DEPENDENCIES.get(field, frozenset())
        )
    return frozenset(sections)


class DatabaseAnalyticsPopoutScrollArea(QScrollArea):
    """Scroll area that keeps popout charts width-bound while preserving vertical scroll."""

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.StrongFocus)
        self.verticalScrollBar().setFocusPolicy(Qt.StrongFocus)
        self.viewport().installEventFilter(self)

    def setWidget(self, widget: object) -> None:  # noqa: N802 - Qt API
        super().setWidget(widget)
        if hasattr(widget, "installEventFilter"):
            widget.installEventFilter(self)
        self._sync_chart_width()

    def resizeEvent(self, event: object) -> None:  # noqa: N802 - Qt API
        super().resizeEvent(event)
        self._sync_chart_width()

    def eventFilter(self, watched: object, event: object) -> bool:  # noqa: N802 - Qt API
        event_type = event.type() if hasattr(event, "type") else None
        if event_type == QEvent.MouseButtonPress:
            self._focus_vertical_scrollbar()
        if event_type == QEvent.Wheel:
            chart_widget = self.widget()
            if watched not in {self, self.viewport(), chart_widget}:
                return False
            self._focus_vertical_scrollbar()
            delta = event.pixelDelta().y() if hasattr(event, "pixelDelta") else 0
            if not delta and hasattr(event, "angleDelta"):
                delta = event.angleDelta().y()
            if delta:
                bar = self.verticalScrollBar()
                bar.setValue(bar.value() - int(delta))
                event.accept()
                return True
            return False
        return super().eventFilter(watched, event)

    def wheelEvent(self, event: object) -> None:  # noqa: N802 - Qt API
        self._focus_vertical_scrollbar()
        super().wheelEvent(event)

    def _focus_vertical_scrollbar(self) -> None:
        self.setFocus(Qt.MouseFocusReason)
        self.verticalScrollBar().setFocus(Qt.MouseFocusReason)

    def _sync_chart_width(self) -> None:
        widget = self.widget()
        if widget is None:
            return
        viewport_width = max(1, self.viewport().width())
        current_height = max(1, widget.minimumHeight(), widget.height(), widget.sizeHint().height())
        widget.setMinimumWidth(1)
        widget.setMaximumWidth(viewport_width)
        widget.resize(viewport_width, current_height)

from ephemeraldaddy.data.genpop import (
    INNER_PLANET_SIGN_DISTRIBUTION_AGGREGATED,
    SUN_SIGN_DISTRIBUTION_AGGREGATED,
)
from ephemeraldaddy.analysis.country_lookup import normalize_country, resolve_country
from ephemeraldaddy.analysis.city_lookup import normalize_city
from ephemeraldaddy.analysis.us_state_lookup import normalize_us_state
from ephemeraldaddy.core.interpretations import (
    AGE_BRACKETS,
    BAZI_ZODIAC,
    ENNEAGRAM,
    ELEMENT_COLORS,
    MODE_COLORS,
    HOUSE_COLORS,
    NAKSHATRA_RANGES,
    NAKSHATRA_PLANET_COLOR,
    PLANET_COLORS,
    RELATION_TYPE,
    SENTIMENT_COLORS,
    SIGN_COLORS,
    ZODIAC_NAMES,
)
from ephemeraldaddy.analysis.human_design import (
    build_human_design_result,
    derive_human_design_profile,
)
from ephemeraldaddy.analysis.hd_incarnation_crosses import (
    find_cross_by_name,
    find_crosses_by_gates,
    get_cross_theme_description,
    get_cross_type_description,
)
from ephemeraldaddy.analysis.bazi_getter import build_bazi_chart_data
from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.analysis.human_design_reference import (
    HD_AUTHORITIES,
    HD_AUTHORITY_COLORS,
    HD_CENTERS,
    HD_TYPES,
    authority_key_to_label,
    canonicalize_hd_authority_label,
    normalize_hd_authority_key,
)
from ephemeraldaddy.gui.features.charts.presentation import (
    abbreviate_nakshatra_label as _abbreviate_nakshatra_label,
    format_percent as _format_percent,
    get_nakshatra,
)
from ephemeraldaddy.gui.features.charts.sign_distribution import SIGN_DISTRIBUTION_DROPDOWN_OPTIONS
from ephemeraldaddy.gui.features.charts.statistical_significance import (
    compute_proportion_significance_results,
    draw_standard_deviation_guides,
    typical_standard_error,
)
from ephemeraldaddy.gui.features.charts.provenance import chart_is_non_aggregable
from ephemeraldaddy.gui.features.charts.tagging import normalize_tag_list
from ephemeraldaddy.analysis.traits import (
    DEFAULT_TRAIT_COLOR,
    calculate_trait_likelihoods,
    list_traits,
    normalize_trait_color,
    trait_possible_score,
)
from ephemeraldaddy.core import db
from ephemeraldaddy.gui.features.charts.enneagram_predictions import (
    build_enneagram_popout_info_html,
    calculate_enneagram_type_weights as _calculate_enneagram_type_weights,
)
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_house_weights as _calculate_dominant_house_weights,
    calculate_dominant_planet_weights as _calculate_dominant_planet_weights,
    calculate_dominant_sign_weights as _calculate_dominant_sign_weights,
)
from ephemeraldaddy.gui.features.charts.bazi_window import (
    resolve_bazi_birth_datetime,
    validate_chart_for_bazi,
)
from ephemeraldaddy.gui.style import (
    ALIGNMENT_CUMULATIVE_SUBTITLE_WRAP_WIDTH,
    CHART_AXES_STYLE,
    CHART_DATA_HIGHLIGHT_COLOR,
    CHART_THEME_COLORS,
    DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS,
    DATABASE_ANALYTICS_GRAPH_AREA_DEBUG_COLOR,
    DATABASE_ANALYTICS_GRAPH_LABEL_REGION_DEBUG_COLOR,
    DATABASE_ANALYTICS_SUBHEADER_STYLE,
    DATABASE_ANALYTICS_SUBTITLE_DEBUG_STYLE,
    DND_STAT_EARTHTONE_COLORS,
    DATABASE_VIEW_SUBHEADER_WORD_WRAP,
    GENDER_GUESSER_COLORS,
    apply_popout_cursor,
    get_cycled_earthtone_colors,
    value_to_red_blue_rgb,
)

logger = logging.getLogger(__name__)


def _gen_pop_decan_counts(sample_size: int) -> list[int]:
    if sample_size <= 0:
        return [0, 0, 0]
    base = sample_size // 3
    remainder = sample_size % 3
    return [base + (1 if idx < remainder else 0) for idx in range(3)]


def _gen_pop_nakshatra_counts(sample_size: int, label_count: int) -> list[int]:
    if sample_size <= 0 or label_count <= 0:
        return [0] * max(0, label_count)
    base = sample_size // label_count
    remainder = sample_size % label_count
    return [base + (1 if idx < remainder else 0) for idx in range(label_count)]

def _gen_pop_sign_norms_for_body(body: str) -> dict[str, float]:
    if body == "Sun":
        return {
            sign: float(details.get("percent", 0.0)) / 100.0
            for sign, details in SUN_SIGN_DISTRIBUTION_AGGREGATED.items()
        }
    if body in {"Mercury", "Venus"}:
        aggregated = INNER_PLANET_SIGN_DISTRIBUTION_AGGREGATED.get(body, {})
        return {
            sign: float(details.get("percent", 0.0)) / 100.0
            for sign, details in aggregated.items()
        }
    equal = 1.0 / float(len(ZODIAC_NAMES))
    return {sign: equal for sign in ZODIAC_NAMES}


def _gen_pop_nakshatra_counts_for_body(*, body: str, sample_size: int, labels: list[str]) -> list[int]:
    if sample_size <= 0:
        return [0 for _ in labels]
    sign_norms = _gen_pop_sign_norms_for_body(body)
    # Use a fine-grained grid to map sign-weighted longitude likelihood to nakshatras.
    # This keeps the baseline tied to the same aggregated birth data used by sign prevalence.
    points_per_sign = 600
    total_points = points_per_sign * len(ZODIAC_NAMES)
    nak_probs = {label: 0.0 for label in labels}
    for sign_idx, sign in enumerate(ZODIAC_NAMES):
        sign_weight = float(sign_norms.get(sign, 0.0))
        if sign_weight <= 0:
            continue
        per_point_weight = sign_weight / float(points_per_sign)
        sign_start = float(sign_idx * 30.0)
        step = 30.0 / float(points_per_sign)
        for point in range(points_per_sign):
            longitude = sign_start + ((point + 0.5) * step)
            nak_label = str(get_nakshatra(longitude)).strip()
            if nak_label in nak_probs:
                nak_probs[nak_label] += per_point_weight
    raw_counts = [nak_probs[label] * float(sample_size) for label in labels]
    rounded = [int(value) for value in raw_counts]
    remainder = int(sample_size - sum(rounded))
    if remainder > 0:
        fractional = sorted(
            enumerate(raw_counts),
            key=lambda item: (item[1] - int(item[1])),
            reverse=True,
        )
        for idx, _ in fractional[:remainder]:
            rounded[idx] += 1
    return rounded




DECAN_STABLE_BLUE_COLORS = ["#1f4e79", "#2f75b5", "#6fa8dc"]


def decan_bar_colors() -> list[str]:
    """Stable decan color mapping (Decan 1/2/3)."""
    return list(DECAN_STABLE_BLUE_COLORS)


def nakshatra_bar_colors(labels: list[str]) -> list[str]:
    """Resolve each nakshatra bar color from interpretations.py metadata."""
    fallback = "#6fa8dc"
    colors: list[str] = []
    for label in labels:
        _ruler, color = NAKSHATRA_PLANET_COLOR.get(str(label), (None, fallback))
        colors.append(str(color).strip() or fallback)
    return colors

def _decan_baseline_counts(*, baseline_mode: str, database_counts: list[int]) -> list[int]:
    if baseline_mode != "gen_pop":
        return list(database_counts)
    return _gen_pop_decan_counts(sum(int(count) for count in database_counts))


def _nakshatra_baseline_counts(*, baseline_mode: str, database_counts: list[int], label_count: int) -> list[int]:
    if baseline_mode != "gen_pop":
        return list(database_counts)
    return _gen_pop_nakshatra_counts(sum(int(count) for count in database_counts), label_count)


def decans_dropdown_options() -> list[tuple[str, str]]:
    return list(SIGN_DISTRIBUTION_DROPDOWN_OPTIONS)


def nakshatras_dropdown_options() -> list[tuple[str, str]]:
    return list(SIGN_DISTRIBUTION_DROPDOWN_OPTIONS)


def decans_empty_cache_fields() -> dict[str, Any]:
    return {
        "position_decan_totals_by_body": {
            body: {1: 0, 2: 0, 3: 0}
            for _label, body in SIGN_DISTRIBUTION_DROPDOWN_OPTIONS
        },
        "position_decan_count_by_body": {
            body: 0.0 for _label, body in SIGN_DISTRIBUTION_DROPDOWN_OPTIONS
        },
    }


def nakshatras_empty_cache_fields() -> dict[str, Any]:
    nakshatra_labels = [str(name) for name, *_ in NAKSHATRA_RANGES]
    return {
        "position_nakshatra_totals_by_body": {
            body: {label: 0 for label in nakshatra_labels}
            for _label, body in SIGN_DISTRIBUTION_DROPDOWN_OPTIONS
        },
        "position_nakshatra_count_by_body": {
            body: 0.0 for _label, body in SIGN_DISTRIBUTION_DROPDOWN_OPTIONS
        },
    }


def snapshot_add_decan(snapshot: dict[str, Any], body: str, longitude: float) -> None:
    decan_number = min(3, max(1, int((float(longitude) % 30.0) // 10.0) + 1))
    snapshot["position_decan_totals_by_body"][body][decan_number] += 1
    snapshot["position_decan_count_by_body"][body] += 1


def snapshot_add_nakshatra(snapshot: dict[str, Any], body: str, longitude: float) -> None:
    nakshatra_name = str(get_nakshatra(float(longitude))).strip()
    if not nakshatra_name:
        return
    totals_by_body = snapshot.get("position_nakshatra_totals_by_body", {})
    body_totals = totals_by_body.get(body)
    if body_totals is None or nakshatra_name not in body_totals:
        return
    body_totals[nakshatra_name] += 1
    snapshot["position_nakshatra_count_by_body"][body] += 1


def apply_decan_snapshot_delta(totals: dict[str, Any], snapshot: dict[str, Any], direction: int) -> None:
    for body, count in snapshot.get("position_decan_count_by_body", {}).items():
        totals["position_decan_count_by_body"][body] += direction * float(count)
    for body, decan_totals in snapshot.get("position_decan_totals_by_body", {}).items():
        for decan in (1, 2, 3):
            totals["position_decan_totals_by_body"][body][decan] += direction * int(decan_totals.get(decan, 0))


def apply_nakshatra_snapshot_delta(totals: dict[str, Any], snapshot: dict[str, Any], direction: int) -> None:
    for body, count in snapshot.get("position_nakshatra_count_by_body", {}).items():
        totals["position_nakshatra_count_by_body"][body] += direction * float(count)
    for body, nakshatra_totals in snapshot.get("position_nakshatra_totals_by_body", {}).items():
        for nakshatra_name, count in nakshatra_totals.items():
            totals["position_nakshatra_totals_by_body"][body][nakshatra_name] += direction * int(count)


def render_decans_chart(
    dialog: Any,
    selection_cache: dict[str, Any],
    database_cache: dict[str, Any],
    loaded_charts: int,
    baseline_mode: str = "database",
) -> None:
    decans_mode = dialog._decans_mode
    selection_decan_counts = selection_cache["position_decan_totals_by_body"].get(decans_mode, {1: 0, 2: 0, 3: 0})
    database_decan_counts = database_cache["position_decan_totals_by_body"].get(decans_mode, {1: 0, 2: 0, 3: 0})

    selection_counts = [int(selection_decan_counts[i]) for i in (1, 2, 3)]
    database_counts = [int(database_decan_counts[i]) for i in (1, 2, 3)]
    baseline_counts = _decan_baseline_counts(
        baseline_mode=baseline_mode,
        database_counts=database_counts,
    )
    display_counts = selection_counts if loaded_charts > 0 else baseline_counts

    decans_canvas = dialog._build_count_distribution_chart(
        labels=["Decan 1", "Decan 2", "Decan 3"],
        selection_counts=display_counts,
        database_counts=display_counts,
        loaded_charts=0,
        bar_colors=decan_bar_colors(),
    )
    dialog._clear_layout(dialog.decans_chart_layout)
    dialog.decans_chart_layout.addWidget(decans_canvas, 0)

    dialog._analysis_chart_export_rows["decans"] = dialog._build_analysis_export_rows(
        labels=["Decan 1", "Decan 2", "Decan 3"],
        selection_values=[float(value) for value in display_counts],
        database_values=[float(value) for value in display_counts],
        selection_counts=display_counts,
        database_counts=display_counts,
        loaded_charts=0,
        include_significance=False,
    )


def render_nakshatras_chart(
    dialog: Any,
    selection_cache: dict[str, Any],
    database_cache: dict[str, Any],
    loaded_charts: int,
    baseline_mode: str = "database",
) -> None:
    nakshatras_mode = dialog._nakshatras_mode
    labels = [str(name) for name, *_ in NAKSHATRA_RANGES]
    selection_totals = selection_cache["position_nakshatra_totals_by_body"].get(nakshatras_mode, {})
    database_totals = database_cache["position_nakshatra_totals_by_body"].get(nakshatras_mode, {})
    selection_counts = [int(selection_totals.get(label, 0)) for label in labels]
    database_counts = [int(database_totals.get(label, 0)) for label in labels]
    if baseline_mode == "gen_pop":
        baseline_counts = _gen_pop_nakshatra_counts_for_body(
            body=nakshatras_mode,
            sample_size=sum(database_counts),
            labels=labels,
        )
    else:
        baseline_counts = _nakshatra_baseline_counts(
            baseline_mode=baseline_mode,
            database_counts=database_counts,
            label_count=len(labels),
        )
    display_counts = selection_counts if loaded_charts > 0 else baseline_counts

    nak_canvas = dialog._build_count_distribution_chart(
        labels=labels,
        selection_counts=display_counts,
        database_counts=display_counts,
        loaded_charts=0,
        auto_height=True,
        bar_colors=nakshatra_bar_colors(labels),
    )
    dialog._clear_layout(dialog.nakshatras_chart_layout)
    dialog.nakshatras_chart_layout.addWidget(nak_canvas, 0)

    dialog._analysis_chart_export_rows["nakshatras"] = dialog._build_analysis_export_rows(
        labels=labels,
        selection_values=[float(value) for value in display_counts],
        database_values=[float(value) for value in display_counts],
        selection_counts=display_counts,
        database_counts=display_counts,
        loaded_charts=0,
        include_significance=False,
    )


class DatabaseAnalyticsChartsMixin:

    DATABASE_ANALYTICS_CATEGORY_TITLES: tuple[tuple[str, str], ...] = (
        ("astro", "🪐Astro"),
        ("esoteric", "🪷Esoteric Alternatives"),
        ("subjective_notes", "💭Subjective Notes"),
        ("predictions", "🔮Predictions"),
        ("demographics", "👥Demographics"),
    )

    def _create_database_analytics_category_layouts(
        self,
        panel: Any,
        layout: QVBoxLayout,
    ) -> dict[str, QVBoxLayout]:
        """Create parent category sections for the Database Analytics panel."""
        return {
            key: self._add_left_panel_collapsible_section(
                panel,
                layout,
                title,
                nested=True,
            )
            for key, title in self.DATABASE_ANALYTICS_CATEGORY_TITLES
        }

    CHINESE_FONT_UNAVAILABLE: bool = True
    BAZI_EMOJI_FONT_FAMILIES: tuple[str, ...] = (
        "Noto Color Emoji",
        "Segoe UI Emoji",
        "Apple Color Emoji",
        "Twitter Color Emoji",
        "EmojiOne Color",
        "Noto Emoji",
        "Symbola",
    )
    _BAZI_AVAILABLE_EMOJI_FONT_FAMILIES: tuple[str, ...] | None = None
    HD_DEFINED_CENTER_ORDER: tuple[str, ...] = (
        "Head",
        "Ajna",
        "Throat",
        "G",
        "Ego",
        "Spleen",
        "Solar Plexus",
        "Sacral",
        "Root",
    )
    HD_CENTER_COLORS: dict[str, str] = {
        str(center_data.get("center", "")).strip(): str(center_data.get("color", "#6fa8dc"))
        for center_data in HD_CENTERS.values()
        if str(center_data.get("center", "")).strip()
    }
    HD_STANDARD_PROFILES: tuple[str, ...] = (
        "1/3",
        "1/4",
        "2/4",
        "2/5",
        "3/5",
        "3/6",
        "4/1",
        "4/6",
        "5/1",
        "5/2",
        "6/2",
        "6/3",
    )
    HD_STANDARD_TYPES: tuple[str, ...] = tuple(
        "Manifesting Generator" if key == "manifesting_generator" else key.replace("_", " ").title()
        for key in HD_TYPES.keys()
    )
    HD_STANDARD_AUTHORITIES: tuple[str, ...] = tuple(
        authority_key_to_label(key)
        for key in HD_AUTHORITIES.keys()
    )

    BAZI_STEM_TRANSLITERATIONS: dict[str, str] = {
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
    BAZI_BRANCH_TRANSLITERATIONS: dict[str, str] = {
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
    BAZI_STEM_EMOJIS: dict[str, str] = {
        "甲": "♂🌵", #Yang Wood
        "乙": "♀🪵", #Yin Wood
        "丙": "♂🔥", #Yang Fire
        "丁": "♀🌋", #Yin Fire
        "戊": "♂🗿", #Yang Earth
        "己": "♀⛰️", #Yin Earth
        "庚": "♂🪓", #Yang Metal
        "辛": "♀🪡", #🎙️ #Yin Metal
        "壬": "♂🌊", #Yang Water
        "癸": "♀💧", #Yin Water
    }
    BAZI_BRANCH_EMOJIS: dict[str, str] = {
        "子": "🐀", #Rat
        "丑": "🐂", #Ox
        "寅": "🐅", #Tiger
        "卯": "🐇", #Rabbit
        "辰": "🐉", #Dragon
        "巳": "🐍", #Snake
        "午": "🐎", #Horse
        "未": "🐐", #Goat
        "申": "🐒", #Monkey
        "酉": "🐓", #Rooster
        "戌": "🐕", #Dog
        "亥": "🐖", #Pig
    }
    BAZI_STEM_TRANSLATIONS: dict[str, str] = {
        "甲": "♂ Wood", #Yang Wood
        "乙": "♀ Wood", #Yin Wood
        "丙": "♂ Fire", #Yang Fire
        "丁": "♀ Fire", #Yin Fire
        "戊": "♂ Earth", #Yang Earth
        "己": "♀ Earth", #Yin Earth
        "庚": "♂ Metal", #Yang Metal
        "辛": "♀ Metal", #🎙️ #Yin Metal
        "壬": "♂ Water", #Yang Water
        "癸": "♀ Water", #Yin Water
    }
    BAZI_BRANCH_TRANSLATIONS: dict[str, str] = {
        "子": "Rat", #Rat
        "丑": "Ox", #Ox
        "寅": "Tiger", #Tiger
        "卯": "Rabbit", #Rabbit
        "辰": "Dragon", #Dragon
        "巳": "Snake", #Snake
        "午": "Horse", #Horse
        "未": "Goat", #Goat
        "申": "Monkey", #Monkey
        "酉": "Rooster", #Rooster
        "戌": "Dog", #Dog
        "亥": "Pig", #Pig
    }
    BAZI_ELEMENT_TRANSLATIONS: dict[str, str] = {
        "木": "Wood", #🌵🪵
        "火": "Fire", #🔥🌋
        "土": "Earth", #🗿⛰️
        "金": "Metal", #🪓🪡
        "水": "Water", #🌊💧
    }
    TAG_DISTRIBUTION_CATEGORY_ORDER: tuple[str, ...] = (
        "Occupation",
        "Uncategorized",
        "Trait",
        "Reputation",
        "Affiliation",
        "Crime",
        "Life Events",
        "Characters",
        "Hobbies",
        "Personality",
        "Genres",
        "Places",
    )
    TAG_DISTRIBUTION_CATEGORY_ALIASES: dict[str, str] = {
        "occupation": "Occupation",
        "trait": "Trait",
        "reputation": "Reputation",
        "affiliation": "Affiliation",
        "crime": "Crime",
        "life events": "Life Events",
        "life_events": "Life Events",
        "life-events": "Life Events",
        "characters": "Characters",
        "character": "Characters",
        "hobbies": "Hobbies",
        "hobby": "Hobbies",
        "personality": "Personality",
        "personality_types": "Personality",
        "genres": "Genres",
        "genre": "Genres",
        "places": "Places",
        "place": "Places",
        "uncategorized": "Uncategorized",
        "unknown": "Uncategorized",
    }
    DOMINANT_FACTORS_TOP3_DROPDOWN_OPTIONS: tuple[tuple[str, str], ...] = (
        ("Dominant Signs (Top 3)", "top3_signs"),
        ("Dominant Bodies (Top 3)", "top3_planets"),
        ("Dominant Houses (Top 3)", "top3_houses"),
        ("Dominant Nakshatras (Top 3)", "top3_nakshatras"),
        ("Dominant Elements (#1)", "top_element"),
        ("Dominant Modes (#1)", "top_mode"),
    )
    DOMINANT_FACTORS_CUMULATIVE_DROPDOWN_OPTIONS: tuple[tuple[str, str], ...] = (
        ("Dominant Signs (Cumulative Weight)", "cumulative_signs"),
        ("Dominant Bodies (Cumulative Weight)", "cumulative_planets"),
        ("Dominant Houses (Cumulative Weight)", "cumulative_houses"),
        ("Dominant Nakshatras (Cumulative Weight)", "cumulative_nakshatras"),
        ("Dominant Elements (Cumulative Weight)", "cumulative_elements"),
        ("Dominant Modes (Cumulative Weight)", "cumulative_modes"),
    )

    def _build_database_subheader_label(self, text: str = "") -> QLabel:
        subheader = QLabel(text)
        subheader_style = DATABASE_ANALYTICS_SUBHEADER_STYLE
        if DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS:
            subheader_style = f"{subheader_style} {DATABASE_ANALYTICS_SUBTITLE_DEBUG_STYLE}"
        subheader.setStyleSheet(subheader_style)
        subheader.setWordWrap(DATABASE_VIEW_SUBHEADER_WORD_WRAP)
        return subheader

    def _dominant_factors_top3_dropdown_options(self) -> list[tuple[str, str]]:
        return list(self.DOMINANT_FACTORS_TOP3_DROPDOWN_OPTIONS)

    def _dominant_factors_cumulative_dropdown_options(self) -> list[tuple[str, str]]:
        return list(self.DOMINANT_FACTORS_CUMULATIVE_DROPDOWN_OPTIONS)

    @staticmethod
    def _dominant_factors_subheader_label(mode: str, *, scope_label: str) -> str:
        label_by_mode = {
            "top3_signs": f"top 3 dominant signs for charts in {scope_label}",
            "top3_planets": f"top 3 dominant bodies for charts in {scope_label}",
            "top3_houses": f"top 3 dominant houses for charts in {scope_label}",
            "top3_nakshatras": f"top 3 dominant nakshatras for charts in {scope_label}",
            "top_element": f"#1 dominant element scores for charts in {scope_label}",
            "top_mode": f"#1 dominant mode scores for charts in {scope_label}",
        }
        return label_by_mode.get(mode, label_by_mode["top3_signs"])

    @staticmethod
    def _cumulative_dominant_factors_subheader_label(mode: str, *, scope_label: str) -> str:
        label_by_mode = {
            "cumulative_signs": f"Cumulative weight of signs across all charts in {scope_label}",
            "cumulative_planets": f"Cumulative weight of bodies across all charts in {scope_label}",
            "cumulative_houses": f"Cumulative weight of houses across all charts in {scope_label}",
            "cumulative_nakshatras": f"Cumulative weight of nakshatras across all charts in {scope_label}",
            "cumulative_elements": f"Cumulative weight of elements across all charts in {scope_label}",
            "cumulative_modes": f"Cumulative weight of modes across all charts in {scope_label}",
        }
        return label_by_mode.get(mode, label_by_mode["cumulative_signs"])

    @staticmethod
    def _dominant_nakshatra_top_three_labels(
        dominant_weights: dict[str, float] | None,
    ) -> set[str]:
        if not dominant_weights:
            return set()
        nakshatra_order = [name for name, *_ in NAKSHATRA_RANGES]
        ranked = sorted(
            (
                (name, float(weight))
                for name, weight in dominant_weights.items()
                if name in nakshatra_order and float(weight) > 0
            ),
            key=lambda item: (-item[1], nakshatra_order.index(item[0])),
        )
        return {name for name, _weight in ranked[:3]}

    @staticmethod
    def _value_length_color(
        value: float,
        minimum: float,
        maximum: float,
    ) -> tuple[float, float, float]:
        """Map shorter bars to darker reds and longer bars to brighter greens."""
        if maximum > minimum:
            ratio = (float(value) - float(minimum)) / (float(maximum) - float(minimum))
        else:
            ratio = 0.5
        clamped_ratio = max(0.0, min(1.0, ratio))
        # dark red -> bright green
        red = 0.62 - (0.44 * clamped_ratio)
        green = 0.16 + (0.78 * clamped_ratio)
        blue = 0.16 + (0.10 * clamped_ratio)
        return (red, green, blue)

    @staticmethod
    def _apply_tight_layout(figure: Figure) -> None:
        """Apply tight layout while silencing benign layout-fit warnings."""
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=(
                    "Tight layout not applied. The left and right margins cannot be "
                    "made large enough to accommodate all Axes decorations."
                ),
                category=UserWarning,
            )
            figure.tight_layout()

    @staticmethod
    def _set_x_limits_with_padding(
        ax,
        minimum: float,
        maximum: float,
        pad_px: float = 10.0,
    ) -> None:
        fig = ax.figure
        axes_width_px = (
            fig.get_size_inches()[0] * fig.dpi * ax.get_position().width
        )
        data_range = maximum - minimum
        if data_range <= 0:
            center = float(minimum)
            # Avoid identical low/high limits, which triggers a Matplotlib warning.
            delta = max(abs(center) * 0.01, 0.5)
            ax.set_xlim(center - delta, center + delta)
            return
        if axes_width_px <= (pad_px * 2):
            ax.set_xlim(minimum, maximum)
            return
        pad_ratio = pad_px / axes_width_px
        data_pad = (pad_ratio * data_range) / max(1 - (2 * pad_ratio), 0.01)
        ax.set_xlim(minimum - data_pad, maximum + data_pad)

    @staticmethod
    def _set_compact_barh_y_limits(
        ax,
        item_count: int,
        bar_height: float,
    ) -> None:
        """Trim excess top/bottom whitespace around horizontal bar charts."""
        if item_count <= 0:
            return
        half_height = max(float(bar_height) / 2.0, 0.01)
        # Keep a tiny gutter so bars/labels do not feel clipped.
        edge_padding = max(0.02, min(0.08, half_height * 0.25))
        lower = -half_height - edge_padding
        upper = (item_count - 1) + half_height + edge_padding
        if ax.yaxis_inverted():
            ax.set_ylim(upper, lower)
        else:
            ax.set_ylim(lower, upper)


    @staticmethod
    def _nice_symmetric_axis_limit(
        values: list[float],
        *,
        minimum_limit: float = 0.01,
        maximum_limit: float = 1.0,
        padding_ratio: float = 1.12,
    ) -> float:
        """Return a rounded symmetric axis limit sized to the visible values."""
        max_abs_value = max((abs(float(value)) for value in values), default=0.0)
        raw_limit = max(float(minimum_limit), max_abs_value * float(padding_ratio))
        maximum_limit = float(maximum_limit)
        if raw_limit >= maximum_limit:
            return maximum_limit

        exponent = math.floor(math.log10(raw_limit))
        base = 10 ** exponent
        fraction = raw_limit / base
        for step in (1.0, 2.0, 2.5, 5.0, 10.0):
            if fraction <= step:
                return min(maximum_limit, step * base)
        return maximum_limit

    @classmethod
    def _configure_symmetric_percent_difference_axis(
        cls,
        ax,
        values: list[float],
        *,
        show_x_axis_labels: bool = True,
    ) -> float:
        """Scale a +/- percentage-difference axis to the current dataset."""
        axis_limit = cls._nice_symmetric_axis_limit(values)
        ax.set_xlim(-axis_limit, axis_limit)
        if show_x_axis_labels:
            ticks = [-axis_limit, -axis_limit / 2.0, 0.0, axis_limit / 2.0, axis_limit]
            ax.set_xticks(ticks)
            ax.set_xticklabels([_format_percent(value) for value in ticks])
        return axis_limit

    @staticmethod
    def _difference_label_x(value: float, axis_limit: float) -> float:
        """Place a difference label just outside its bar but inside the axis."""
        direction = 1.0 if value >= 0 else -1.0
        offset = max(float(axis_limit) * 0.03, 0.001)
        margin = max(float(axis_limit) * 0.02, 0.001)
        raw_x = float(value) + (direction * offset)
        if direction >= 0:
            return min(raw_x, float(axis_limit) - margin)
        return max(raw_x, -float(axis_limit) + margin)

    @staticmethod
    def _configure_positive_percent_axis(
        ax,
        values: list[float],
        *,
        show_x_axis_labels: bool = True,
        percent_decimals: int = 2,
    ) -> tuple[float, float]:
        """Apply a dynamic 0..max percent axis for compact left-panel bar charts."""
        max_value = max((float(value) for value in values), default=0.0)
        if max_value <= 0:
            axis_max = 1.0
        else:
            # Keep a small right gutter for value labels while still zooming
            # enough to make small percent differences easier to read.
            axis_max = min(1.0, max_value * 1.12)
            axis_max = max(axis_max, 0.04)
        ax.set_xlim(0, axis_max)
        if show_x_axis_labels:
            tick_count = 5
            ticks = [
                (axis_max * index) / (tick_count - 1)
                for index in range(tick_count)
            ]
            ax.set_xticks(ticks)
            ax.set_xticklabels([_format_percent(value, decimals=percent_decimals) for value in ticks])
        return 0.0, axis_max

    @staticmethod
    def _clear_layout(layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    @staticmethod
    def _empty_bazi_metrics_cache() -> dict[str, Any]:
        return {
            "bazi_sign_counts": {
                "year": {},
                "month": {},
                "day": {},
                "hour": {},
                "all": {},
            },
            "bazi_element_counts": {},
        }

    def _extract_bazi_metadata_for_analytics(self, chart: Any) -> dict[str, Any] | None:
        if chart is None or self._is_placeholder_chart(chart):
            return None
        if validate_chart_for_bazi(chart) is not None:
            return None
        try:
            dt_local = resolve_bazi_birth_datetime(chart)
            include_hour = chart_uses_houses(chart)
            bazi_data = build_bazi_chart_data(dt_local, include_hour=include_hour)
        except Exception:
            return None
        return {
            "year": str(getattr(bazi_data, "year_pillar", "") or "").strip(),
            "month": str(getattr(bazi_data, "month_pillar", "") or "").strip(),
            "day": str(getattr(bazi_data, "day_pillar", "") or "").strip(),
            "hour": str(getattr(bazi_data, "hour_pillar", "") or "").strip(),
            "year_element": str((bazi_data.five_elements_summary or {}).get("year", "") or "").strip(),
            "month_element": str((bazi_data.five_elements_summary or {}).get("month", "") or "").strip(),
            "day_element": str((bazi_data.five_elements_summary or {}).get("day", "") or "").strip(),
            "hour_element": str((bazi_data.five_elements_summary or {}).get("hour", "") or "").strip(),
        }

    def _populate_bazi_snapshot(self, snapshot: dict[str, Any], chart: Any) -> None:
        bazi_metadata = self._extract_bazi_metadata_for_analytics(chart)
        if bazi_metadata is None:
            return
        for pillar_key in ("year", "month", "day", "hour"):
            pillar_value = str(bazi_metadata.get(pillar_key, "") or "").strip()
            if not pillar_value or pillar_value == "Unknown":
                continue
            key_counts = snapshot["bazi_sign_counts"][pillar_key]
            key_counts[pillar_value] = int(key_counts.get(pillar_value, 0)) + 1
            all_counts = snapshot["bazi_sign_counts"]["all"]
            all_counts[pillar_value] = int(all_counts.get(pillar_value, 0)) + 1
        for element_key in ("year_element", "month_element", "day_element", "hour_element"):
            element_value = str(bazi_metadata.get(element_key, "") or "").strip()
            if not element_value or element_value == "Unknown":
                continue
            snapshot["bazi_element_counts"][element_value] = (
                int(snapshot["bazi_element_counts"].get(element_value, 0)) + 1
            )

    def _bazi_label_with_english(self, raw_label: str, *, mode: str) -> str:
        normalized = str(raw_label or "").strip()
        if not normalized:
            return ""

        def _display_label(*, original: str, translated: str) -> str:
            english_only = bool(getattr(self, "CHINESE_FONT_UNAVAILABLE", True))
            if english_only:
                return translated or original
            return f"{original} ({translated})" if translated else original

        if mode == "elements":
            translated = " ".join(
                self.BAZI_ELEMENT_TRANSLATIONS.get(char, "")
                for char in normalized
                if self.BAZI_ELEMENT_TRANSLATIONS.get(char, "")
            ).strip()
            return _display_label(original=normalized, translated=translated)
        if mode == "animals":
            translated = self.BAZI_BRANCH_TRANSLATIONS.get(normalized, "").strip()
            return _display_label(original=normalized, translated=translated)
        if len(normalized) == 2:
            stem = self.BAZI_STEM_TRANSLATIONS.get(normalized[0], "")
            branch = self.BAZI_BRANCH_TRANSLATIONS.get(normalized[1], "")
            translated = " ".join(part for part in (stem, branch) if part)
            return _display_label(original=normalized, translated=translated)
        translated = (
            self.BAZI_STEM_TRANSLATIONS.get(normalized)
            or self.BAZI_BRANCH_TRANSLATIONS.get(normalized)
            or self.BAZI_ELEMENT_TRANSLATIONS.get(normalized)
            or ""
        )
        return _display_label(original=normalized, translated=translated)

    @staticmethod
    def _label_contains_emoji(label: str) -> bool:
        return bool(
            re.search(
                (
                    "["
                    "\U0001F300-\U0001F5FF"
                    "\U0001F600-\U0001F64F"
                    "\U0001F680-\U0001F6FF"
                    "\U0001F700-\U0001F77F"
                    "\U0001F780-\U0001F7FF"
                    "\U0001F800-\U0001F8FF"
                    "\U0001F900-\U0001F9FF"
                    "\U0001FA00-\U0001FA6F"
                    "\U0001FA70-\U0001FAFF"
                    "\u2600-\u26FF"
                    "\u2700-\u27BF"
                    "]"
                ),
                str(label or ""),
            )
        )

    def _apply_bazi_snapshot_delta(
        self,
        totals: dict[str, Any],
        snapshot: dict[str, Any],
        direction: int,
    ) -> None:
        bazi_sign_snapshot = snapshot.get("bazi_sign_counts", {})
        if isinstance(bazi_sign_snapshot, dict):
            for pillar_key in ("year", "month", "day", "hour", "all"):
                pillar_counts = bazi_sign_snapshot.get(pillar_key, {})
                if not isinstance(pillar_counts, dict):
                    continue
                target_counts = totals["bazi_sign_counts"][pillar_key]
                for label, value in pillar_counts.items():
                    normalized_label = str(label).strip()
                    if not normalized_label:
                        continue
                    target_counts[normalized_label] = int(target_counts.get(normalized_label, 0)) + (
                        direction * int(value)
                    )
                    if target_counts[normalized_label] <= 0:
                        del target_counts[normalized_label]
        bazi_elements_snapshot = snapshot.get("bazi_element_counts", {})
        if isinstance(bazi_elements_snapshot, dict):
            for label, value in bazi_elements_snapshot.items():
                normalized_label = str(label).strip()
                if not normalized_label:
                    continue
                totals["bazi_element_counts"][normalized_label] = int(
                    totals["bazi_element_counts"].get(normalized_label, 0)
                ) + (direction * int(value))
                if totals["bazi_element_counts"][normalized_label] <= 0:
                    del totals["bazi_element_counts"][normalized_label]

    @staticmethod
    def _sign_from_longitude(longitude: float) -> str:
        normalized = float(longitude) % 360.0
        return ZODIAC_NAMES[int(normalized // 30) % 12]

    def _display_name_for_chart_id(self, chart_id: int) -> str:
        # Integer chart IDs are a Database Analytics row/sort adapter only;
        # app-wide identity and persisted metadata should be keyed by UID.
        row = self._active_chart_rows_by_id.get(int(chart_id))
        if row is not None and len(row) > 1:
            name = str(row[1] or "").strip()
            if name:
                return name
        chart = self._get_chart_for_filter(int(chart_id))
        chart_name = str(getattr(chart, "name", "") or "").strip() if chart is not None else ""
        return chart_name or f"Chart {int(chart_id)}"

    def _analysis_matching_chart_names(self, chart_key: str, label: str) -> str:
        selected_ids = self._exclude_placeholder_chart_ids(self._selected_chart_ids())
        if not selected_ids:
            return ""
        matching_names: list[str] = []
        label_text = str(label).strip()
        for chart_id in selected_ids:
            chart = self._get_chart_for_filter(int(chart_id))
            if chart is None:
                continue
            include = False
            if chart_key == "planetary_sign_prevalence":
                body = str(self._sign_distribution_mode or "").strip()
                lon = chart.positions.get(body) if getattr(chart, "positions", None) else None
                include = lon is not None and self._sign_from_longitude(float(lon)) == label_text
            elif chart_key == "human_design":
                hd_gates, hd_lines, hd_channels, hd_centers, hd_type, hd_authority = self._extract_human_design_profile(chart)
                mode = str(getattr(self, "_human_design_mode", "hd_gates") or "hd_gates").strip()
                if mode == "hd_gates":
                    include = label_text.isdigit() and int(label_text) in set(hd_gates)
                elif mode == "hd_channels":
                    normalized = set()
                    for channel in hd_channels:
                        channel_text = str(channel).strip()
                        if not channel_text:
                            continue
                        parts = channel_text.split("-")
                        if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                            a, b = int(parts[0].strip()), int(parts[1].strip())
                            channel_text = f"{min(a, b)}-{max(a, b)}"
                        normalized.add(channel_text)
                    include = label_text in normalized
                elif mode == "hd_lines":
                    include = label_text.isdigit() and int(label_text) in set(hd_lines)
                elif mode == "hd_defined_centers":
                    include = label_text in set(str(center).strip() for center in hd_centers)
                elif mode == "hd_types":
                    include = self._format_human_design_type_label(hd_type) == label_text
                elif mode == "hd_profiles":
                    hd_profile = str(getattr(chart, "human_design_profile", "") or "").strip()
                    include = hd_profile == label_text
                elif mode == "hd_authorities":
                    include = canonicalize_hd_authority_label(hd_authority) == label_text
                elif mode == "hd_incarnation_crosses":
                    try:
                        hd_result = build_human_design_result(chart)
                    except Exception:
                        hd_result = None
                    cross_label = self._format_human_design_incarnation_cross_label(
                        str(getattr(hd_result, "incarnation_cross", "")).strip()
                    )
                    include = cross_label == label_text
            if include:
                matching_names.append(self._display_name_for_chart_id(int(chart_id)))
        return ", ".join(matching_names)

    def _export_database_analysis_chart_csv(self, chart_key: str, chart_title: str) -> None:
        rows = self._analysis_chart_export_rows.get(chart_key) or []
        if not rows:
            QMessageBox.information(
                self,
                "incomplete birthdate",
                "There is incomplete birthdate available to export yet.",
            )
            return

        export_date = datetime.date.today().isoformat()
        default_stem = self._analysis_chart_filenames.get(chart_key, chart_key)
        default_filename = f"{default_stem}-{export_date}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export {chart_title} as CSV",
            default_filename,
            "CSV Files (*.csv)",
        )
        QTimer.singleShot(0, self._reactivate_database_view)
        if not file_path:
            return
        if not file_path.lower().endswith(".csv"):
            file_path = f"{file_path}.csv"

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(
                    [
                        "label",
                        "selection",
                        "database",
                        "difference",
                        "selection_qty",
                        "database_qty",
                        "% of DB",
                        "std_error",
                        "z_score",
                        "p_value",
                        "adjusted_p_value",
                        "significance",
                        "statistical_model",
                        "matching chart names",
                    ]
                )
                for row in rows:
                    (
                        label,
                        selection_value,
                        database_value,
                        difference,
                        selection_count,
                        database_count,
                        percent_of_database,
                        *statistical_values,
                    ) = row
                    standard_error = statistical_values[0] if len(statistical_values) > 0 else None
                    z_score = statistical_values[1] if len(statistical_values) > 1 else None
                    p_value = statistical_values[2] if len(statistical_values) > 2 else None
                    adjusted_p_value = statistical_values[3] if len(statistical_values) > 3 else None
                    significance = statistical_values[4] if len(statistical_values) > 4 else "n/a"
                    statistical_model = statistical_values[5] if len(statistical_values) > 5 else "category proportion z-test"
                    writer.writerow(
                        [
                            str(label),
                            round(selection_value, 8),
                            round(database_value, 8),
                            round(difference, 8),
                            selection_count,
                            database_count,
                            round(percent_of_database, 8),
                            "" if standard_error is None else round(float(standard_error), 8),
                            "" if z_score is None else round(float(z_score), 8),
                            "" if p_value is None else round(float(p_value), 8),
                            "" if adjusted_p_value is None else round(float(adjusted_p_value), 8),
                            significance,
                            statistical_model,
                            self._analysis_matching_chart_names(chart_key, label),
                        ]
                    )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export failed",
                f"Could not export {chart_title} as CSV:\n{e}",
            )
            return

        QMessageBox.information(
            self,
            "Export complete",
            f"Saved chart CSV to:\n{file_path}",
        )

    def _attach_database_analytics_tick_label_tooltips(
        self,
        canvas: FigureCanvas,
        figure: Figure,
        label_tooltips: dict[str, str] | None,
    ) -> None:
        if not label_tooltips:
            return
        normalized_tooltips = {
            self._clean_database_analytics_label(label): str(tooltip)
            for label, tooltip in label_tooltips.items()
            if str(tooltip).strip()
        }
        if not normalized_tooltips:
            return

        last_tooltip_label = {"label": ""}

        def _on_tick_label_hover(event: Any) -> None:
            axes_to_check = [event.inaxes] if event.inaxes is not None else list(figure.axes)
            for tick_label in [
                tick_label
                for axis in axes_to_check
                for tick_label in [*axis.get_yticklabels(), *axis.get_xticklabels()]
            ]:
                label_text = self._clean_database_analytics_label(tick_label.get_text())
                tooltip_text = normalized_tooltips.get(label_text)
                if not tooltip_text:
                    continue
                contains, _ = tick_label.contains(event)
                if contains:
                    if last_tooltip_label["label"] != label_text:
                        QToolTip.showText(
                            canvas.mapToGlobal(QPoint(int(event.x), int(event.y))),
                            tooltip_text,
                            canvas,
                        )
                        last_tooltip_label["label"] = label_text
                    return
            if last_tooltip_label["label"]:
                QToolTip.hideText()
                last_tooltip_label["label"] = ""

        canvas.mpl_connect("motion_notify_event", _on_tick_label_hover)

    def _configure_left_panel_canvas(
        self,
        canvas: FigureCanvas,
        figure: Figure,
    ) -> None:
        self._tag_database_analytics_pick_targets(figure)
        height = int(round(figure.get_size_inches()[1] * figure.dpi))
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        canvas.setMinimumWidth(0)
        canvas.setMinimumHeight(height)
        canvas.setMaximumHeight(height)
        #adds trackpad scrolling & hoverstate arrow scroll:
        canvas.setFocusPolicy(Qt.NoFocus)
        apply_popout_cursor(canvas)
        canvas.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        canvas.installEventFilter(self)

    @staticmethod
    def _clean_database_analytics_label(label: object) -> str:
        text = str(label or "").strip()
        text = re.sub(r"^\([^)]*\)\s*", "", text)
        text = re.sub(r"\s+", " ", text)
        return text or "this category"

    @staticmethod
    def _tag_database_analytics_pick_targets(figure: Figure) -> None:
        """Make Database Analytics bars and labels clickable in copied popout figures."""
        for ax in figure.axes:
            y_tick_lookup = [
                (
                    float(tick),
                    DatabaseAnalyticsChartsMixin._clean_database_analytics_label(
                        label.get_text()
                    ),
                )
                for tick, label in zip(ax.get_yticks(), ax.get_yticklabels())
                if str(label.get_text()).strip()
            ]
            x_tick_lookup = [
                (
                    float(tick),
                    DatabaseAnalyticsChartsMixin._clean_database_analytics_label(
                        label.get_text()
                    ),
                )
                for tick, label in zip(ax.get_xticks(), ax.get_xticklabels())
                if str(label.get_text()).strip()
                and not str(label.get_text()).strip().endswith("%")
            ]
            for patch in ax.patches:
                try:
                    width = float(patch.get_width())
                    height = float(patch.get_height())
                except (TypeError, ValueError):
                    continue
                if abs(width) < 1e-12 and abs(height) < 1e-12:
                    continue
                horizontal = abs(width) >= abs(height)
                if horizontal and y_tick_lookup:
                    center = float(patch.get_y()) + (height / 2.0)
                    label = min(y_tick_lookup, key=lambda item: abs(item[0] - center))[1]
                    left_edge = float(patch.get_x())
                    value = -abs(width) if left_edge < 0.0 else width
                elif x_tick_lookup:
                    center = float(patch.get_x()) + (width / 2.0)
                    label = min(x_tick_lookup, key=lambda item: abs(item[0] - center))[1]
                    value = height
                else:
                    continue
                patch.set_picker(True)
                patch.set_gid(f"database_analytics_bar:{label}:{value:.8g}")
            for tick_label in [*ax.get_yticklabels(), *ax.get_xticklabels()]:
                label_text = DatabaseAnalyticsChartsMixin._clean_database_analytics_label(
                    tick_label.get_text()
                )
                if label_text and label_text != "this category":
                    tick_label.set_picker(True)
                    tick_label.set_gid(f"database_analytics_label:{label_text}")

    @staticmethod
    def _database_analytics_candidate_keys(chart_key: str) -> list[str]:
        candidate_keys = [chart_key]
        if chart_key == "alignment_summary":
            candidate_keys.extend([
                "alignment_summary_cumulative",
                "social_score_summary",
            ])
        return candidate_keys

    def _database_analytics_canvas_for_key(self, chart_key: str) -> FigureCanvas | None:
        for key in self._database_analytics_candidate_keys(chart_key):
            layout = getattr(self, "_database_metrics_chart_layouts", {}).get(key)
            if layout is None:
                continue
            for index in range(layout.count()):
                item = layout.itemAt(index)
                widget = item.widget() if item is not None else None
                if isinstance(widget, FigureCanvas) and widget.isVisible():
                    return widget
                if isinstance(widget, FigureCanvas):
                    return widget
        return None

    def _database_analytics_chart_key_for_canvas(
        self,
        canvas: FigureCanvas,
    ) -> str | None:
        for chart_key, layout in getattr(self, "_database_metrics_chart_layouts", {}).items():
            if layout is None:
                continue
            for index in range(layout.count()):
                item = layout.itemAt(index)
                if item is not None and item.widget() is canvas:
                    return chart_key
        return None

    def _database_analytics_title_for_key(self, chart_key: str) -> str:
        dropdown = getattr(self, "_analysis_chart_dropdowns", {}).get(chart_key)
        if dropdown is not None:
            current_text = str(dropdown.currentText() or "").strip()
            if current_text:
                return current_text.title()
        return str(chart_key or "Database Analytics").replace("_", " ").title()

    def _handle_database_analytics_canvas_wheel(self, event: Any) -> bool:
        scroll_area = getattr(self, "selection_sentiment_panel_scroll", None)
        if scroll_area is None:
            return False
        scrollbar = scroll_area.verticalScrollBar()
        pixel_delta = event.pixelDelta().y() if hasattr(event, "pixelDelta") else 0
        angle_delta = event.angleDelta().y() if hasattr(event, "angleDelta") else 0
        if pixel_delta:
            scrollbar.setValue(scrollbar.value() - pixel_delta)
            return True
        if angle_delta:
            scroll_amount = int(angle_delta / 120) * scrollbar.singleStep() * 3
            scrollbar.setValue(scrollbar.value() - scroll_amount)
            return True
        return False

    @staticmethod
    def _enneagram_type_for_database_label(label: str) -> int | None:
        clean_label = DatabaseAnalyticsChartsMixin._clean_database_analytics_label(label)
        match = re.search(r"\btype\s+([1-9])\b", clean_label, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
        if clean_label.isdigit():
            enneagram_type = int(clean_label)
            if 1 <= enneagram_type <= 9:
                return enneagram_type
        for enneagram_type, type_data in ENNEAGRAM.items():
            type_name = str(type_data.get("name", "")).strip()
            if type_name and type_name.casefold() in clean_label.casefold():
                return int(enneagram_type)
        return None

    @staticmethod
    def _database_analytics_color_for_label(label: str, chart_title: str = "") -> str:
        clean_label = DatabaseAnalyticsChartsMixin._clean_database_analytics_label(label)
        label_key = clean_label.casefold()
        if clean_label in SIGN_COLORS:
            return str(SIGN_COLORS[clean_label])
        if clean_label in PLANET_COLORS:
            return str(PLANET_COLORS[clean_label])
        if clean_label in HOUSE_COLORS:
            return str(HOUSE_COLORS[clean_label])
        house_match = re.fullmatch(r"house\s+(1[0-2]|[1-9])", label_key)
        if house_match:
            return str(HOUSE_COLORS.get(f"House {house_match.group(1)}", CHART_DATA_HIGHLIGHT_COLOR))
        if clean_label in ELEMENT_COLORS:
            return str(ELEMENT_COLORS[clean_label])
        mode_color = MODE_COLORS.get(label_key)
        if mode_color:
            return str(mode_color)
        nakshatra_color = NAKSHATRA_PLANET_COLOR.get(clean_label)
        if nakshatra_color:
            return str(nakshatra_color[1])
        authority_key = normalize_hd_authority_key(canonicalize_hd_authority_label(clean_label))
        if HD_AUTHORITY_COLORS.get(authority_key):
            return str(HD_AUTHORITY_COLORS[authority_key])
        if clean_label in DatabaseAnalyticsChartsMixin.HD_CENTER_COLORS:
            return str(DatabaseAnalyticsChartsMixin.HD_CENTER_COLORS[clean_label])
        if clean_label.casefold() in BAZI_ZODIAC:
            color = (BAZI_ZODIAC.get(clean_label.casefold(), {}) or {}).get("color")
            return str(color or CHART_DATA_HIGHLIGHT_COLOR)
        return CHART_DATA_HIGHLIGHT_COLOR

    @staticmethod
    def _database_analytics_category_name(label: str, chart_title: str) -> str:
        clean_label = DatabaseAnalyticsChartsMixin._clean_database_analytics_label(label)
        title_key = str(chart_title or "").casefold()
        label_key = clean_label.casefold()
        if clean_label in SIGN_COLORS:
            return "Zodiac sign"
        if clean_label in PLANET_COLORS:
            return "Astrological body / point"
        if clean_label in HOUSE_COLORS or re.fullmatch(r"house\s+(1[0-2]|[1-9])", label_key):
            return "Astrological house"
        if clean_label in ELEMENT_COLORS:
            return "Element"
        if MODE_COLORS.get(label_key):
            return "Mode / modality"
        if clean_label in {str(name) for name, *_ in NAKSHATRA_RANGES}:
            return "Nakshatra"
        if clean_label in RELATION_TYPE:
            return "Relationship classification"
        if clean_label in SENTIMENT_COLORS or "sentiment" in title_key:
            return "Sentiment / tone"
        if clean_label.casefold() in BAZI_ZODIAC or "bazi" in title_key:
            return "BaZi / Chinese astrology"
        if DatabaseAnalyticsChartsMixin._enneagram_type_for_database_label(clean_label) is not None or "enneagram" in title_key:
            return "Enneagram type"
        if clean_label in AGE_BRACKETS or "age" in title_key:
            return "Age bucket"
        if "birth" in title_key:
            return "Birth-data category"
        if "tag" in title_key:
            return "Saved tag"
        return "Database analytics category"

    @staticmethod
    def _database_analytics_definition_for_label(label: str, chart_title: str) -> str:
        clean_label = DatabaseAnalyticsChartsMixin._clean_database_analytics_label(label)
        title_key = str(chart_title or "").casefold()
        label_key = clean_label.casefold()
        if clean_label in ZODIAC_NAMES:
            return f"{clean_label} is a zodiac sign category; this bar compares its share in the selected charts against the comparison database."
        if clean_label in PLANET_COLORS:
            return f"{clean_label} is an astrological body or point; this bar compares how often it is the measured or dominant factor."
        if clean_label in HOUSE_COLORS or re.fullmatch(r"house\s+(1[0-2]|[1-9])", label_key):
            return f"{clean_label} is an astrological house category; this bar compares how often placements or dominance land there."
        if clean_label in ELEMENT_COLORS:
            return f"{clean_label} is an elemental category; this bar compares that element's share in the analytics."
        if MODE_COLORS.get(label_key):
            return f"{clean_label} is a mode/modality category; this bar compares how often Cardinal, Fixed, or Mutable emphasis appears."
        if clean_label in {str(name) for name, *_ in NAKSHATRA_RANGES}:
            return f"{clean_label} is a nakshatra category; this bar compares how often placements or dominance fall in that lunar mansion."
        if clean_label in RELATION_TYPE:
            return f"{clean_label} is a relationship classification assigned to charts; this bar compares its frequency."
        if clean_label in SENTIMENT_COLORS or "sentiment" in title_key:
            return f"{clean_label} is a sentiment/tone category; this bar compares how often that tone appears in chart metadata."
        if clean_label in BAZI_ZODIAC or "bazi" in title_key:
            return f"{clean_label} is a BaZi / Chinese astrology category; this bar compares how often it appears."
        if DatabaseAnalyticsChartsMixin._enneagram_type_for_database_label(clean_label) is not None or "enneagram" in title_key:
            return f"{clean_label} is an Enneagram type category; this bar compares how often that predicted or assigned type appears."
        if clean_label in AGE_BRACKETS or "age" in title_key:
            return f"{clean_label} is an age bucket; this bar compares how many charts fall in that age range."
        if "birth" in title_key:
            return f"{clean_label} is a birth-data category; this bar compares how many charts share that birth timing or place attribute."
        if "tag" in title_key:
            return f"{clean_label} is a saved tag/category label; this bar compares how often it is attached to charts."
        return f"{clean_label} is the category represented by this row; this bar compares its frequency or score in the current Database View analytics."

    @staticmethod
    def _database_analytics_incarnation_cross_info_html(label: str) -> str | None:
        clean_label = DatabaseAnalyticsChartsMixin._clean_database_analytics_label(label)
        cross_entry = find_cross_by_name(clean_label) if clean_label else None
        if not cross_entry:
            return None
        cross_name = str(cross_entry.get("full_name") or clean_label).strip() or clean_label
        gates = cross_entry.get("gates", ())
        gates_text = "/".join(str(gate) for gate in gates) if gates else "Unknown"
        theme = str(cross_entry.get("theme", "")).strip() or "Unknown"
        angle = str(cross_entry.get("cross_type", "")).strip() or "Unknown"
        theme_description = get_cross_theme_description(theme)
        type_description = get_cross_type_description(angle)
        detail_items = [
            ("Theme", theme),
            ("Angle", angle),
            ("Gates", gates_text),
        ]
        if theme_description:
            detail_items.append(("Theme description", theme_description))
        if type_description:
            detail_items.append(("Angle description", type_description))
        detail_html = "".join(
            f"<li><b>{html.escape(title)}:</b> {html.escape(text)}</li>"
            for title, text in detail_items
        )
        return f"<h3>Incarnation Cross: {html.escape(cross_name)}</h3><ul>{detail_html}</ul>"

    def _database_analytics_single_selected_chart(self) -> Any | None:
        """Return the one selected chart, or None when Database Analytics is aggregating."""
        selected_ids_method = getattr(self, "_selected_chart_ids", None)
        exclude_method = getattr(self, "_exclude_placeholder_chart_ids", None)
        get_chart = getattr(self, "_get_chart_for_filter", None)
        if not callable(selected_ids_method) or not callable(get_chart):
            return None
        selected_ids = list(selected_ids_method() or [])
        if callable(exclude_method):
            selected_ids = list(exclude_method(selected_ids) or [])
        if len(selected_ids) != 1:
            return None
        return get_chart(int(selected_ids[0]))

    def _build_database_analytics_chart_analytics_info_html(
        self,
        *,
        chart_title: str,
        label: str,
    ) -> str | None:
        """Return the matching Chart Analytics explainer for known astro categories."""
        del chart_title
        clean_label = self._clean_database_analytics_label(label)
        owner = getattr(self, "_app_owner", None)
        chart = self._database_analytics_single_selected_chart()
        if chart is None:
            return None
        builder_host = self if hasattr(self, "_build_body_popout_info") else owner
        if builder_host is None:
            return None

        if clean_label in PLANET_COLORS and hasattr(builder_host, "_build_body_popout_info"):
            return builder_host._build_body_popout_info(chart, clean_label)
        if clean_label in SIGN_COLORS and hasattr(builder_host, "_build_sign_popout_info"):
            return builder_host._build_sign_popout_info(chart, clean_label)
        if clean_label in ELEMENT_COLORS and hasattr(builder_host, "_build_element_popout_info"):
            return builder_host._build_element_popout_info(chart, clean_label)
        if MODE_COLORS.get(clean_label.casefold()) and hasattr(builder_host, "_build_mode_popout_info"):
            return builder_host._build_mode_popout_info(chart, clean_label)
        if clean_label in {str(name) for name, *_ in NAKSHATRA_RANGES} and hasattr(
            builder_host, "_build_nakshatra_popout_info"
        ):
            return builder_host._build_nakshatra_popout_info(chart, clean_label)
        house_match = re.fullmatch(r"(?:house\s+)?(1[0-2]|[1-9])", clean_label.casefold())
        if house_match and hasattr(builder_host, "_build_house_popout_info"):
            return builder_host._build_house_popout_info(chart, int(house_match.group(1)))
        return None

    @staticmethod
    def _database_analytics_trait_description_for_label(label: str) -> str | None:
        clean_label = DatabaseAnalyticsChartsMixin._clean_database_analytics_label(label)
        for trait in list_traits(active_only=False):
            if str(trait.get("name", "")).strip() != clean_label:
                continue
            description = str(trait.get("description", "")).strip()
            return description or None
        return None

    def _build_database_analytics_popout_info_html(
        self,
        *,
        chart_title: str,
        label: str,
        value: float | None,
    ) -> str:
        clean_title = self._clean_database_analytics_label(chart_title)
        clean_label = self._clean_database_analytics_label(label)
        chart_analytics_html = self._build_database_analytics_chart_analytics_info_html(
            chart_title=clean_title,
            label=clean_label,
        )
        if chart_analytics_html:
            return chart_analytics_html
        if "incarnation" in clean_title.casefold() and "cross" in clean_title.casefold():
            cross_html = self._database_analytics_incarnation_cross_info_html(clean_label)
            if cross_html:
                return cross_html
        enneagram_type = self._enneagram_type_for_database_label(clean_label)
        if enneagram_type is not None and "enneagram" in clean_title.casefold():
            return build_enneagram_popout_info_html(
                enneagram_type,
                enneagram=ENNEAGRAM,
                chart_theme_colors=CHART_THEME_COLORS,
                highlight_color=CHART_DATA_HIGHLIGHT_COLOR,
                debug_math_enabled=False,
                chart=None,
                calculate_type_weights=None,
            )
        trait_description = None
        if "trait" in clean_title.casefold():
            trait_description = self._database_analytics_trait_description_for_label(clean_label)
        definition = self._database_analytics_definition_for_label(clean_label, clean_title)
        value_line = ""
        if value is not None and math.isfinite(float(value)):
            if abs(float(value)) <= 1.0:
                value_text = _format_percent(abs(float(value)))
            else:
                value_text = f"{float(value):,.2f}".rstrip("0").rstrip(".")
            direction = (
                "above the comparison baseline"
                if float(value) > 0
                else "below the comparison baseline"
            )
            if abs(float(value)) < 1e-12:
                direction = "at the comparison baseline"
            value_line = (
                f"<p><b>Bar reading:</b> about {html.escape(value_text)} {html.escape(direction)}. "
                "In selection-vs-database charts, rightward bars mean the selected charts contain more of this category than the database baseline, and leftward bars mean less.</p>"
            )
        std_dev_line = ""
        if self._standard_deviation_indicators_visible():
            std_dev_line = (
                "<p><b>Standard deviation / SE guide lines:</b> The red dashed lines mark about one and two standard errors away from the baseline. "
                "A bar inside the first pair is usually ordinary noise; reaching the ±1 line is a mild signal; reaching or passing the ±2 line is a stronger clue that the selection genuinely differs from raw probability.</p>"
            )
        label_color = self._database_analytics_color_for_label(clean_label, clean_title)
        category_name = self._database_analytics_category_name(clean_label, clean_title)
        description_line = ""
        if trait_description:
            description_line = (
                f'<p><i>{html.escape(trait_description)}</i></p>'
            )
        return (
            f'<h3 style="color:{html.escape(label_color)}; font-weight:800;">{html.escape(clean_label)}</h3>'
            f"{description_line}"
            f'<p><b style="color:{CHART_DATA_HIGHLIGHT_COLOR};">Category:</b> {html.escape(category_name)}</p>'
            f'<p><b style="color:{CHART_DATA_HIGHLIGHT_COLOR};">What this measures:</b> {html.escape(definition)}</p>'
            f'<p><b style="color:{CHART_DATA_HIGHLIGHT_COLOR};">Where it appears:</b> <i>{html.escape(clean_title)}</i>.</p>'
            f"{value_line}"
            f"{std_dev_line}"
        )

    def _show_database_analytics_popout(self, chart_key: str, chart_title: str) -> None:
        source_canvas = self._database_analytics_canvas_for_key(chart_key)
        if source_canvas is None:
            QMessageBox.information(
                self,
                "No chart available",
                "Expand this Database Analytics section and load chart data before opening the popout.",
            )
            return
        figure = copy.deepcopy(source_canvas.figure)
        self._tag_database_analytics_pick_targets(figure)
        source_width, source_height = source_canvas.figure.get_size_inches()
        figure.set_size_inches(
            max(9.5, float(source_width)),
            max(6.2, float(source_height)),
            forward=True,
        )
        figure.patch.set_facecolor(self._database_analytics_figure_facecolor())
        for ax in figure.axes:
            ax.set_facecolor(self._database_analytics_axes_facecolor())
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{chart_title} — Database Analytics")
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.setMinimumSize(820, 620)
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        dialog.setLayout(layout)
        popout_canvas = FigureCanvas(figure)
        canvas_height = max(1, int(figure.get_figheight() * figure.dpi))
        popout_canvas.setMinimumSize(QSize(1, canvas_height))
        popout_canvas.setMinimumHeight(canvas_height)
        popout_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        chart_scroll = DatabaseAnalyticsPopoutScrollArea(dialog)
        chart_scroll.setWidget(popout_canvas)
        chart_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        info_panel = QTextEdit()
        info_panel.setReadOnly(True)
        info_panel.setPlaceholderText(
            "Click any bar or label to see a plain-English definition."
        )
        info_panel.setMinimumHeight(150)
        dialog.installEventFilter(chart_scroll)
        info_panel.installEventFilter(chart_scroll)
        info_panel.viewport().installEventFilter(chart_scroll)
        layout.addWidget(chart_scroll, 3)
        layout.addWidget(info_panel, 1)

        def _on_pick(event: Any) -> None:
            artist = getattr(event, "artist", None)
            artist_gid = (
                artist.get_gid()
                if artist is not None and hasattr(artist, "get_gid")
                else None
            )
            if not isinstance(artist_gid, str):
                return
            value: float | None = None
            label = ""
            if artist_gid.startswith("database_analytics_bar:"):
                payload = artist_gid.removeprefix("database_analytics_bar:")
                label, _separator, raw_value = payload.rpartition(":")
                try:
                    value = float(raw_value)
                except ValueError:
                    value = None
            elif artist_gid.startswith("database_analytics_label:"):
                _prefix, label = artist_gid.split(":", 1)
            else:
                return
            info_panel.setHtml(
                self._build_database_analytics_popout_info_html(
                    chart_title=chart_title,
                    label=label,
                    value=value,
                )
            )

        def _show_info_for_pick_target(label: str, value: float | None) -> None:
            info_panel.setHtml(
                self._build_database_analytics_popout_info_html(
                    chart_title=chart_title,
                    label=label,
                    value=value,
                )
            )

        def _on_click(event: Any) -> None:
            if getattr(event, "inaxes", None) is None:
                return
            mouse_event = getattr(event, "guiEvent", None) or event
            for artist in [*getattr(event.inaxes, "patches", [])]:
                artist_gid = artist.get_gid() if hasattr(artist, "get_gid") else None
                if (
                    not isinstance(artist_gid, str)
                    or not artist_gid.startswith("database_analytics_bar:")
                ):
                    continue
                contains, _details = artist.contains(mouse_event)
                if not contains:
                    continue
                payload = artist_gid.removeprefix("database_analytics_bar:")
                label, _separator, raw_value = payload.rpartition(":")
                try:
                    value = float(raw_value)
                except ValueError:
                    value = None
                _show_info_for_pick_target(label, value)
                return
            for tick_label in [
                *event.inaxes.get_yticklabels(),
                *event.inaxes.get_xticklabels(),
            ]:
                artist_gid = tick_label.get_gid() if hasattr(tick_label, "get_gid") else None
                if (
                    not isinstance(artist_gid, str)
                    or not artist_gid.startswith("database_analytics_label:")
                ):
                    continue
                contains, _details = tick_label.contains(mouse_event)
                if contains:
                    _prefix, label = artist_gid.split(":", 1)
                    _show_info_for_pick_target(label, None)
                    return

        popout_canvas.mpl_connect("pick_event", _on_pick)
        popout_canvas.mpl_connect("button_press_event", _on_click)
        if hasattr(self, "_register_popout_shortcuts"):
            self._register_popout_shortcuts(dialog)
        dialog.resize(980, 720)
        dialog.show()
        popout_dialogs = getattr(self, "_database_analytics_popout_dialogs", None)
        if popout_dialogs is None:
            self._database_analytics_popout_dialogs = []
            popout_dialogs = self._database_analytics_popout_dialogs
        popout_dialogs.append(dialog)
        dialog.destroyed.connect(
            lambda _=None, dialog=dialog: popout_dialogs.remove(dialog)
            if dialog in popout_dialogs
            else None
        )

    @staticmethod
    def _clean_database_analytics_label(label: object) -> str:
        text = str(label or "").strip()
        text = re.sub(r"^\([^)]*\)\s*", "", text)
        text = re.sub(r"\s+", " ", text)
        return text or "this category"

    @staticmethod
    def _tag_database_analytics_pick_targets(figure: Figure) -> None:
        """Make Database Analytics bars and labels clickable in copied popout figures."""
        for ax in figure.axes:
            y_tick_lookup = [
                (
                    float(tick),
                    DatabaseAnalyticsChartsMixin._clean_database_analytics_label(
                        label.get_text()
                    ),
                )
                for tick, label in zip(ax.get_yticks(), ax.get_yticklabels())
                if str(label.get_text()).strip()
            ]
            x_tick_lookup = [
                (
                    float(tick),
                    DatabaseAnalyticsChartsMixin._clean_database_analytics_label(
                        label.get_text()
                    ),
                )
                for tick, label in zip(ax.get_xticks(), ax.get_xticklabels())
                if str(label.get_text()).strip()
                and not str(label.get_text()).strip().endswith("%")
            ]
            for patch in ax.patches:
                try:
                    width = float(patch.get_width())
                    height = float(patch.get_height())
                except (TypeError, ValueError):
                    continue
                if abs(width) < 1e-12 and abs(height) < 1e-12:
                    continue
                horizontal = abs(width) >= abs(height)
                if horizontal and y_tick_lookup:
                    center = float(patch.get_y()) + (height / 2.0)
                    label = min(y_tick_lookup, key=lambda item: abs(item[0] - center))[1]
                    value = width
                elif x_tick_lookup:
                    center = float(patch.get_x()) + (width / 2.0)
                    label = min(x_tick_lookup, key=lambda item: abs(item[0] - center))[1]
                    value = height
                else:
                    continue
                patch.set_picker(True)
                patch.set_gid(f"database_analytics_bar:{label}:{value:.8g}")
            for tick_label in [*ax.get_yticklabels(), *ax.get_xticklabels()]:
                label_text = DatabaseAnalyticsChartsMixin._clean_database_analytics_label(
                    tick_label.get_text()
                )
                if label_text and label_text != "this category":
                    tick_label.set_picker(True)
                    tick_label.set_gid(f"database_analytics_label:{label_text}")

    def _database_analytics_canvas_for_key(self, chart_key: str) -> FigureCanvas | None:
        candidate_keys = [chart_key]
        if chart_key == "alignment_summary":
            candidate_keys.extend([
                "alignment_summary_cumulative",
                "social_score_summary",
            ])
        for key in candidate_keys:
            layout = getattr(self, "_database_metrics_chart_layouts", {}).get(key)
            if layout is None:
                continue
            for index in range(layout.count()):
                item = layout.itemAt(index)
                widget = item.widget() if item is not None else None
                if isinstance(widget, FigureCanvas) and widget.isVisible():
                    return widget
                if isinstance(widget, FigureCanvas):
                    return widget
        return None

    @staticmethod
    def _enneagram_type_for_database_label(label: str) -> int | None:
        clean_label = DatabaseAnalyticsChartsMixin._clean_database_analytics_label(label)
        match = re.search(r"\btype\s+([1-9])\b", clean_label, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
        if clean_label.isdigit():
            enneagram_type = int(clean_label)
            if 1 <= enneagram_type <= 9:
                return enneagram_type
        for enneagram_type, type_data in ENNEAGRAM.items():
            type_name = str(type_data.get("name", "")).strip()
            if type_name and type_name.casefold() in clean_label.casefold():
                return int(enneagram_type)
        return None

    @staticmethod
    def _database_analytics_definition_for_label(label: str, chart_title: str) -> str:
        clean_label = DatabaseAnalyticsChartsMixin._clean_database_analytics_label(label)
        title_key = str(chart_title or "").casefold()
        label_key = clean_label.casefold()
        if clean_label in ZODIAC_NAMES:
            return f"{clean_label} is a zodiac sign category; this bar compares its share in the selected charts against the comparison database."
        if clean_label in PLANET_COLORS:
            return f"{clean_label} is an astrological body or point; this bar compares how often it is the measured or dominant factor."
        if clean_label in HOUSE_COLORS or re.fullmatch(r"house\s+(1[0-2]|[1-9])", label_key):
            return f"{clean_label} is an astrological house category; this bar compares how often placements or dominance land there."
        if clean_label in ELEMENT_COLORS:
            return f"{clean_label} is an elemental category; this bar compares that element's share in the analytics."
        if MODE_COLORS.get(label_key):
            return f"{clean_label} is a mode/modality category; this bar compares how often Cardinal, Fixed, or Mutable emphasis appears."
        if clean_label in {str(name) for name, *_ in NAKSHATRA_RANGES}:
            return f"{clean_label} is a nakshatra category; this bar compares how often placements or dominance fall in that lunar mansion."
        if clean_label in RELATION_TYPE:
            return f"{clean_label} is a relationship classification assigned to charts; this bar compares its frequency."
        if clean_label in SENTIMENT_COLORS or "sentiment" in title_key:
            return f"{clean_label} is a sentiment/tone category; this bar compares how often that tone appears in chart metadata."
        if clean_label in BAZI_ZODIAC or "bazi" in title_key:
            return f"{clean_label} is a BaZi / Chinese astrology category; this bar compares how often it appears."
        if DatabaseAnalyticsChartsMixin._enneagram_type_for_database_label(clean_label) is not None or "enneagram" in title_key:
            return f"{clean_label} is an Enneagram type category; this bar compares how often that predicted or assigned type appears."
        if clean_label in AGE_BRACKETS or "age" in title_key:
            return f"{clean_label} is an age bucket; this bar compares how many charts fall in that age range."
        if "birth" in title_key:
            return f"{clean_label} is a birth-data category; this bar compares how many charts share that birth timing or place attribute."
        if "tag" in title_key:
            return f"{clean_label} is a saved tag/category label; this bar compares how often it is attached to charts."
        return f"{clean_label} is the category represented by this row; this bar compares its frequency or score in the current Database View analytics."

    def _build_database_analytics_popout_info_html(
        self,
        *,
        chart_title: str,
        label: str,
        value: float | None,
    ) -> str:
        clean_title = self._clean_database_analytics_label(chart_title)
        clean_label = self._clean_database_analytics_label(label)
        chart_analytics_html = self._build_database_analytics_chart_analytics_info_html(
            chart_title=clean_title,
            label=clean_label,
        )
        if chart_analytics_html:
            return chart_analytics_html
        if "incarnation" in clean_title.casefold() and "cross" in clean_title.casefold():
            cross_html = self._database_analytics_incarnation_cross_info_html(clean_label)
            if cross_html:
                return cross_html
        enneagram_type = self._enneagram_type_for_database_label(clean_label)
        if enneagram_type is not None and "enneagram" in clean_title.casefold():
            return build_enneagram_popout_info_html(
                enneagram_type,
                enneagram=ENNEAGRAM,
                chart_theme_colors=CHART_THEME_COLORS,
                highlight_color=CHART_DATA_HIGHLIGHT_COLOR,
                debug_math_enabled=False,
                chart=None,
                calculate_type_weights=None,
            )
        trait_description = None
        if "trait" in clean_title.casefold():
            trait_description = self._database_analytics_trait_description_for_label(clean_label)
        definition = self._database_analytics_definition_for_label(clean_label, clean_title)
        value_line = ""
        if value is not None and math.isfinite(float(value)):
            if abs(float(value)) <= 1.0:
                value_text = _format_percent(abs(float(value)))
            else:
                value_text = f"{float(value):,.2f}".rstrip("0").rstrip(".")
            direction = (
                "above the comparison baseline"
                if float(value) > 0
                else "below the comparison baseline"
            )
            if abs(float(value)) < 1e-12:
                direction = "at the comparison baseline"
            value_line = (
                f"<p><b>Bar reading:</b> about {html.escape(value_text)} {html.escape(direction)}. "
                "In selection-vs-database charts, rightward bars mean the selected charts contain more of this category than the database baseline, and leftward bars mean less.</p>"
            )
        std_dev_line = ""
        if self._standard_deviation_indicators_visible():
            std_dev_line = (
                "<p><b>Standard deviation / SE guide lines:</b> The red dashed lines mark about one and two standard errors away from the baseline. "
                "A bar inside the first pair is usually ordinary noise; reaching the ±1 line is a mild signal; reaching or passing the ±2 line is a stronger clue that the selection may genuinely differ from the database, though it is still not proof by itself.</p>"
            )
        label_color = self._database_analytics_color_for_label(clean_label, clean_title)
        category_name = self._database_analytics_category_name(clean_label, clean_title)
        description_line = ""
        if trait_description:
            description_line = (
                f'<p><b style="color:{CHART_DATA_HIGHLIGHT_COLOR};">Description:</b> '
                f"{html.escape(trait_description)}</p>"
            )
        return (
            f'<h3 style="color:{html.escape(label_color)}; font-weight:800;">{html.escape(clean_label)}</h3>'
            f'<p><b style="color:{CHART_DATA_HIGHLIGHT_COLOR};">Category:</b> {html.escape(category_name)}</p>'
            f'<p><b style="color:{CHART_DATA_HIGHLIGHT_COLOR};">What this measures:</b> {html.escape(definition)}</p>'
            f"{description_line}"
            f'<p><b style="color:{CHART_DATA_HIGHLIGHT_COLOR};">Where it appears:</b> <i>{html.escape(clean_title)}</i>.</p>'
            f"{value_line}"
            f"{std_dev_line}"
        )

    def _show_database_analytics_popout(self, chart_key: str, chart_title: str) -> None:
        source_canvas = self._database_analytics_canvas_for_key(chart_key)
        if source_canvas is None:
            QMessageBox.information(
                self,
                "No chart available",
                "Expand this Database Analytics section and load chart data before opening the popout.",
            )
            return
        figure = copy.deepcopy(source_canvas.figure)
        self._tag_database_analytics_pick_targets(figure)
        source_width, source_height = source_canvas.figure.get_size_inches()
        figure.set_size_inches(
            max(9.5, float(source_width)),
            max(6.2, float(source_height)),
            forward=True,
        )
        figure.patch.set_facecolor(self._database_analytics_figure_facecolor())
        for ax in figure.axes:
            ax.set_facecolor(self._database_analytics_axes_facecolor())
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{chart_title} — Database Analytics")
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.setMinimumSize(820, 620)
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        dialog.setLayout(layout)
        popout_canvas = FigureCanvas(figure)
        canvas_height = max(1, int(figure.get_figheight() * figure.dpi))
        popout_canvas.setMinimumSize(QSize(1, canvas_height))
        popout_canvas.setMinimumHeight(canvas_height)
        popout_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        chart_scroll = DatabaseAnalyticsPopoutScrollArea(dialog)
        chart_scroll.setWidget(popout_canvas)
        chart_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        info_panel = QTextEdit()
        info_panel.setReadOnly(True)
        info_panel.setPlaceholderText(
            "Click any bar or label to see a plain-English definition."
        )
        info_panel.setMinimumHeight(150)
        dialog.installEventFilter(chart_scroll)
        info_panel.installEventFilter(chart_scroll)
        info_panel.viewport().installEventFilter(chart_scroll)
        layout.addWidget(chart_scroll, 3)
        layout.addWidget(info_panel, 1)

        def _on_pick(event: Any) -> None:
            artist = getattr(event, "artist", None)
            artist_gid = (
                artist.get_gid()
                if artist is not None and hasattr(artist, "get_gid")
                else None
            )
            if not isinstance(artist_gid, str):
                return
            value: float | None = None
            label = ""
            if artist_gid.startswith("database_analytics_bar:"):
                payload = artist_gid.removeprefix("database_analytics_bar:")
                label, _separator, raw_value = payload.rpartition(":")
                try:
                    value = float(raw_value)
                except ValueError:
                    value = None
            elif artist_gid.startswith("database_analytics_label:"):
                _prefix, label = artist_gid.split(":", 1)
            else:
                return
            info_panel.setHtml(
                self._build_database_analytics_popout_info_html(
                    chart_title=chart_title,
                    label=label,
                    value=value,
                )
            )

        def _show_info_for_pick_target(label: str, value: float | None) -> None:
            info_panel.setHtml(
                self._build_database_analytics_popout_info_html(
                    chart_title=chart_title,
                    label=label,
                    value=value,
                )
            )

        def _on_click(event: Any) -> None:
            if getattr(event, "inaxes", None) is None:
                return
            mouse_event = getattr(event, "guiEvent", None) or event
            for artist in [*getattr(event.inaxes, "patches", [])]:
                artist_gid = artist.get_gid() if hasattr(artist, "get_gid") else None
                if (
                    not isinstance(artist_gid, str)
                    or not artist_gid.startswith("database_analytics_bar:")
                ):
                    continue
                contains, _details = artist.contains(mouse_event)
                if not contains:
                    continue
                payload = artist_gid.removeprefix("database_analytics_bar:")
                label, _separator, raw_value = payload.rpartition(":")
                try:
                    value = float(raw_value)
                except ValueError:
                    value = None
                _show_info_for_pick_target(label, value)
                return
            for tick_label in [
                *event.inaxes.get_yticklabels(),
                *event.inaxes.get_xticklabels(),
            ]:
                artist_gid = tick_label.get_gid() if hasattr(tick_label, "get_gid") else None
                if (
                    not isinstance(artist_gid, str)
                    or not artist_gid.startswith("database_analytics_label:")
                ):
                    continue
                contains, _details = tick_label.contains(mouse_event)
                if contains:
                    _prefix, label = artist_gid.split(":", 1)
                    _show_info_for_pick_target(label, None)
                    return

        popout_canvas.mpl_connect("pick_event", _on_pick)
        popout_canvas.mpl_connect("button_press_event", _on_click)
        if hasattr(self, "_register_popout_shortcuts"):
            self._register_popout_shortcuts(dialog)
        dialog.resize(980, 720)
        dialog.show()
        popout_dialogs = getattr(self, "_database_analytics_popout_dialogs", None)
        if popout_dialogs is None:
            self._database_analytics_popout_dialogs = []
            popout_dialogs = self._database_analytics_popout_dialogs
        popout_dialogs.append(dialog)
        dialog.destroyed.connect(
            lambda _=None, dialog=dialog: popout_dialogs.remove(dialog)
            if dialog in popout_dialogs
            else None
        )

    @staticmethod
    def _format_database_count_label(label: str, count: float | int) -> str:
        if isinstance(count, float) and not float(count).is_integer():
            count_text = f"{count:,.1f}"
        else:
            count_text = f"{int(round(count)):,.0f}"
        return f"({count_text}) {label}"

    @staticmethod
    def _graph_label_decimal_places(
        max_display_value: float,
        preferred_decimals: int = 2,
    ) -> int:
        """Use decimals only when the rendered graph values stay in single digits."""
        preferred = max(0, int(preferred_decimals))
        if preferred == 0:
            return 0
        return preferred if abs(float(max_display_value)) <= 9.99 else 0

    def _format_selection_database_count_label(
        self,
        label: str,
        database_count: float | int,
        selected_count: float | int,
        show_selected: bool,
    ) -> str:
        if not show_selected:
            return self._format_database_count_label(label, database_count)
        if isinstance(selected_count, float) and not float(selected_count).is_integer():
            selected_text = f"{selected_count:,.1f}"
        else:
            selected_text = f"{int(round(selected_count)):,.0f}"
        if isinstance(database_count, float) and not float(database_count).is_integer():
            database_text = f"{database_count:,.1f}"
        else:
            database_text = f"{int(round(database_count)):,.0f}"
        database_count_value = float(database_count)
        selected_count_value = float(selected_count)
        percent_text = (
            _format_percent(selected_count_value / database_count_value)
            if database_count_value
            else "0%"
        )
        return f"({selected_text} of {database_text} : {percent_text}) {label}"

    def _extract_human_design_profile(
        self,
        chart: Any,
    ) -> tuple[list[int], list[int], list[str], list[str], str, str]:
        if getattr(chart, "positions", None):
            try:
                hd_gates, hd_lines, hd_channels, hd_type = derive_human_design_profile(chart)
            except Exception:
                hd_gates, hd_lines, hd_channels, hd_type = [], [], [], ""
            try:
                hd_result = build_human_design_result(chart)
            except Exception:
                hd_result = None
            hd_defined_centers = sorted(
                {
                    str(center).strip()
                    for center in getattr(hd_result, "defined_centers", [])
                    if str(center).strip()
                },
                key=lambda center_name: (
                    self.HD_DEFINED_CENTER_ORDER.index(center_name)
                    if center_name in self.HD_DEFINED_CENTER_ORDER
                    else len(self.HD_DEFINED_CENTER_ORDER),
                    center_name,
                ),
            )
            chart.human_design_gates = list(hd_gates)
            chart.human_design_lines = list(hd_lines)
            chart.human_design_channels = list(hd_channels)
            chart.human_design_defined_centers = list(hd_defined_centers)
            if hd_type:
                chart.human_design_type = hd_type
            hd_authority = canonicalize_hd_authority_label(
                str(getattr(hd_result, "authority", "")).strip()
            )
            if not hd_type:
                hd_type = str(getattr(chart, "human_design_type", "") or "").strip()
            if not hd_authority:
                hd_authority = canonicalize_hd_authority_label(
                    str(getattr(chart, "human_design_authority", "") or "").strip()
                )
            hd_profile = str(getattr(hd_result, "profile", "") or "").strip()
            if hd_profile:
                chart.human_design_profile = hd_profile
            if hd_authority:
                chart.human_design_authority = hd_authority
            return hd_gates, hd_lines, hd_channels, hd_defined_centers, hd_type, hd_authority

        hd_gates = [
            int(gate)
            for gate in (getattr(chart, "human_design_gates", []) or [])
            if isinstance(gate, int) and 1 <= int(gate) <= 64
        ]
        hd_lines = [
            int(line)
            for line in (getattr(chart, "human_design_lines", []) or [])
            if isinstance(line, int) and 1 <= int(line) <= 6
        ]
        hd_channels = [
            str(channel)
            for channel in (getattr(chart, "human_design_channels", []) or [])
            if str(channel).strip()
        ]
        hd_defined_centers = [
            str(center)
            for center in (getattr(chart, "human_design_defined_centers", []) or [])
            if str(center).strip()
        ]
        hd_type = str(getattr(chart, "human_design_type", "") or "").strip()
        hd_authority = canonicalize_hd_authority_label(
            str(getattr(chart, "human_design_authority", "") or "").strip()
        )
        return hd_gates, hd_lines, hd_channels, hd_defined_centers, hd_type, hd_authority


    @staticmethod
    def _format_human_design_incarnation_cross_label(label: str) -> str:
        label_text = str(label or "").strip()
        cross = find_cross_by_name(label_text)
        if cross:
            return str(cross.get("full_name") or label_text)
        gate_values = [int(value) for value in re.findall(r"\d+", label_text)]
        if len(gate_values) >= 4:
            matches = find_crosses_by_gates(
                gate_values[0],
                gate_values[1],
                gate_values[2],
                gate_values[3],
            )
            if matches:
                return str(matches[0].get("full_name") or label_text)
        return label_text

    @staticmethod
    def _format_human_design_type_label(label: str) -> str:
        if str(label).strip() == "Manifesting Generator":
            return "MF Generator"
        return str(label)

    @staticmethod
    def _human_design_mode_payload(
        mode: str,
        selection_cache: dict[str, Any],
        database_cache: dict[str, Any],
    ) -> tuple[list[str], dict[str, int], dict[str, int], float, float]:
        if mode == "hd_profiles":
            labels = list(DatabaseAnalyticsChartsMixin.HD_STANDARD_PROFILES)
            selection_counts = {
                label: int(selection_cache["human_design_profile_totals"].get(label, 0))
                for label in labels
            }
            database_counts = {
                label: int(database_cache["human_design_profile_totals"].get(label, 0))
                for label in labels
            }
            return (
                labels,
                selection_counts,
                database_counts,
                float(selection_cache["human_design_profile_total_count"]),
                float(database_cache["human_design_profile_total_count"]),
            )
        if mode == "hd_incarnation_crosses":
            raw_labels = sorted(
                set(selection_cache["human_design_incarnation_cross_totals"].keys())
                | set(database_cache["human_design_incarnation_cross_totals"].keys())
            )
            selection_counts: dict[str, int] = {}
            database_counts: dict[str, int] = {}
            for raw_label in raw_labels:
                display_label = DatabaseAnalyticsChartsMixin._format_human_design_incarnation_cross_label(raw_label)
                selection_counts[display_label] = selection_counts.get(display_label, 0) + int(
                    selection_cache["human_design_incarnation_cross_totals"].get(raw_label, 0)
                )
                database_counts[display_label] = database_counts.get(display_label, 0) + int(
                    database_cache["human_design_incarnation_cross_totals"].get(raw_label, 0)
                )
            labels = sorted(set(selection_counts.keys()) | set(database_counts.keys()))
            return (
                labels,
                selection_counts,
                database_counts,
                float(selection_cache["human_design_incarnation_cross_total_count"]),
                float(database_cache["human_design_incarnation_cross_total_count"]),
            )
        if mode == "hd_types":
            raw_labels = list(DatabaseAnalyticsChartsMixin.HD_STANDARD_TYPES)
            labels = [
                DatabaseAnalyticsChartsMixin._format_human_design_type_label(label)
                for label in raw_labels
            ]
            selection_counts = {
                DatabaseAnalyticsChartsMixin._format_human_design_type_label(label): int(
                    selection_cache["human_design_type_totals"].get(label, 0)
                )
                for label in raw_labels
            }
            database_counts = {
                DatabaseAnalyticsChartsMixin._format_human_design_type_label(label): int(
                    database_cache["human_design_type_totals"].get(label, 0)
                )
                for label in raw_labels
            }
            return (
                labels,
                selection_counts,
                database_counts,
                float(selection_cache["human_design_type_total_count"]),
                float(database_cache["human_design_type_total_count"]),
            )
        if mode == "hd_authorities":
            labels = list(DatabaseAnalyticsChartsMixin.HD_STANDARD_AUTHORITIES)
            selection_counts = {
                label: int(selection_cache["human_design_authority_totals"].get(label, 0))
                for label in labels
            }
            database_counts = {
                label: int(database_cache["human_design_authority_totals"].get(label, 0))
                for label in labels
            }
            return (
                labels,
                selection_counts,
                database_counts,
                float(selection_cache["human_design_authority_total_count"]),
                float(database_cache["human_design_authority_total_count"]),
            )
        if mode == "hd_lines":
            labels = [str(line) for line in range(1, 7)]
            selection_counts = {
                label: int(selection_cache["human_design_line_totals"].get(int(label), 0))
                for label in labels
            }
            database_counts = {
                label: int(database_cache["human_design_line_totals"].get(int(label), 0))
                for label in labels
            }
            return (
                labels,
                selection_counts,
                database_counts,
                float(selection_cache["human_design_line_total_count"]),
                float(database_cache["human_design_line_total_count"]),
            )
        if mode == "hd_channels":
            labels = sorted(
                set(selection_cache["human_design_channel_totals"].keys())
                | set(database_cache["human_design_channel_totals"].keys()),
                key=lambda label: (
                    int(label.split("-")[0]) if "-" in label and label.split("-")[0].isdigit() else 999,
                    int(label.split("-")[1]) if "-" in label and len(label.split("-")) > 1 and label.split("-")[1].isdigit() else 999,
                    str(label),
                ),
            )
            selection_counts = {
                label: int(selection_cache["human_design_channel_totals"].get(label, 0))
                for label in labels
            }
            database_counts = {
                label: int(database_cache["human_design_channel_totals"].get(label, 0))
                for label in labels
            }
            return (
                labels,
                selection_counts,
                database_counts,
                float(selection_cache["human_design_channel_total_count"]),
                float(database_cache["human_design_channel_total_count"]),
            )
        if mode == "hd_defined_centers":
            labels = list(DatabaseAnalyticsChartsMixin.HD_DEFINED_CENTER_ORDER)
            selection_counts = {
                label: int(selection_cache["human_design_defined_center_totals"].get(label, 0))
                for label in labels
            }
            database_counts = {
                label: int(database_cache["human_design_defined_center_totals"].get(label, 0))
                for label in labels
            }
            return (
                labels,
                selection_counts,
                database_counts,
                float(selection_cache["human_design_defined_center_total_count"]),
                float(database_cache["human_design_defined_center_total_count"]),
            )
        labels = [str(gate) for gate in range(1, 65)]
        selection_counts = {
            label: int(selection_cache["human_design_gate_totals"].get(int(label), 0))
            for label in labels
        }
        database_counts = {
            label: int(database_cache["human_design_gate_totals"].get(int(label), 0))
            for label in labels
        }
        return (
            labels,
            selection_counts,
            database_counts,
            float(selection_cache["human_design_gate_total_count"]),
            float(database_cache["human_design_gate_total_count"]),
        )

     #DB View's Lefthand Panel: Selection Comparison Chart 2: Relationship Distribution Chart

    def _standard_deviation_indicators_visible(self) -> bool:
        visibility = getattr(self, "_visibility", None)
        if visibility is None:
            return True
        return bool(visibility.get("charts.standard_deviation_indicators"))

    def _draw_category_significance_guides(
        self,
        ax: Any,
        selection_counts: Sequence[float | int] | Mapping[str, float | int],
        database_counts: Sequence[float | int] | Mapping[str, float | int],
        loaded_charts: int | float,
        selection_total: float | None = None,
        database_total: float | None = None,
    ) -> None:
        if not self._standard_deviation_indicators_visible():
            return
        if float(loaded_charts or 0) <= 0:
            return
        if isinstance(selection_counts, Mapping):
            if isinstance(database_counts, Mapping):
                labels = [
                    *selection_counts.keys(),
                    *(label for label in database_counts.keys() if label not in selection_counts),
                ]
                selection_count_values = [selection_counts.get(label, 0) for label in labels]
                database_count_values = [database_counts.get(label, 0) for label in labels]
            else:
                selection_count_values = list(selection_counts.values())
                database_count_values = list(database_counts)
        else:
            selection_count_values = list(selection_counts)
            if isinstance(database_counts, Mapping):
                database_count_values = list(database_counts.values())
            else:
                database_count_values = list(database_counts)
        correction = getattr(self, "_significance_correction", "benjamini_hochberg")
        results = compute_proportion_significance_results(
            selection_counts=selection_count_values,
            database_counts=database_count_values,
            loaded_charts=loaded_charts,
            correction=correction,
            selection_total=selection_total,
            database_total=database_total,
        )
        sigma = typical_standard_error(results)
        if sigma is None:
            sigma = self._typical_single_selection_standard_error(
                selection_counts=selection_count_values,
                database_counts=database_count_values,
                selection_total=selection_total,
                database_total=database_total,
            )
        draw_standard_deviation_guides(
            ax,
            sigma,
            max_sigma=2,
            label_prefix="SE",
        )

    @staticmethod
    def _typical_single_selection_standard_error(
        *,
        selection_counts: list[float | int],
        database_counts: list[float | int],
        selection_total: float | None = None,
        database_total: float | None = None,
    ) -> float | None:
        resolved_selection_total = (
            float(selection_total)
            if selection_total is not None
            else float(sum(max(0.0, float(value)) for value in selection_counts))
        )
        resolved_database_total = (
            float(database_total)
            if database_total is not None
            else float(sum(max(0.0, float(value)) for value in database_counts))
        )
        if resolved_selection_total <= 0.0 or resolved_database_total <= 0.0:
            return None
        values: list[float] = []
        for database_count in database_counts:
            p_database = max(0.0, float(database_count)) / resolved_database_total
            variance = p_database * (1.0 - p_database) / resolved_selection_total
            if resolved_database_total > 1.0 and 0.0 < resolved_selection_total < resolved_database_total:
                variance *= max(0.0, (resolved_database_total - resolved_selection_total) / (resolved_database_total - 1.0))
            if variance > 0.0:
                values.append(math.sqrt(variance))
        if not values:
            return None
        return math.sqrt(sum(value * value for value in values) / len(values))

    def _build_relationship_distribution_chart(
        self,
        selection_relationships: dict[str, float],
        database_relationships: dict[str, float],
        selection_relationship_counts: dict[str, float],
        database_relationship_counts: dict[str, float],
        loaded_charts: int,
        bar_height: float = 0.6,
    ) -> FigureCanvas:
        relationship_figure = Figure(figsize=(2.7, 5.8))
        relationship_figure.patch.set_facecolor(self._database_analytics_figure_facecolor())
        relationship_ax = relationship_figure.add_subplot(111)
        relationship_ax.set_facecolor(self._database_analytics_axes_facecolor())
        relationship_labels = list(RELATION_TYPE)
        relationship_display_labels = [
            self._format_selection_database_count_label(
                relationship,
                database_relationship_counts.get(relationship, 0),
                selection_relationship_counts.get(relationship, 0),
                loaded_charts > 0,
            )
            for relationship in relationship_labels
        ]
        relationship_positions = list(range(len(relationship_labels)))
        relationship_colors = get_cycled_earthtone_colors(len(relationship_labels))
        selection_values = [
            selection_relationships[relationship]
            for relationship in relationship_labels
        ]
        database_values = [
            database_relationships[relationship]
            for relationship in relationship_labels
        ]
        if loaded_charts == 0:
            relationship_bars = relationship_ax.barh(
                relationship_positions,
                database_values,
                color=relationship_colors,
                height=bar_height,
                zorder=2,
            )
            relationship_ax.set_xlim(0, 1)
            relationship_ax.set_yticks(
                relationship_positions,
                labels=relationship_display_labels,
            )
            relationship_ax.invert_yaxis()
            self._set_compact_barh_y_limits(relationship_ax, len(relationship_labels), bar_height)
            relationship_ax.tick_params(axis="y", **CHART_AXES_STYLE["y_tick"])
            relationship_ax.tick_params(axis="x", **CHART_AXES_STYLE["x_tick"])
            relationship_ax.set_xlabel("")
            relationship_ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            relationship_ax.set_xticklabels(
                [_format_percent(value) for value in [0, 0.25, 0.5, 0.75, 1.0]]
            )
            for bar, database_value in zip(relationship_bars, database_values):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                label_x = min(database_value + 0.02, 0.95)
                relationship_ax.text(
                    label_x,
                    bar_center,
                    _format_percent(database_value),
                    va="center",
                    ha="left",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            differences = [
                selection - database
                for selection, database in zip(selection_values, database_values)
            ]
            widths = [abs(value) for value in differences]
            relationship_bars = relationship_ax.barh(
                relationship_positions,
                widths,
                left=[
                    0 if value >= 0 else -abs(value) for value in differences
                ],
                color=relationship_colors,
                height=bar_height,
                zorder=2,
            )
            relationship_axis_limit = self._configure_symmetric_percent_difference_axis(
                relationship_ax,
                differences,
            )
            relationship_ax.set_yticks(
                relationship_positions,
                labels=relationship_display_labels,
            )
            relationship_ax.invert_yaxis()
            self._set_compact_barh_y_limits(relationship_ax, len(relationship_labels), bar_height)
            relationship_ax.tick_params(axis="y", **CHART_AXES_STYLE["y_tick"])
            relationship_ax.tick_params(axis="x", **CHART_AXES_STYLE["x_tick"])
            relationship_ax.set_xlabel("")
            relationship_ax.axvline(
                0,
                color=CHART_THEME_COLORS["spine"],
                linewidth=1.5,
                zorder=1,
            )
            self._draw_category_significance_guides(
                relationship_ax,
                [selection_relationship_counts.get(label, 0) for label in relationship_labels],
                [database_relationship_counts.get(label, 0) for label in relationship_labels],
                loaded_charts,
            )
            for bar, diff_value in zip(relationship_bars, differences):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                selection_value = bar.get_width()
                if selection_value > 0:
                    label_value = abs(diff_value)
                    label_x = self._difference_label_x(diff_value, relationship_axis_limit)
                    relationship_ax.text(
                        label_x,
                        bar_center,
                        _format_percent(label_value),
                        va="center",
                        ha="left" if diff_value >= 0 else "right",
                        color=CHART_THEME_COLORS["text"],
                        fontsize=7.5,
                    )
        for spine in relationship_ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in relationship_ax.get_yticklabels():
            tick_label.set_ha("right")
        self._apply_tight_layout(relationship_figure)
        
        relationship_figure.subplots_adjust(left=0.51, bottom=0.12, right=0.97, top=0.98)
        #relationship_figure.subplots_adjust(**CHART_AXES_STYLE["barh_adjust"])

        relationship_canvas = FigureCanvas(relationship_figure)
        self._configure_left_panel_canvas(
            relationship_canvas,
            relationship_figure,
        )
        relationship_canvas.draw_idle()
        return relationship_canvas

    #DB View's Lefthand Panel: Selection Comparison Chart 1: Sentiment Distribution Chart
    def _build_sentiment_chart(
        self,
        display_labels: list[str],
        selection_values: list[float],
        database_values: list[float],
        selection_counts: list[float],
        database_counts: list[float],
        loaded_charts: int,
        positive_labels: list[str],
        negative_labels: list[str],
        positive_total_label: str,
        negative_total_label: str,
    ) -> FigureCanvas:
        # DB View's lefthand panel top graph dimensions
        figure = Figure(figsize=(1.5, 6.8))  # graph dimensions
        figure.patch.set_facecolor(self._database_analytics_figure_facecolor())
        ax = figure.add_subplot(111)
        ax.set_facecolor(self._database_analytics_axes_facecolor())
        positive_total_color = "#39ff14"
        negative_total_color = "#ff1744"
        negative_start_display = len(positive_labels) + 1
        if negative_labels:
            ax.axhspan(
                negative_start_display - 0.5,
                len(display_labels) - 0.5,
                facecolor="#222222",
                zorder=0,
            )

        colors = []
        for label in display_labels:
            if label == positive_total_label:
                colors.append(positive_total_color)
            elif label == negative_total_label:
                colors.append(negative_total_color)
            else:
                colors.append(SENTIMENT_COLORS.get(label, "#6fa8dc"))
        display_labels_with_counts = [
            self._format_selection_database_count_label(
                label,
                database_count,
                selection_count,
                loaded_charts > 0,
            )
            for label, selection_count, database_count in zip(
                display_labels,
                selection_counts,
                database_counts,
            )
        ]
        y_positions = list(range(len(display_labels)))
        bar_height = 0.6  # how tall (or wide for horizontal graphs) are the bars?
        if loaded_charts == 0:
            selection_bars = ax.barh(
                y_positions,
                database_values,
                color=colors,
                height=bar_height,
                zorder=2,
            )
            self._set_x_limits_with_padding(ax, 0, 1)
            ax.set_yticks(y_positions, labels=display_labels_with_counts)
            ax.invert_yaxis()
            self._set_compact_barh_y_limits(ax, len(display_labels), bar_height)
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.set_xlabel("")
            ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            ax.set_xticklabels(
                [_format_percent(value) for value in [0, 0.25, 0.5, 0.75, 1.0]]
            )
            for bar, database_value in zip(selection_bars, database_values):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                label_x = min(database_value + 0.02, 0.95)
                ax.text(
                    label_x,
                    bar_center,
                    _format_percent(database_value),
                    va="center",
                    ha="left",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            difference_values = [
                selection - database
                for selection, database in zip(selection_values, database_values)
            ]
            difference_widths = [abs(value) for value in difference_values]
            selection_bars = ax.barh(
                y_positions,
                difference_widths,
                left=[
                    0 if value >= 0 else -abs(value)
                    for value in difference_values
                ],
                color=colors,
                height=bar_height,
                zorder=2,
            )
            axis_limit = self._configure_symmetric_percent_difference_axis(ax, difference_values)
            ax.set_yticks(y_positions, labels=display_labels_with_counts)
            ax.invert_yaxis()
            self._set_compact_barh_y_limits(ax, len(display_labels), bar_height)
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.set_xlabel("")
            ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            for bar, difference_value in zip(selection_bars, difference_values):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                selection_value = bar.get_width()
                if selection_value > 0:
                    label_value = abs(difference_value)
                    label_x = self._difference_label_x(difference_value, axis_limit)
                    ax.text(
                        label_x,
                        bar_center,
                        _format_percent(label_value),
                        va="center",
                        ha="left" if difference_value >= 0 else "right",
                        color=CHART_THEME_COLORS["text"],
                        fontsize=7.5,
                    )
        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label, label in zip(ax.get_yticklabels(), display_labels):
            tick_label.set_ha("right")
            if label == positive_total_label:
                tick_label.set_color(positive_total_color)
            elif label == negative_total_label:
                tick_label.set_color(negative_total_color)        
        self._apply_tight_layout(figure)
        # DB View's lefthand panel's graph margins.
        # Lower the top bound to reserve space for the title.
        figure.subplots_adjust(left=0.51, bottom=0.12, right=0.97, top=0.98)

        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas
                
    #DB View's Lefthand Panel: Selection Comparison Chart 2: Sign Distribution Chart
    def _build_sign_distribution_chart(
        self,
        selection_signs: dict[str, float],
        database_signs: dict[str, float],
        selection_sign_counts: dict[str, float],
        database_sign_counts: dict[str, float],
        loaded_charts: int,
        bar_height: float = 0.6,
    ) -> FigureCanvas:
        # DB View's lefthand panel graph dimensions (for sign graph)?
        sign_figure = Figure(figsize=(2.7, 5.8))
        sign_figure.patch.set_facecolor(self._database_analytics_figure_facecolor())
        sign_ax = sign_figure.add_subplot(111)
        sign_ax.set_facecolor(self._database_analytics_axes_facecolor())
        sign_labels = list(ZODIAC_NAMES)
        sign_display_labels = [
            self._format_selection_database_count_label(
                sign,
                database_sign_counts.get(sign, 0),
                selection_sign_counts.get(sign, 0),
                loaded_charts > 0,
            )
            for sign in sign_labels
        ]
        sign_colors = [SIGN_COLORS.get(sign, "#6fa8dc") for sign in sign_labels]
        sign_positions = list(range(len(sign_labels)))
        selection_sign_values = [selection_signs[sign] for sign in sign_labels]
        database_sign_values = [database_signs[sign] for sign in sign_labels]
        if loaded_charts == 0:
            sign_bars = sign_ax.barh(
                sign_positions,
                database_sign_values,
                color=sign_colors,
                height=bar_height,
                zorder=2,
            )
            sign_ax.set_xlim(0, 1)
            sign_ax.set_yticks(sign_positions, labels=sign_display_labels)
            sign_ax.invert_yaxis()
            self._set_compact_barh_y_limits(sign_ax, len(sign_labels), bar_height)
            sign_ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            sign_ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            sign_ax.set_xlabel("")
            sign_ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            sign_ax.set_xticklabels(
                [_format_percent(value) for value in [0, 0.25, 0.5, 0.75, 1.0]]
            )
            for bar, database_value in zip(sign_bars, database_sign_values):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                label_x = min(database_value + 0.02, 0.95)
                sign_ax.text(
                    label_x,
                    bar_center,
                    _format_percent(database_value),
                    va="center",
                    ha="left",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            sign_differences = [
                selection - database
                for selection, database in zip(
                    selection_sign_values,
                    database_sign_values,
                )
            ]
            sign_widths = [abs(value) for value in sign_differences]
            sign_bars = sign_ax.barh(
                sign_positions,
                sign_widths,
                left=[
                    0 if value >= 0 else -abs(value)
                    for value in sign_differences
                ],
                color=sign_colors,
                height=bar_height,
                zorder=2,
            )
            sign_axis_limit = self._configure_symmetric_percent_difference_axis(sign_ax, sign_differences)
            sign_ax.set_yticks(sign_positions, labels=sign_display_labels)
            sign_ax.invert_yaxis()
            self._set_compact_barh_y_limits(sign_ax, len(sign_labels), bar_height)
            sign_ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            sign_ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            sign_ax.set_xlabel("")
            sign_ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            self._draw_category_significance_guides(
                sign_ax,
                [selection_sign_counts.get(label, 0) for label in sign_labels],
                [database_sign_counts.get(label, 0) for label in sign_labels],
                loaded_charts,
            )
            for bar, diff_value in zip(sign_bars, sign_differences):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                selection_value = bar.get_width()
                if selection_value > 0:
                    label_value = abs(diff_value)
                    label_x = self._difference_label_x(diff_value, sign_axis_limit)
                    sign_ax.text(
                        label_x,
                        bar_center,
                        _format_percent(label_value),
                        va="center",
                        ha="left" if diff_value >= 0 else "right",
                        color=CHART_THEME_COLORS["text"],
                        fontsize=7.5,
                    )
        for spine in sign_ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in sign_ax.get_yticklabels():
            tick_label.set_ha("right")
        self._apply_tight_layout(sign_figure)
        sign_figure.subplots_adjust(left=0.51, bottom=0.12, right=0.97, top=0.98)

        sign_canvas = FigureCanvas(sign_figure)
        self._configure_left_panel_canvas(sign_canvas, sign_figure)
        sign_canvas.draw_idle()
        return sign_canvas

    #DB View's Lefthand Panel: Selection Comparison Chart 3: Dominant Sign Chart
    def _build_dominant_sign_chart(
        self,
        selection_signs: dict[str, float],
        database_signs: dict[str, float],
        selection_sign_counts: dict[str, float],
        database_sign_counts: dict[str, float],
        loaded_charts: int,
        bar_height: float = 0.6,
        sign_labels: list[str] | None = None,
        selection_total: float | None = None,
        database_total: float | None = None,
        include_significance_guides: bool = True,
        label_tooltips: dict[str, str] | None = None,
    ) -> FigureCanvas:
        dominant_figure = Figure(figsize=(2.7, 5.8))
        dominant_figure.patch.set_facecolor(self._database_analytics_figure_facecolor())
        dominant_ax = dominant_figure.add_subplot(111)
        dominant_ax.set_facecolor(self._database_analytics_axes_facecolor())
        sign_labels = list(sign_labels or ZODIAC_NAMES)
        sign_display_labels = [
            self._format_selection_database_count_label(
                sign,
                database_sign_counts.get(sign, 0),
                selection_sign_counts.get(sign, 0),
                loaded_charts > 0,
            )
            for sign in sign_labels
        ]
        sign_colors = [SIGN_COLORS.get(sign, "#6fa8dc") for sign in sign_labels]
        sign_positions = list(range(len(sign_labels)))
        selection_sign_values = [selection_signs[sign] for sign in sign_labels]
        database_sign_values = [database_signs[sign] for sign in sign_labels]
        if loaded_charts == 0:
            sign_bars = dominant_ax.barh(
                sign_positions,
                database_sign_values,
                color=sign_colors,
                height=bar_height,
                zorder=2,
            )
            dominant_ax.set_xlim(0, 1)
            dominant_ax.set_yticks(sign_positions, labels=sign_display_labels)
            dominant_ax.invert_yaxis()
            self._set_compact_barh_y_limits(dominant_ax, len(sign_labels), bar_height)
            dominant_ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            dominant_ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            dominant_ax.set_xlabel("")
            dominant_ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            dominant_ax.set_xticklabels(
                [_format_percent(value) for value in [0, 0.25, 0.5, 0.75, 1.0]]
            )
            for bar, database_value in zip(sign_bars, database_sign_values):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                label_x = min(database_value + 0.02, 0.95)
                dominant_ax.text(
                    label_x,
                    bar_center,
                    _format_percent(database_value),
                    va="center",
                    ha="left",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            sign_differences = [
                selection - database
                for selection, database in zip(
                    selection_sign_values,
                    database_sign_values,
                )
            ]
            sign_widths = [abs(value) for value in sign_differences]
            sign_bars = dominant_ax.barh(
                sign_positions,
                sign_widths,
                left=[
                    0 if value >= 0 else -abs(value)
                    for value in sign_differences
                ],
                color=sign_colors,
                height=bar_height,
                zorder=2,
            )
            dominant_axis_limit = self._configure_symmetric_percent_difference_axis(dominant_ax, sign_differences)
            dominant_ax.set_yticks(sign_positions, labels=sign_display_labels)
            dominant_ax.invert_yaxis()
            self._set_compact_barh_y_limits(dominant_ax, len(sign_labels), bar_height)
            dominant_ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            dominant_ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            dominant_ax.set_xlabel("")
            dominant_ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            if include_significance_guides:
                self._draw_category_significance_guides(
                    dominant_ax,
                    [selection_sign_counts.get(label, 0) for label in sign_labels],
                    [database_sign_counts.get(label, 0) for label in sign_labels],
                    loaded_charts,
                    selection_total=selection_total,
                    database_total=database_total,
                )
            for bar, diff_value in zip(sign_bars, sign_differences):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                selection_value = bar.get_width()
                if selection_value > 0:
                    label_value = abs(diff_value)
                    label_x = self._difference_label_x(diff_value, dominant_axis_limit)
                    dominant_ax.text(
                        label_x,
                        bar_center,
                        _format_percent(label_value),
                        va="center",
                        ha="left" if diff_value >= 0 else "right",
                        color=CHART_THEME_COLORS["text"],
                        fontsize=7.5,
                    )
        for spine in dominant_ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in dominant_ax.get_yticklabels():
            tick_label.set_ha("right")
        self._apply_tight_layout(dominant_figure)
        dominant_figure.subplots_adjust(left=0.51, bottom=0.12, right=0.97, top=0.98)

        dominant_canvas = FigureCanvas(dominant_figure)
        self._configure_left_panel_canvas(dominant_canvas, dominant_figure)
        dominant_canvas.draw_idle()
        return dominant_canvas

    def _build_dominant_planet_chart(
        self,
        selection_planets: dict[str, float],
        database_planets: dict[str, float],
        selection_planet_counts: dict[str, float],
        database_planet_counts: dict[str, float],
        loaded_charts: int,
        include_count_prefixes: bool = True,
        bar_height: float = 0.6,
        labels: list[str] | None = None,
        height_scale: float = 1.0,
        force_value_fallback_colors: bool = False,
        label_colors: dict[str, str] | None = None,
        selection_total: float | None = None,
        database_total: float | None = None,
        include_significance_guides: bool = True,
        label_tooltips: dict[str, str] | None = None,
        auto_height: bool = False,
    ) -> FigureCanvas:
        labels = list(labels or selection_planets.keys())
        clamped_height_scale = max(0.5, float(height_scale))
        chart_height = (
            max(2.9, min(14.0, (len(labels) * 0.38) + 1.0))
            if auto_height
            else 4 * clamped_height_scale
        )
        # Keep bottom margin visually consistent in pixels when chart height is scaled up.
        scaled_bottom_margin = min(0.12, max(0.02, 0.12 / clamped_height_scale))
        figure = Figure(figsize=(1.5, chart_height)) #width of graph, height of graph
        figure.patch.set_facecolor(self._database_analytics_figure_facecolor())
        ax = figure.add_subplot(111)
        ax.set_facecolor(self._database_analytics_axes_facecolor())
        display_label_by_label = {
            label: _abbreviate_nakshatra_label(str(label))
            for label in labels
        }
        if include_count_prefixes:
            display_labels = [
                self._format_selection_database_count_label(
                    display_label_by_label.get(label, str(label)),
                    database_planet_counts.get(label, 0),
                    selection_planet_counts.get(label, 0),
                    loaded_charts > 0,
                )
                for label in labels
            ]
        else:
            display_labels = [display_label_by_label.get(label, str(label)) for label in labels]
        def _resolve_distribution_color(label: str) -> str:
            authority_key = normalize_hd_authority_key(
                canonicalize_hd_authority_label(str(label).strip())
            )
            authority_color = HD_AUTHORITY_COLORS.get(authority_key)
            if authority_color:
                return authority_color
            if label in DatabaseAnalyticsChartsMixin.HD_CENTER_COLORS:
                return DatabaseAnalyticsChartsMixin.HD_CENTER_COLORS[label]
            return PLANET_COLORS.get(
                label,
                HOUSE_COLORS.get(
                    label,
                    ELEMENT_COLORS.get(
                        label,
                        NAKSHATRA_PLANET_COLOR.get(label, (None, "#6fa8dc"))[1],
                    ),
                ),
            )
        positions = list(range(len(labels)))
        selection_values = [selection_planets[label] for label in labels]
        database_values = [database_planets[label] for label in labels]
        displayed_value_by_label = {
            label: (
                abs(selection_values[index] - database_values[index])
                if loaded_charts > 0
                else database_values[index]
            )
            for index, label in enumerate(labels)
        }
        value_min = min(displayed_value_by_label.values(), default=0.0)
        value_max = max(displayed_value_by_label.values(), default=1.0)
        colors = []
        for label in labels:
            custom_color = str((label_colors or {}).get(label, "")).strip()
            resolved_color = custom_color or _resolve_distribution_color(label)
            use_value_fallback = force_value_fallback_colors or resolved_color == "#6fa8dc"
            if use_value_fallback:
                colors.append(
                    self._value_length_color(displayed_value_by_label.get(label, 0.0), value_min, value_max)
                )
            else:
                colors.append(resolved_color)
        if loaded_charts == 0:
            bars = ax.barh(positions, database_values, color=colors, height=bar_height, zorder=2)
            _, axis_max = self._configure_positive_percent_axis(ax, database_values)
            label_decimals = self._graph_label_decimal_places(
                max((value * 100.0 for value in database_values), default=0.0),
                preferred_decimals=2,
            )
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            self._set_compact_barh_y_limits(ax, len(labels), bar_height)
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            for bar, database_value in zip(bars, database_values):
                label_offset = max(axis_max * 0.015, 0.0015)
                label_x = min(database_value + label_offset, axis_max * 0.985)
                ax.text(label_x, bar.get_y() + (bar.get_height() / 2), _format_percent(database_value, decimals=label_decimals), va="center", ha="left", color=CHART_THEME_COLORS["text"], fontsize=7.5)
        else:
            differences = [selection - database for selection, database in zip(selection_values, database_values)]
            widths = [abs(value) for value in differences]
            bars = ax.barh(
                positions,
                widths,
                left=[0 if value >= 0 else -abs(value) for value in differences],
                color=colors,
                height=bar_height,
                zorder=2,
            )
            axis_limit = self._configure_symmetric_percent_difference_axis(ax, differences)
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            self._set_compact_barh_y_limits(ax, len(labels), bar_height)
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            if include_significance_guides:
                self._draw_category_significance_guides(
                    ax,
                    [selection_planet_counts.get(label, 0) for label in labels],
                    [database_planet_counts.get(label, 0) for label in labels],
                    loaded_charts,
                    selection_total=selection_total,
                    database_total=database_total,
                )
            for bar, diff_value in zip(bars, differences):
                width = bar.get_width()
                if width <= 0:
                    continue
                label_x = width if diff_value >= 0 else -width
                label_x = self._difference_label_x(diff_value, axis_limit)
                ax.text(label_x, bar.get_y() + (bar.get_height() / 2), _format_percent(abs(diff_value)), va="center", ha="left" if diff_value >= 0 else "right", color=CHART_THEME_COLORS["text"], fontsize=7.5)

        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for index, tick_label in enumerate(ax.get_yticklabels()):
            tick_label.set_ha("right")
            if label_colors is not None and index < len(colors):
                tick_label.set_color(colors[index])
        self._apply_tight_layout(figure)
        figure.subplots_adjust(left=0.51, bottom=scaled_bottom_margin, right=0.97, top=0.98)
        canvas = FigureCanvas(figure)
        self._attach_database_analytics_tick_label_tooltips(canvas, figure, label_tooltips)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas

    def _build_dominant_house_chart(
        self,
        selection_houses: dict[str, float],
        database_houses: dict[str, float],
        selection_house_counts: dict[str, float],
        database_house_counts: dict[str, float],
        loaded_charts: int,
        bar_height: float = 0.6,
        labels: list[str] | None = None,
        selection_total: float | None = None,
        database_total: float | None = None,
        include_significance_guides: bool = True,
    ) -> FigureCanvas:
        return self._build_dominant_planet_chart(
            selection_planets=selection_houses,
            database_planets=database_houses,
            selection_planet_counts=selection_house_counts,
            database_planet_counts=database_house_counts,
            loaded_charts=loaded_charts,
            bar_height=bar_height,
            labels=labels,
            selection_total=selection_total,
            database_total=database_total,
            include_significance_guides=include_significance_guides,
        )

    def _build_gender_distribution_chart(
        self,
        labels: list[str],
        selection_values: dict[str, float],
        database_values: dict[str, float],
        selection_counts: dict[str, int],
        database_counts: dict[str, int],
        loaded_charts: int,
        bar_height: float = 0.6,
    ) -> FigureCanvas:
        figure = Figure(figsize=(1.5, max(2.8, min(8.0, (len(labels) * 0.42) + 0.8))))
        figure.patch.set_facecolor(self._database_analytics_figure_facecolor())
        ax = figure.add_subplot(111)
        ax.set_facecolor(self._database_analytics_axes_facecolor())

        color_by_label = {
            "masculine": GENDER_GUESSER_COLORS["masculine"],
            "feminine": GENDER_GUESSER_COLORS["feminine"],
            "androgynous": GENDER_GUESSER_COLORS["androgynous"],
            "m": GENDER_GUESSER_COLORS["masculine"],
            "f": GENDER_GUESSER_COLORS["feminine"],
            "n/a": GENDER_GUESSER_COLORS["androgynous"],
        }
        display_labels = [
            self._format_selection_database_count_label(
                label,
                database_counts.get(label, 0),
                selection_counts.get(label, 0),
                loaded_charts > 0,
            )
            for label in labels
        ]
        colors = [
            color_by_label.get(
                str(label).strip().casefold(),
                "#6fa8dc",  # keep unknown labels such as "?" on default blue
            )
            for label in labels
        ]
        positions = list(range(len(labels)))
        selection_plot_values = [float(selection_values.get(label, 0.0)) for label in labels]
        database_plot_values = [float(database_values.get(label, 0.0)) for label in labels]

        if loaded_charts == 0:
            bars = ax.barh(positions, database_plot_values, color=colors, height=bar_height, zorder=2)
            ax.set_xlim(0, 1)
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            self._set_compact_barh_y_limits(ax, len(labels), bar_height)
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
            ax.set_xticklabels([_format_percent(value) for value in [0, 0.25, 0.5, 0.75, 1.0]])
            for bar, database_value in zip(bars, database_plot_values):
                ax.text(
                    min(database_value + 0.02, 0.95),
                    bar.get_y() + (bar.get_height() / 2),
                    _format_percent(database_value),
                    va="center",
                    ha="left",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            differences = [selection - database for selection, database in zip(selection_plot_values, database_plot_values)]
            widths = [abs(value) for value in differences]
            bars = ax.barh(
                positions,
                widths,
                left=[0 if value >= 0 else -abs(value) for value in differences],
                color=colors,
                height=bar_height,
                zorder=2,
            )
            axis_limit = self._configure_symmetric_percent_difference_axis(ax, differences)
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            self._set_compact_barh_y_limits(ax, len(labels), bar_height)
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            self._draw_category_significance_guides(
                ax,
                selection_counts,
                database_counts,
                loaded_charts,
            )
            for bar, diff_value in zip(bars, differences):
                width = bar.get_width()
                if width <= 0:
                    continue
                label_x = width if diff_value >= 0 else -width
                label_x = self._difference_label_x(diff_value, axis_limit)
                ax.text(
                    label_x,
                    bar.get_y() + (bar.get_height() / 2),
                    _format_percent(abs(diff_value)),
                    va="center",
                    ha="left" if diff_value >= 0 else "right",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )

        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in ax.get_yticklabels():
            tick_label.set_ha("right")
        self._apply_tight_layout(figure)
        figure.subplots_adjust(left=0.51, bottom=0.12, right=0.97, top=0.98)

        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas

    def _build_dominant_element_chart(
        self,
        selection_elements: dict[str, float],
        database_elements: dict[str, float],
        selection_element_counts: dict[str, float],
        database_element_counts: dict[str, float],
        loaded_charts: int,
        bar_height: float = 0.6,
    ) -> FigureCanvas:
        return self._build_dominant_planet_chart(
            selection_planets=selection_elements,
            database_planets=database_elements,
            selection_planet_counts=selection_element_counts,
            database_planet_counts=database_element_counts,
            loaded_charts=loaded_charts,
            bar_height=bar_height,
        )

    def _build_species_distribution_chart(
        self,
        selection_species: dict[str, float],
        database_species: dict[str, float],
        selection_species_counts: dict[str, float],
        database_species_counts: dict[str, float],
        loaded_charts: int,
        bar_height: float = 0.32,
        show_x_axis_labels: bool = False,
    ) -> FigureCanvas:
        labels = list(selection_species.keys())
        # Keep D&D species and class distributions visually consistent and compact
        # so the full graph remains visible above the fold.
        chart_height = 4.9
        figure = Figure(figsize=(1.5, chart_height))
        figure.patch.set_facecolor(self._database_analytics_figure_facecolor())
        ax = figure.add_subplot(111)
        ax.set_facecolor(self._database_analytics_axes_facecolor())
        display_labels = [
            self._format_selection_database_count_label(
                species,
                database_species_counts.get(species, 0),
                selection_species_counts.get(species, 0),
                loaded_charts > 0,
            )
            for species in labels
        ]
        positions = list(range(len(labels)))
        colors = get_cycled_earthtone_colors(len(labels))
        selection_values = [selection_species[species] for species in labels]
        database_values = [database_species[species] for species in labels]
        if loaded_charts == 0:
            species_bars = ax.barh(
                positions,
                database_values,
                color=colors,
                height=bar_height,
                zorder=2,
            )
            label_decimals = self._graph_label_decimal_places(
                max((value * 100.0 for value in database_values), default=0.0),
                preferred_decimals=2,
            )
            _, axis_max = self._configure_positive_percent_axis(
                ax,
                database_values,
                show_x_axis_labels=show_x_axis_labels,
            )
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            self._set_compact_barh_y_limits(ax, len(labels), bar_height)
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            if show_x_axis_labels:
                ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            else:
                ax.tick_params(axis="x", length=0, labelbottom=False)
            ax.set_xlabel("")
            for bar, database_value in zip(species_bars, database_values):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                label_offset = max(axis_max * 0.015, 0.0015)
                label_x = min(database_value + label_offset, axis_max * 0.985)
                ax.text(
                    label_x,
                    bar_center,
                    _format_percent(database_value, decimals=label_decimals),
                    va="center",
                    ha="left",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            differences = [
                selection - database
                for selection, database in zip(selection_values, database_values)
            ]
            widths = [abs(value) for value in differences]
            species_bars = ax.barh(
                positions,
                widths,
                left=[0 if value >= 0 else -abs(value) for value in differences],
                color=colors,
                height=bar_height,
                zorder=2,
            )
            axis_limit = self._configure_symmetric_percent_difference_axis(
                ax,
                differences,
                show_x_axis_labels=show_x_axis_labels,
            )
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            self._set_compact_barh_y_limits(ax, len(labels), bar_height)
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            if show_x_axis_labels:
                ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            else:
                ax.tick_params(axis="x", length=0, labelbottom=False)
            ax.set_xlabel("")
            ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            for bar, diff_value in zip(species_bars, differences):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                selection_value = bar.get_width()
                if selection_value > 0:
                    label_value = abs(diff_value)
                    label_x = self._difference_label_x(diff_value, axis_limit)
                    ax.text(
                        label_x,
                        bar_center,
                        _format_percent(label_value),
                        va="center",
                        ha="left" if diff_value >= 0 else "right",
                        color=CHART_THEME_COLORS["text"],
                        fontsize=7.5,
                    )
        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in ax.get_yticklabels():
            tick_label.set_ha("right")
        self._apply_tight_layout(figure)
        figure.subplots_adjust(left=0.51, bottom=0.12, right=0.97, top=0.98)

        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas

    def _build_social_score_summary_chart(
        self,
        labels: list[str],
        selection_values: list[float],
        database_values: list[float],
        loaded_charts: int,
        social_score_min: float | None = None,
        social_score_max: float | None = None,
        bar_height: float = 0.6,
        color_resolver: Any = None,
        fixed_axis_limit: float | None = None,
        value_precision: int = 2,
        figure_height: float = 2.8,
    ) -> FigureCanvas:
        figure = Figure(figsize=(4.8, figure_height))
        figure.patch.set_facecolor(self._database_analytics_figure_facecolor())
        ax = figure.add_subplot(111)
        ax.set_facecolor(self._database_analytics_axes_facecolor())
        def _resolve_bar_color(label: str, value: float) -> Any:
            if callable(color_resolver):
                try:
                    return color_resolver(label, value)
                except TypeError:
                    # Backward compatibility for resolver callbacks that only
                    # accept the numeric value (e.g., alignment_score_to_rgb).
                    return color_resolver(value)
            return "#6fa8dc"

        def _is_percent_metric(metric_label: str) -> bool:
            return "(%)" in metric_label

        if loaded_charts > 0:
            max_visible_value = max(
                (abs(selection - database) for selection, database in zip(selection_values, database_values)),
                default=0.0,
            )
        else:
            max_visible_value = max((abs(database) for database in database_values), default=0.0)
        decimals = self._graph_label_decimal_places(max_visible_value, value_precision)

        def _format_metric_value(metric_label: str, value: float, *, signed: bool = False) -> str:
            if _is_percent_metric(metric_label):
                return f"{value:+.{decimals}f}%" if signed else f"{value:.{decimals}f}%"
            return f"{value:+.{decimals}f}" if signed else f"{value:.{decimals}f}"

        display_labels = []
        for label, selection_value in zip(labels, selection_values):
            if loaded_charts > 0:
                display_labels.append(
                    f"({_format_metric_value(label, selection_value)}) {label}"
                )
            else:
                display_labels.append(label)

        positions = list(range(len(labels)))
        range_min = float(social_score_min) if social_score_min is not None else None
        range_max = float(social_score_max) if social_score_max is not None else None

        def _resolve_social_color(label: str, value: float) -> Any:
            if range_min is None or range_max is None:
                return _resolve_bar_color(label, value)
            return value_to_red_blue_rgb(value, range_min, range_max)

        if loaded_charts == 0:
            colors = [
                _resolve_social_color(label, value)
                for label, value in zip(labels, database_values)
            ]
            bars = ax.barh(
                positions,
                database_values,
                color=colors,
                height=bar_height,
                zorder=2,
            )
            if fixed_axis_limit is not None:
                limit = float(fixed_axis_limit)
                lower_bound = -limit
                upper_bound = limit
                ax.set_xlim(-limit, limit)
            elif range_min is not None and range_max is not None:
                limit = max(abs(range_min), abs(range_max), 1.0)
                lower_bound = -limit
                upper_bound = limit
                ax.set_xlim(-limit, limit)
            else:
                lower_bound = min(0.0, min(database_values, default=0.0))
                upper_bound = max(0.0, max(database_values, default=0.0))
                self._set_x_limits_with_padding(ax, lower_bound, upper_bound)
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            self._set_compact_barh_y_limits(ax, len(labels), bar_height)
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.set_xlabel("")
            if lower_bound < 0 < upper_bound:
                ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            for bar, label, database_value in zip(bars, labels, database_values):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                label_x = database_value + (0.6 if database_value >= 0 else -0.6)
                ax.text(
                    label_x,
                    bar_center,
                    _format_metric_value(label, database_value),
                    va="center",
                    ha="left" if database_value >= 0 else "right",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            differences = [
                selection - database
                for selection, database in zip(selection_values, database_values)
            ]
            colors = [
                _resolve_social_color(label, value)
                for label, value in zip(labels, selection_values)
            ]
            widths = [abs(value) for value in differences]
            bars = ax.barh(
                positions,
                widths,
                left=[0 if value >= 0 else -abs(value) for value in differences],
                color=colors,
                height=bar_height,
                zorder=2,
            )
            max_abs_difference = max((abs(value) for value in differences), default=0.0)
            if fixed_axis_limit is not None:
                axis_limit = float(fixed_axis_limit)
                max_abs_difference = max(max_abs_difference, axis_limit)
                ax.set_xlim(-axis_limit, axis_limit)
            elif range_min is not None and range_max is not None:
                axis_limit = self._nice_symmetric_axis_limit(
                    [range_min, range_max],
                    maximum_limit=float("inf"),
                )
                max_abs_difference = max(max_abs_difference, axis_limit)
                ax.set_xlim(-axis_limit, axis_limit)
            else:
                axis_limit = self._nice_symmetric_axis_limit(
                    differences,
                    maximum_limit=float("inf"),
                )
                max_abs_difference = max(max_abs_difference, axis_limit)
                ax.set_xlim(-axis_limit, axis_limit)
            ax.set_yticks(positions, labels=display_labels)
            ax.invert_yaxis()
            self._set_compact_barh_y_limits(ax, len(labels), bar_height)
            ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
            ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
            ax.set_xlabel("")
            ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            for bar, label, difference in zip(bars, labels, differences):
                bar_center = bar.get_y() + (bar.get_height() / 2)
                width = bar.get_width()
                if width > 0:
                    label_x = self._difference_label_x(difference, max_abs_difference)
                    ax.text(
                        label_x,
                        bar_center,
                        _format_metric_value(label, difference, signed=True),
                        va="center",
                        ha="left" if difference >= 0 else "right",
                        color=CHART_THEME_COLORS["text"],
                        fontsize=7.5,
                    )
        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in ax.get_yticklabels():
            tick_label.set_ha("right")
        # Manual margins are explicitly set for this chart; skip tight_layout to avoid
        # benign "cannot be made large enough" warnings with long axis labels.
        figure.subplots_adjust(left=0.51, bottom=0.12, right=0.97, top=0.98)

        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas

    def _build_dnd_statblock_summary_chart(
        self,
        selection_cache: dict[str, Any],
        database_cache: dict[str, Any],
        loaded_charts: int,
    ) -> FigureCanvas:
        labels = list(DND_STAT_KEYS)
        dnd_stat_colors = get_cycled_earthtone_colors(len(labels))
        stat_color_lookup = {
            label: dnd_stat_colors[index]
            for index, label in enumerate(labels)
        }
        selection_values_map = self._compute_dnd_statblock_averages(selection_cache)
        database_values_map = self._compute_dnd_statblock_averages(database_cache)
        selection_values = [selection_values_map[label] for label in labels]
        database_values = [database_values_map[label] for label in labels]
        return self._build_social_score_summary_chart(
            labels=labels,
            selection_values=selection_values,
            database_values=database_values,
            loaded_charts=loaded_charts,
            color_resolver=lambda label, _value: stat_color_lookup.get(
                label,
                DND_STAT_EARTHTONE_COLORS.get(label, "#6fa8dc"),
            ),
            fixed_axis_limit=20.0,
            value_precision=0,
        )

    def _compute_dnd_statblock_averages(
        self,
        metric_cache: dict[str, Any],
    ) -> dict[str, float]:
        labels = list(DND_STAT_KEYS)
        stat_count = float(metric_cache.get("dnd_stat_count", 0))
        stat_totals = metric_cache.get("dnd_stat_totals", {})
        return {
            label: (
                float(stat_totals.get(label, 0.0)) / stat_count
                if stat_count
                else 0.0
            )
            for label in labels
        }

    def _build_alignment_cumulative_chart(
        self,
        selection_cumulative: float,
        selection_average: float,
        database_average: float,
        loaded_charts: int,
    ) -> FigureCanvas:
        figure = Figure(figsize=(4.8, 1.6))
        figure.patch.set_facecolor(self._database_analytics_figure_facecolor())
        ax = figure.add_subplot(111)
        ax.set_facecolor(self._database_analytics_axes_facecolor())

        ax.hlines(
            y=0,
            xmin=-10,
            xmax=10,
            color=CHART_THEME_COLORS["spine"],
            linewidth=6,
            zorder=1,
            alpha=0.6,
        )
        ax.hlines(y=0, xmin=-10, xmax=0, color="#c62828", linewidth=4, zorder=2, alpha=0.85)
        ax.hlines(y=0, xmin=0, xmax=10, color="#1565c0", linewidth=4, zorder=2, alpha=0.85)
        ax.vlines(0, -0.3, 0.3, color=CHART_THEME_COLORS["text"], linewidth=1.0, zorder=3)

        db_avg_clamped = max(-10.0, min(10.0, float(database_average)))
        ax.scatter(
            [db_avg_clamped],
            [0],
            marker="|",
            s=260,
            linewidths=2.0,
            color="#f4d35e",
            zorder=4,
        )

        if loaded_charts > 0:
            selection_avg_clamped = max(-10.0, min(10.0, float(selection_average)))
            ax.scatter(
                [selection_avg_clamped],
                [0],
                marker="o",
                s=44,
                color="#6fa8dc",
                edgecolors=CHART_THEME_COLORS["text"],
                linewidths=0.8,
                zorder=5,
            )
            subtitle = (
                f"Selection Total: {selection_cumulative:+.1f} | "
                f"Selection Avg: {selection_average:+.2f} | "
                f"DB Avg: {database_average:+.2f}"
            )
        else:
            subtitle = f"DB Avg Alignment: {database_average:+.2f}"

        subtitle = textwrap.fill(
            subtitle,
            width=ALIGNMENT_CUMULATIVE_SUBTITLE_WRAP_WIDTH,
            break_long_words=False,
        )

        ax.text(
            0.5,
            -0.48,
            subtitle,
            ha="center",
            va="top",
            transform=ax.transAxes,
            color=CHART_THEME_COLORS["text"],
            fontsize=7.5,
            wrap=True,
            clip_on=False,
        )

        ax.set_xlim(-10.7, 10.7)
        ax.set_ylim(-0.45, 0.8)
        ax.set_yticks([])
        ax.set_xticks([-10, -5, 0, 5, 10])
        ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
        for spine in ax.spines.values():
            spine.set_visible(False)

        figure.subplots_adjust(left=0.08, right=0.98, top=0.94, bottom=0.34)
        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas

    @staticmethod
    def _minutes_to_label(total_minutes: float) -> str:
        minutes = int(round(total_minutes)) % (24 * 60)
        hours, mins = divmod(minutes, 60)
        return f"{hours:02d}:{mins:02d}"

    @staticmethod
    def _format_birthplace_comparison_line(
        *,
        label: str,
        selection_count: int,
        database_count: int,
        selection_total: int,
        database_total: int,
    ) -> str:
        safe_label = html.escape(str(label))
        if selection_total <= 0 or database_total <= 0:
            return f"• {safe_label} ({database_count} in DB)"

        selection_pct = (float(selection_count) / float(selection_total)) * 100.0
        database_pct = (float(database_count) / float(database_total)) * 100.0
        percent_delta = abs(selection_pct - database_pct)
        rounded_delta = int(round(percent_delta))

        if rounded_delta == 0:
            return (
                f'• {safe_label} ({selection_count}) | ({database_count} in DB) | '
                '<span style="color: #b8b8b8;">'
                "(selection % identical to DB)</span>"
            )

        if selection_pct > database_pct:
            return (
                f'• {safe_label} ({selection_count}) | ({database_count} in DB) | '
                f'<span style="color: lime;">{rounded_delta}% '
                "more common in selection than DB</span>"
            )

        return (
            f'• {safe_label} ({selection_count}) | ({database_count} in DB) | '
            f'<span style="color: red;">{rounded_delta}% '
            "less common in selection than DB</span>"
        )

    def _build_birthplace_comparison_text_widget(self, lines: list[str]) -> QLabel:
        widget = QLabel()
        widget.setTextFormat(Qt.RichText)
        widget.setWordWrap(True)
        widget.setStyleSheet("font-size: 11px; color: #f5f5f5;")
        widget.setText("<br>".join(lines))
        return widget

    @staticmethod
    def _split_tag_category(tag_value: str) -> tuple[str, str]:
        cleaned = str(tag_value or "").strip()
        if not cleaned:
            return "Uncategorized", ""
        if "." in cleaned:
            parts = [part.strip() for part in cleaned.split(".") if part.strip()]
            if len(parts) >= 2:
                category_key = parts[0].casefold()
                category_label = DatabaseAnalyticsChartsMixin.TAG_DISTRIBUTION_CATEGORY_ALIASES.get(
                    category_key,
                )
                if category_label is None:
                    return "Uncategorized", cleaned
                child_label = ".".join(parts[1:]).strip()
                return category_label, child_label
        return "Uncategorized", cleaned

    def _collect_tag_distribution_analytics(
        self,
        chart_ids: list[int] | set[int],
    ) -> dict[str, Any]:
        category_to_counts: dict[str, Counter[str]] = {}
        for chart_id in chart_ids:
            chart = self._get_chart_for_filter(int(chart_id))
            if chart is None:
                continue
            deduped_tags = normalize_tag_list(getattr(chart, "tags", []))
            for tag in deduped_tags:
                category, normalized_tag = self._split_tag_category(tag)
                if not normalized_tag:
                    continue
                category_counter = category_to_counts.setdefault(category, Counter())
                category_counter[normalized_tag] += 1
        return {
            "total_charts": len(chart_ids),
            "category_counts": {
                category: dict(counter)
                for category, counter in category_to_counts.items()
            },
        }

    def _render_tag_distribution_section(
        self,
        *,
        chart_ids: list[int],
        database_chart_ids: set[int],
        loaded_charts: int,
        should_refresh: Callable[[str], bool],
    ) -> list[tuple[str, float, float, float, int, int, float]]:
        selection_tag_analytics = self._collect_tag_distribution_analytics(chart_ids)
        database_tag_analytics = self._collect_tag_distribution_analytics(database_chart_ids)
        selection_tag_categories = selection_tag_analytics.get("category_counts", {})
        database_tag_categories = database_tag_analytics.get("category_counts", {})
        category_names = list(self.TAG_DISTRIBUTION_CATEGORY_ORDER)

        tag_dropdown = getattr(self, "_analysis_chart_dropdowns", {}).get("tag_distribution")
        if tag_dropdown is not None:
            options: list[tuple[str, str]] = [("All", "all")]
            options.extend((category, category) for category in category_names)
            selected_mode = getattr(self, "_tag_distribution_mode", "all")
            allowed_modes = {option_value for _option_label, option_value in options}
            if selected_mode not in allowed_modes:
                selected_mode = "all"
            tag_dropdown.blockSignals(True)
            tag_dropdown.clear()
            for option_label, option_value in options:
                tag_dropdown.addItem(option_label.upper(), option_value)
            selected_index = tag_dropdown.findData(selected_mode)
            if selected_index < 0 and tag_dropdown.count() > 0:
                selected_index = 0
            if selected_index >= 0:
                tag_dropdown.setCurrentIndex(selected_index)
                current_mode = tag_dropdown.currentData()
                if isinstance(current_mode, str):
                    self._tag_distribution_mode = current_mode
            tag_dropdown.blockSignals(False)

        selected_mode = getattr(self, "_tag_distribution_mode", "all")
        if selected_mode == "all":
            categories_to_render = category_names
        elif selected_mode in category_names:
            categories_to_render = [selected_mode]
        else:
            categories_to_render = []

        tag_export_rows: list[tuple[str, float, float, float, int, int, float]] = []
        if should_refresh("tag_distribution"):
            self._clear_layout(self.tag_distribution_chart_layout)
        for category_name in categories_to_render:
            selection_counts_raw = selection_tag_categories.get(category_name, {})
            database_counts_raw = database_tag_categories.get(category_name, {})
            source_counts = selection_counts_raw if loaded_charts else database_counts_raw
            filtered_tags = [tag for tag, count in source_counts.items() if int(count) > 1]
            filtered_tags.sort(
                key=lambda tag: (
                    -int(source_counts.get(tag, 0)),
                    tag.casefold(),
                )
            )
            if not filtered_tags:
                continue
            selection_counts = [int(selection_counts_raw.get(tag, 0)) for tag in filtered_tags]
            database_counts = [int(database_counts_raw.get(tag, 0)) for tag in filtered_tags]
            selection_total = max(1, int(selection_tag_analytics.get("total_charts", 0)))
            database_total = max(1, int(database_tag_analytics.get("total_charts", 0)))
            selection_values = [count / selection_total for count in selection_counts]
            database_values = [count / database_total for count in database_counts]
            significance_results = compute_proportion_significance_results(
                selection_counts=selection_counts,
                database_counts=database_counts,
                loaded_charts=loaded_charts,
                correction=getattr(self, "_significance_correction", "benjamini_hochberg"),
                selection_total=selection_total,
                database_total=database_total,
            )
            for tag_label, selection_value, database_value, selection_count, database_count, significance in zip(
                filtered_tags,
                selection_values,
                database_values,
                selection_counts,
                database_counts,
                significance_results,
            ):
                displayed_selection_value = selection_value if loaded_charts else database_value
                relative_percent = (
                    (displayed_selection_value / database_value)
                    if database_value > 0
                    else 0.0
                )
                tag_export_rows.append(
                    (
                        f"{category_name}: {tag_label}",
                        displayed_selection_value,
                        database_value,
                        displayed_selection_value - database_value,
                        selection_count if loaded_charts else database_count,
                        database_count,
                        relative_percent,
                        significance.standard_error,
                        significance.z_score,
                        significance.p_value,
                        significance.adjusted_p_value,
                        significance.band,
                        significance.model,
                    )
                )
            if should_refresh("tag_distribution"):
                tag_canvas = self._build_tag_distribution_chart(
                    category_label=category_name,
                    labels=filtered_tags,
                    selection_values=selection_values,
                    database_values=database_values,
                    selection_counts=selection_counts,
                    database_counts=database_counts,
                    loaded_charts=loaded_charts,
                )
                self.tag_distribution_chart_layout.addWidget(tag_canvas, 0)

        if should_refresh("tag_distribution") and not tag_export_rows:
            self.tag_distribution_chart_layout.addWidget(
                self._build_text_analysis_widget(["No repeated tags available for this scope."]),
                0,
                Qt.AlignTop,
            )
        return tag_export_rows

    def _create_tags_database_analytics_section(self, panel: Any, layout: QVBoxLayout) -> None:
        """Create the un-nested Tags section at the bottom of Database Analytics."""
        tag_distribution_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "🏷️Tags",
            section_key="tag_distribution",
            expanded=self._is_database_metrics_section_expanded("tag_distribution"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "tag_distribution",
                checked,
            ),
        )
        self._database_metrics_section_expanded["tag_distribution"] = self._is_database_metrics_section_expanded("tag_distribution")
        self._create_analysis_chart_header(
            tag_distribution_section_layout,
            "🏷️Tags",
            "tag_distribution",
            "tag_distribution",
            dropdown_options=[("All", "all")],
            show_title=False,
        )
        tag_subheader = self._build_database_subheader_label(
            "Repeated tags by category. With selection, rows show selection % relative to DB %."
        )
        tag_distribution_section_layout.addWidget(tag_subheader)
        (
            self.tag_distribution_chart_container,
            self.tag_distribution_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["tag_distribution"] = self.tag_distribution_chart_layout
        tag_distribution_section_layout.addWidget(self.tag_distribution_chart_container)

    def _create_traits_database_analytics_section(self, panel: Any, layout: Any) -> None:
        traits_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "🧬Traits",
            section_key="traits_distribution",
            expanded=self._is_database_metrics_section_expanded("traits_distribution"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "traits_distribution",
                checked,
            ),
        )
        self._database_metrics_section_expanded["traits_distribution"] = self._is_database_metrics_section_expanded("traits_distribution")
        self._create_analysis_chart_header(
            traits_section_layout,
            "🧬Traits",
            "traits_distribution",
            "traits_distribution",
            dropdown_options=[("Trait Predictions", "trait_predictions"), ("Trait Rankings", "trait_rankings")],
            show_title=False,
        )
        self.traits_distribution_subheader_label = self._build_database_subheader_label(
            "Average active custom trait likelihoods across the database. With selection, bars compare selection average to DB average."
        )
        traits_section_layout.addWidget(self.traits_distribution_subheader_label)

        self.traits_distribution_rank_container = QWidget()
        trait_rank_container_layout = QVBoxLayout()
        trait_rank_container_layout.setContentsMargins(0, 0, 0, 0)
        trait_rank_container_layout.setSpacing(0)
        self.traits_distribution_rank_container.setLayout(trait_rank_container_layout)

        trait_rank_row = QWidget()
        trait_rank_layout = QHBoxLayout()
        trait_rank_layout.setContentsMargins(0, 0, 0, 0)
        trait_rank_layout.setSpacing(6)
        trait_rank_row.setLayout(trait_rank_layout)
        trait_rank_label = QLabel("Top charts for trait:")
        trait_rank_label.setStyleSheet("color: #cfcfcf; font-size: 8pt;")
        trait_rank_layout.addWidget(trait_rank_label)
        self.traits_distribution_rank_combo = QComboBox()
        self.traits_distribution_rank_combo.setMinimumContentsLength(22)
        self.traits_distribution_rank_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.traits_distribution_rank_combo.currentIndexChanged.connect(
            lambda _index: self._on_traits_distribution_rank_trait_changed()
        )
        trait_rank_layout.addWidget(self.traits_distribution_rank_combo, 1)
        trait_rank_container_layout.addWidget(trait_rank_row)

        self.traits_distribution_rank_label = QLabel("")
        self.traits_distribution_rank_label.setTextFormat(Qt.RichText)
        self.traits_distribution_rank_label.setWordWrap(True)
        self.traits_distribution_rank_label.setStyleSheet("color: #d8d8d8; padding: 2px 0 6px 0;")
        trait_rank_container_layout.addWidget(self.traits_distribution_rank_label)
        traits_section_layout.addWidget(self.traits_distribution_rank_container)

        (
            self.traits_distribution_chart_container,
            self.traits_distribution_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["traits_distribution"] = self.traits_distribution_chart_layout
        traits_section_layout.addWidget(self.traits_distribution_chart_container)
        self._sync_traits_distribution_display_mode()


    def _traits_distribution_display_mode(self) -> str:
        dropdown = getattr(self, "_analysis_chart_dropdowns", {}).get("traits_distribution")
        if dropdown is not None:
            selected_mode = dropdown.currentData()
            if isinstance(selected_mode, str) and selected_mode in {"trait_predictions", "trait_rankings"}:
                return selected_mode
        selected_mode = str(getattr(self, "_traits_distribution_mode", "trait_predictions") or "trait_predictions")
        return selected_mode if selected_mode in {"trait_predictions", "trait_rankings"} else "trait_predictions"

    def _sync_traits_distribution_display_mode(self) -> None:
        show_rankings = self._traits_distribution_display_mode() == "trait_rankings"
        rank_container = getattr(self, "traits_distribution_rank_container", None)
        if rank_container is not None:
            rank_container.setVisible(show_rankings)
        subheader = getattr(self, "traits_distribution_subheader_label", None)
        if subheader is not None:
            subheader.setVisible(not show_rankings)
        chart_container = getattr(self, "traits_distribution_chart_container", None)
        if chart_container is not None:
            chart_container.setVisible(not show_rankings)

    def _refresh_traits_distribution_rankings_from_cached_context(self) -> None:
        context = getattr(self, "_traits_distribution_rank_context", None)
        rank_label = getattr(self, "traits_distribution_rank_label", None)
        if not isinstance(context, dict) or not isinstance(rank_label, QLabel):
            return
        rankings = self._traits_distribution_chart_rankings(
            chart_ids=context.get("chart_ids", ()),
            trait_signature=context.get("trait_signature", ()),
            selected_trait_name=str(context.get("selected_trait_name", "") or ""),
            database_values=context.get("database_values", {}),
        )
        self._traits_distribution_current_ranked_chart_ids = {
            int(row["chart_id"])
            for row in rankings
            if isinstance(row, dict) and "chart_id" in row
        }
        rank_label.setText(
            self._render_traits_distribution_rankings_html(
                context.get("selected_trait_name"),
                rankings,
                scope_label=str(context.get("scope_label", "the database")),
                cache_warmed=bool(context.get("cache_warmed", False)),
            )
        )

    def _refresh_traits_distribution_rankings_after_hidden_chart_change(self, hidden_chart_ids: set[int]) -> None:
        current_ranked_ids = getattr(self, "_traits_distribution_current_ranked_chart_ids", set())
        if not hidden_chart_ids or not current_ranked_ids or not (set(hidden_chart_ids) & set(current_ranked_ids)):
            return
        self._refresh_traits_distribution_rankings_from_cached_context()

    def _on_traits_distribution_rank_trait_changed(self) -> None:
        combo = getattr(self, "traits_distribution_rank_combo", None)
        if not isinstance(combo, QComboBox):
            return
        selected_name = combo.currentData()
        if isinstance(selected_name, str):
            self._traits_distribution_rank_trait_name = selected_name
        if getattr(self, "_traits_distribution_rank_refresh_pending", False):
            return
        self._traits_distribution_rank_refresh_pending = True

        def _refresh() -> None:
            self._traits_distribution_rank_refresh_pending = False
            update = getattr(self, "_update_sentiment_tally", None)
            if callable(update):
                update(
                    update_database_metrics=True,
                    update_similarities=False,
                    sections_to_refresh={"traits_distribution"},
                )

        QTimer.singleShot(0, _refresh)

    def _sync_traits_distribution_rank_combo(self, trait_items: list[dict[str, Any]]) -> str | None:
        combo = getattr(self, "traits_distribution_rank_combo", None)
        if not isinstance(combo, QComboBox):
            return None
        active_traits = [
            trait for trait in trait_items
            if str(trait.get("name", "")).strip() and not bool(trait.get("archived", False))
        ]
        current_name = str(getattr(self, "_traits_distribution_rank_trait_name", "") or "")
        combo.blockSignals(True)
        try:
            combo.clear()
            if not active_traits:
                combo.addItem("No active traits", "")
                combo.setEnabled(False)
                self._traits_distribution_rank_trait_name = ""
                return None
            combo.setEnabled(True)
            for trait in active_traits:
                name = str(trait.get("name", "")).strip()
                combo.addItem(name, name)
            selected_index = combo.findData(current_name)
            if selected_index < 0:
                selected_index = 0
            combo.setCurrentIndex(selected_index)
            selected_name = combo.currentData()
            if isinstance(selected_name, str) and selected_name:
                self._traits_distribution_rank_trait_name = selected_name
                return selected_name
            return None
        finally:
            combo.blockSignals(False)

    def _traits_distribution_chart_rankings(
        self,
        *,
        chart_ids: list[int] | set[int],
        trait_signature: tuple[tuple[str, str, str], ...],
        selected_trait_name: str,
        database_values: Mapping[str, float],
    ) -> list[dict[str, Any]]:
        """Return cached top chart matches for a trait without a second all-traits pass."""
        if not selected_trait_name:
            return []
        normalized_chart_ids = tuple(sorted({int(chart_id) for chart_id in chart_ids}))
        cache_revision = int(getattr(self, "_database_metrics_cache_revision", 0))
        likelihood_cache = getattr(self, "_traits_distribution_chart_likelihood_cache", None)
        if not isinstance(likelihood_cache, dict):
            return []
        rows: list[dict[str, Any]] = []
        hidden_chart_ids = {int(chart_id) for chart_id in getattr(self, "_hidden_chart_ids", set())}
        db_average_pct = float(database_values.get(selected_trait_name, 0.0)) * 100.0
        for chart_id in normalized_chart_ids:
            if int(chart_id) in hidden_chart_ids:
                continue
            chart = self._get_chart_for_filter(int(chart_id))
            if chart is None or self._is_placeholder_chart(chart):
                continue
            chart_cache_key = (cache_revision, trait_signature, int(chart_id))
            likelihoods = likelihood_cache.get(chart_cache_key)
            if likelihoods is None:
                # The aggregate collector should have warmed this cache already.
                # Skip instead of doing surprise UI-thread work during dropdown use.
                continue
            try:
                likelihood = float(likelihoods.get(selected_trait_name, 0.0))
            except (TypeError, ValueError):
                continue
            chart_name = str(getattr(chart, "name", "") or f"Chart {chart_id}").strip()
            rows.append(
                {
                    "chart_id": int(chart_id),
                    "name": chart_name or f"Chart {chart_id}",
                    "likelihood": likelihood,
                    "deviation": likelihood - db_average_pct,
                }
            )
        rows.sort(key=lambda row: (-float(row["likelihood"]), -float(row["deviation"]), str(row["name"]).casefold()))
        return rows[:10]

    @staticmethod
    def _render_traits_distribution_rankings_html(
        selected_trait_name: str | None,
        rankings: list[dict[str, Any]],
        *,
        scope_label: str,
        cache_warmed: bool,
    ) -> str:
        if not selected_trait_name:
            return "<span style='color:#9a9a9a;'>No active trait selected for top-chart ranking.</span>"
        safe_trait = html.escape(selected_trait_name)
        safe_scope = html.escape(scope_label)
        if not rankings:
            if not cache_warmed:
                return (
                    f"<span style='color:#9a9a9a;'>Top chart matches for <b>{safe_trait}</b> "
                    "will appear after trait scores finish warming.</span>"
                )
            return (
                f"<span style='color:#9a9a9a;'>No non-placeholder charts are currently available "
                f"to rank for <b>{safe_trait}</b>.</span>"
            )
        rows = []
        for rank, row in enumerate(rankings, start=1):
            name = html.escape(str(row.get("name", "")))
            likelihood = float(row.get("likelihood", 0.0))
            deviation = float(row.get("deviation", 0.0))
            deviation_color = "#90ee90" if deviation >= 0 else "#ffb3b3"
            rows.append(
                "<tr>"
                f"<td style='padding:1px 8px 1px 0; color:#9a9a9a; text-align:right;'>{rank}</td>"
                f"<td style='padding:1px 8px 1px 0; color:#f0f0f0;'>{name}</td>"
                f"<td style='padding:1px 8px 1px 0; color:#d8d8d8; text-align:right;'>{likelihood:.1f}%</td>"
                f"<td style='padding:1px 0; color:{deviation_color}; text-align:right;'>{deviation:+.1f}</td>"
                "</tr>"
            )
        return (
            f"<div style='padding-bottom:3px;'>Top 10 <b>{safe_trait}</b> chart matches in {safe_scope}.</div>"
            "<table cellspacing='0' cellpadding='0' style='width:100%;'>"
            "<tr>"
            "<th style='padding:1px 8px 2px 0; color:#f5f5f5; text-align:right;'>#</th>"
            "<th style='padding:1px 8px 2px 0; color:#f5f5f5; text-align:left;'>chart</th>"
            "<th style='padding:1px 8px 2px 0; color:#f5f5f5; text-align:right;'>match</th>"
            "<th style='padding:1px 0 2px 0; color:#f5f5f5; text-align:right;'>vs DB</th>"
            "</tr>"
            f"{''.join(rows)}"
            "</table>"
            "<div style='color:#9a9a9a; padding-top:3px;'>"
            "Ranking reuses warmed trait-score cache so dropdown changes do not launch another full scoring pass."
            "</div>"
        )

    @staticmethod
    def _traits_distribution_signature(trait_items: list[dict[str, Any]]) -> tuple[tuple[str, str, str], ...]:
        return tuple(
            (
                str(item.get("name", "")).strip(),
                normalize_trait_color(str(item.get("color", DEFAULT_TRAIT_COLOR))),
                repr(item.get("profile", {})),
            )
            for item in trait_items
            if str(item.get("name", "")).strip() and not bool(item.get("archived", False))
        )

    @staticmethod
    def _stable_traits_metadata_hash(value: Any) -> str:
        try:
            payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
        except TypeError:
            payload = repr(value)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _chart_trait_metadata_signature(self, chart: Any) -> str:
        try:
            uses_houses = bool(chart_uses_houses(chart))
        except Exception:
            uses_houses = bool(getattr(chart, "use_birth_time_data", False))
        return self._stable_traits_metadata_hash(
            {
                "birth_date": getattr(chart, "birth_date", None),
                "birth_time": getattr(chart, "birth_time", None),
                "birth_place": getattr(chart, "birth_place", None),
                "datetime": getattr(chart, "datetime", None),
                "datetime_iso": getattr(chart, "datetime_iso", None),
                "lat": getattr(chart, "lat", None),
                "lon": getattr(chart, "lon", None),
                "birthtime_unknown": bool(getattr(chart, "birthtime_unknown", False)),
                "retcon_time_used": bool(getattr(chart, "retcon_time_used", False)),
                "retcon_hour": getattr(chart, "retcon_hour", None),
                "retcon_minute": getattr(chart, "retcon_minute", None),
                "chart_uses_houses": uses_houses,
            }
        )

    def _persist_traits_distribution_metadata(
        self,
        *,
        normalized_chart_ids: tuple[int, ...],
        trait_items: list[dict[str, Any]],
        trait_names: list[str],
        chart_likelihoods: dict[int, dict[str, float]],
        database_averages_pct: dict[str, float],
    ) -> None:
        """Passively backfill UID-keyed trait metadata from warmed analytics scores."""
        if not normalized_chart_ids or not trait_names or not chart_likelihoods:
            return
        trait_signature_hash = self._stable_traits_metadata_hash(
            {
                "version": 1,
                "traits": [
                    {
                        "name": trait.get("name", ""),
                        "color": normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR))),
                        "profile": trait.get("profile", {}),
                    }
                    for trait in trait_items
                    if str(trait.get("name", "")).strip() and not bool(trait.get("archived", False))
                ],
            }
        )
        norm_signature = self._stable_traits_metadata_hash(normalized_chart_ids)
        threshold = TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD
        for chart_id, likelihoods in chart_likelihoods.items():
            chart = self._get_chart_for_filter(int(chart_id))
            chart_uid = str(getattr(chart, "chart_uid", "") or "").strip()
            if not chart_uid:
                continue
            rows: list[dict[str, Any]] = []
            for name in trait_names:
                if name not in database_averages_pct:
                    continue
                likelihood = float(likelihoods.get(name, 0.0))
                db_average = float(database_averages_pct.get(name, 0.0))
                deviation = likelihood - db_average
                rows.append(
                    {
                        "trait_name": name,
                        "direction": "above" if deviation >= threshold else "below" if deviation <= -threshold else "neutral",
                        "likelihood": likelihood,
                        "db_average": db_average,
                        "deviation": deviation,
                    }
                )
            if not rows:
                continue
            try:
                db.upsert_chart_trait_metadata(
                    chart_uid,
                    rows,
                    trait_signature=trait_signature_hash,
                    norm_signature=norm_signature,
                    chart_signature=self._chart_trait_metadata_signature(chart),
                )
            except Exception:
                logger.exception("Failed to passively persist trait metadata for chart UID %s.", chart_uid)

    def _clear_traits_distribution_analytics_cache(self, changed_chart_ids: set[int] | None = None) -> None:
        self._traits_distribution_analytics_cache = {}
        if changed_chart_ids is None:
            self._traits_distribution_chart_likelihood_cache = {}
            return

        likelihood_cache = getattr(self, "_traits_distribution_chart_likelihood_cache", None)
        if not isinstance(likelihood_cache, dict):
            self._traits_distribution_chart_likelihood_cache = {}
            return

        changed_ids = {int(chart_id) for chart_id in changed_chart_ids}
        for cache_key in list(likelihood_cache):
            if (
                isinstance(cache_key, tuple)
                and len(cache_key) >= 3
                and isinstance(cache_key[2], int)
                and cache_key[2] in changed_ids
            ):
                likelihood_cache.pop(cache_key, None)


    def _traits_distribution_chart_tokens(self) -> dict[int, str]:
        """Return stable per-chart row fingerprints for persisted trait-score reuse."""
        cached_tokens = getattr(self, "_traits_distribution_chart_token_cache", None)
        if isinstance(cached_tokens, dict):
            return dict(cached_tokens)
        normalize_row = getattr(self, "_normalize_chart_row", None)
        encode_value = getattr(self, "_encode_database_metrics_cache_value", None)
        tokens: dict[int, str] = {}
        for row in getattr(self, "_chart_rows", []) or []:
            normalized = normalize_row(row) if callable(normalize_row) else row
            if normalized is None:
                continue
            try:
                chart_id = int(normalized[0])
            except (TypeError, ValueError, IndexError):
                continue
            encoded = encode_value(normalized) if callable(encode_value) else normalized
            try:
                payload = json.dumps(encoded, sort_keys=True, default=str, separators=(",", ":"))
            except TypeError:
                payload = repr(encoded)
            tokens[chart_id] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self._traits_distribution_chart_token_cache = dict(tokens)
        return tokens

    def _traits_distribution_likelihood_cache_path(self):
        from ephemeraldaddy.core.db import DB_DIR

        return DB_DIR / TRAITS_DISTRIBUTION_LIKELIHOOD_CACHE_FILENAME

    def _load_traits_distribution_likelihood_cache(self) -> bool:
        if getattr(self, "_traits_distribution_likelihood_cache_loaded", False):
            return True
        self._traits_distribution_likelihood_cache_loaded = True
        path = self._traits_distribution_likelihood_cache_path()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return False
        except Exception:
            logger.exception("Failed to load traits distribution likelihood cache from %s.", path)
            return False
        if not isinstance(payload, dict):
            return False
        if payload.get("version") != TRAITS_DISTRIBUTION_LIKELIHOOD_CACHE_VERSION:
            return False
        entries = payload.get("entries", [])
        if not isinstance(entries, list):
            return False
        cache_revision = int(getattr(self, "_database_metrics_cache_revision", 0))
        chart_tokens = self._traits_distribution_chart_tokens()
        likelihood_cache: dict[tuple[Any, ...], dict[str, float]] = {}
        individual_cache: dict[tuple[tuple[str, str, str], int], float] = {}
        skipped_entries = 0
        for entry in entries:
            if not isinstance(entry, dict):
                skipped_entries += 1
                continue
            try:
                chart_id = int(entry.get("chart_id"))
            except (TypeError, ValueError):
                skipped_entries += 1
                continue
            saved_chart_token = str(entry.get("chart_token", "") or "")
            current_chart_token = chart_tokens.get(chart_id)
            if current_chart_token and saved_chart_token and saved_chart_token != current_chart_token:
                skipped_entries += 1
                continue
            signature = entry.get("trait_signature")
            likelihoods = entry.get("likelihoods")
            if not isinstance(signature, list) or not isinstance(likelihoods, dict):
                skipped_entries += 1
                continue
            trait_signature = tuple(
                (str(item[0]), str(item[1]), str(item[2]))
                for item in signature
                if isinstance(item, (list, tuple)) and len(item) == 3
            )
            if not trait_signature:
                skipped_entries += 1
                continue
            normalized_likelihoods: dict[str, float] = {}
            trait_keys_by_name = {name: (name, color, profile) for name, color, profile in trait_signature}
            for name, value in likelihoods.items():
                if not isinstance(name, str):
                    continue
                try:
                    likelihood = float(value)
                except (TypeError, ValueError):
                    skipped_entries += 1
                    continue
                normalized_likelihoods[str(name)] = likelihood
                trait_key = trait_keys_by_name.get(str(name))
                if trait_key is not None:
                    individual_cache[(trait_key, chart_id)] = likelihood
            if not normalized_likelihoods:
                skipped_entries += 1
                continue
            likelihood_cache[(cache_revision, trait_signature, chart_id)] = normalized_likelihoods
        if not likelihood_cache and not individual_cache:
            return False
        if skipped_entries:
            logger.info(
                "Skipped %s invalid or stale entr%s while loading traits distribution likelihood cache.",
                skipped_entries,
                "y" if skipped_entries == 1 else "ies",
            )
        self._traits_distribution_chart_likelihood_cache = likelihood_cache
        self._traits_distribution_individual_likelihood_cache = individual_cache
        self._traits_distribution_likelihood_cache_dirty = False
        return True

    def _save_traits_distribution_likelihood_cache(self) -> None:
        likelihood_cache = getattr(self, "_traits_distribution_chart_likelihood_cache", None)
        if not isinstance(likelihood_cache, dict) or not likelihood_cache:
            return
        entries: list[dict[str, Any]] = []
        current_revision = int(getattr(self, "_database_metrics_cache_revision", 0))
        chart_tokens = self._traits_distribution_chart_tokens()
        for cache_key, likelihoods in likelihood_cache.items():
            if (
                not isinstance(cache_key, tuple)
                or len(cache_key) != 3
                or cache_key[0] != current_revision
                or not isinstance(cache_key[1], tuple)
                or not isinstance(likelihoods, dict)
            ):
                continue
            try:
                chart_id = int(cache_key[2])
                normalized_likelihoods = {str(name): float(value) for name, value in likelihoods.items()}
            except (TypeError, ValueError):
                continue
            entries.append(
                {
                    "trait_signature": [list(item) for item in cache_key[1]],
                    "chart_id": chart_id,
                    "chart_token": chart_tokens.get(chart_id, ""),
                    "likelihoods": normalized_likelihoods,
                }
            )
            if len(entries) >= TRAITS_DISTRIBUTION_LIKELIHOOD_CACHE_MAX_ENTRIES:
                break
        if not entries:
            return
        try:
            path = self._traits_distribution_likelihood_cache_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            payload: dict[str, Any] = {
                "version": TRAITS_DISTRIBUTION_LIKELIHOOD_CACHE_VERSION,
                "entries": entries,
            }
            if len(likelihood_cache) > len(entries):
                payload["truncated"] = True
                payload["max_entries"] = TRAITS_DISTRIBUTION_LIKELIHOOD_CACHE_MAX_ENTRIES
            temp_path = path.with_suffix(f"{path.suffix}.tmp")
            temp_path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
            temp_path.replace(path)
            self._traits_distribution_likelihood_cache_dirty = False
        except Exception:
            logger.exception("Failed to save traits distribution likelihood cache.")

    def _collect_traits_distribution_analytics(
        self,
        chart_ids: list[int] | set[int],
        trait_items: list[dict[str, Any]] | None = None,
        trait_signature: tuple[tuple[str, str, str], ...] | None = None,
        time_budget_seconds: float | None = TRAITS_DISTRIBUTION_SCORING_TIME_BUDGET_SECONDS,
    ) -> dict[str, Any]:
        trait_items = trait_items if trait_items is not None else list_traits(active_only=True)
        trait_signature = (
            trait_signature
            if trait_signature is not None
            else self._traits_distribution_signature(trait_items)
        )
        normalized_chart_ids = tuple(sorted({int(chart_id) for chart_id in chart_ids}))
        aggregate_cache = getattr(self, "_traits_distribution_analytics_cache", None)
        if not isinstance(aggregate_cache, dict):
            aggregate_cache = {}
            self._traits_distribution_analytics_cache = aggregate_cache
        cache_revision = int(getattr(self, "_database_metrics_cache_revision", 0))
        aggregate_cache_key = (cache_revision, trait_signature, normalized_chart_ids)
        cached = aggregate_cache.get(aggregate_cache_key)
        if isinstance(cached, dict):
            return copy.deepcopy(cached)

        trait_names = [name for name, _color, _profile in trait_signature]
        totals: dict[str, float] = {name: 0.0 for name in trait_names}
        colors = {name: color for name, color, _profile in trait_signature}
        possible_scores = {
            str(item.get("name", "")): max(float(trait_possible_score(item.get("profile", {}))), 1.0)
            for item in trait_items
            if str(item.get("name", "")).strip() and not bool(item.get("archived", False))
        }
        chart_count = 0
        likelihood_cache = getattr(self, "_traits_distribution_chart_likelihood_cache", None)
        if not isinstance(likelihood_cache, dict):
            self._load_traits_distribution_likelihood_cache()
            likelihood_cache = getattr(self, "_traits_distribution_chart_likelihood_cache", None)
        if not isinstance(likelihood_cache, dict):
            likelihood_cache = {}
            self._traits_distribution_chart_likelihood_cache = likelihood_cache
        individual_cache = getattr(self, "_traits_distribution_individual_likelihood_cache", None)
        if not isinstance(individual_cache, dict):
            individual_cache = {}
            self._traits_distribution_individual_likelihood_cache = individual_cache
        trait_items_by_key = {
            (
                str(item.get("name", "")).strip(),
                normalize_trait_color(str(item.get("color", DEFAULT_TRAIT_COLOR))),
                repr(item.get("profile", {})),
            ): item
            for item in trait_items
            if str(item.get("name", "")).strip() and not bool(item.get("archived", False))
        }

        cache_updated = False
        partial = False
        chart_likelihoods_for_metadata: dict[int, dict[str, float]] = {}
        uncached_started_at = time.monotonic()
        for chart_id in normalized_chart_ids:
            chart = self._get_chart_for_filter(int(chart_id))
            if chart is None or self._is_placeholder_chart(chart):
                continue
            chart_cache_key = (cache_revision, trait_signature, int(chart_id))
            likelihoods = likelihood_cache.get(chart_cache_key)
            if likelihoods is None:
                likelihoods = {}
                missing_trait_items: list[dict[str, Any]] = []
                for trait_key in trait_signature:
                    cached_likelihood = individual_cache.get((trait_key, int(chart_id)))
                    if cached_likelihood is None:
                        trait_item = trait_items_by_key.get(trait_key)
                        if trait_item is not None:
                            missing_trait_items.append(trait_item)
                        continue
                    likelihoods[trait_key[0]] = float(cached_likelihood)
                if missing_trait_items:
                    if (
                        time_budget_seconds is not None
                        and time_budget_seconds >= 0
                        and cache_updated
                        and (time.monotonic() - uncached_started_at) >= float(time_budget_seconds)
                    ):
                        partial = True
                        break
                    try:
                        missing_likelihoods = calculate_trait_likelihoods(
                            chart,
                            missing_trait_items,
                            possible_scores=possible_scores,
                        )
                    except Exception:
                        logger.exception(
                            "Trait likelihood calculation failed for chart %s during database analytics refresh.",
                            self._debug_chart_label(chart),
                        )
                        continue
                    likelihoods.update(missing_likelihoods)
                    for trait_key in trait_signature:
                        name = trait_key[0]
                        if name in missing_likelihoods:
                            individual_cache[(trait_key, int(chart_id))] = float(missing_likelihoods[name])
                    cache_updated = True
                if len(likelihoods) >= len(trait_names):
                    likelihood_cache[chart_cache_key] = dict(likelihoods)
            if len(likelihoods) >= len(trait_names):
                chart_likelihoods_for_metadata[int(chart_id)] = dict(likelihoods)
            chart_count += 1
            for name in trait_names:
                try:
                    totals[name] += float(likelihoods.get(name, 0.0)) / 100.0
                except (TypeError, ValueError):
                    continue
        result = {
            "trait_names": trait_names,
            "totals": totals,
            "chart_count": chart_count,
            "colors": colors,
            "partial": partial,
            "requested_chart_count": len(normalized_chart_ids),
        }
        if not partial:
            aggregate_cache[aggregate_cache_key] = copy.deepcopy(result)
            if chart_count:
                self._persist_traits_distribution_metadata(
                    normalized_chart_ids=normalized_chart_ids,
                    trait_items=trait_items,
                    trait_names=trait_names,
                    chart_likelihoods=chart_likelihoods_for_metadata,
                    database_averages_pct={
                        name: (float(total) / float(chart_count)) * 100.0
                        for name, total in totals.items()
                    },
                )
        if cache_updated:
            self._traits_distribution_likelihood_cache_dirty = True
            self._save_traits_distribution_likelihood_cache()
        return result

    def _render_traits_distribution_section(
        self,
        *,
        chart_ids: list[int],
        database_chart_ids: set[int],
        loaded_charts: int,
        should_refresh: Callable[[str], bool],
    ) -> None:
        if not should_refresh("traits_distribution"):
            return

        trait_items = list_traits(active_only=True)
        trait_signature = self._traits_distribution_signature(trait_items)
        selected_trait_name = self._sync_traits_distribution_rank_combo(trait_items)
        database_analytics = self._collect_traits_distribution_analytics(
            database_chart_ids,
            trait_items=trait_items,
            trait_signature=trait_signature,
        )
        if set(chart_ids) == set(database_chart_ids):
            selection_analytics = copy.deepcopy(database_analytics)
        else:
            selection_analytics = self._collect_traits_distribution_analytics(
                chart_ids,
                trait_items=trait_items,
                trait_signature=trait_signature,
            )
        trait_names = list(database_analytics.get("trait_names", []))
        if not trait_names:
            trait_names = list(selection_analytics.get("trait_names", []))
        selection_count = max(0, int(selection_analytics.get("chart_count", 0)))
        database_count = max(0, int(database_analytics.get("chart_count", 0)))
        selection_totals = selection_analytics.get("totals", {})
        database_totals = database_analytics.get("totals", {})
        selection_values = {
            name: (float(selection_totals.get(name, 0.0)) / float(selection_count) if selection_count else 0.0)
            for name in trait_names
        }
        database_values = {
            name: (float(database_totals.get(name, 0.0)) / float(database_count) if database_count else 0.0)
            for name in trait_names
        }
        ranking_scope_ids: list[int] | set[int] = chart_ids if loaded_charts > 0 else database_chart_ids
        ranking_scope_label = "the current selection" if loaded_charts > 0 else "the database"
        rank_label = getattr(self, "traits_distribution_rank_label", None)
        self._traits_distribution_rank_context = {
            "chart_ids": tuple(sorted({int(chart_id) for chart_id in ranking_scope_ids})),
            "trait_signature": trait_signature,
            "selected_trait_name": selected_trait_name or "",
            "database_values": dict(database_values),
            "scope_label": ranking_scope_label,
            "cache_warmed": database_count > 0 and not bool(database_analytics.get("partial", False)),
        }
        if isinstance(rank_label, QLabel):
            rankings = self._traits_distribution_chart_rankings(
                chart_ids=ranking_scope_ids,
                trait_signature=trait_signature,
                selected_trait_name=selected_trait_name or "",
                database_values=database_values,
            )
            self._traits_distribution_current_ranked_chart_ids = {int(row["chart_id"]) for row in rankings}
            rank_label.setText(
                self._render_traits_distribution_rankings_html(
                    selected_trait_name,
                    rankings,
                    scope_label=ranking_scope_label,
                    cache_warmed=database_count > 0 and not bool(database_analytics.get("partial", False)),
                )
            )
        self._sync_traits_distribution_display_mode()
        ordered_labels = sorted(
            trait_names,
            key=lambda name: (
                -(selection_values.get(name, 0.0) if loaded_charts else database_values.get(name, 0.0)),
                name.casefold(),
            ),
        )
        database_partial = bool(database_analytics.get("partial", False))
        requested_database_count = int(database_analytics.get("requested_chart_count", database_count) or database_count)
        if loaded_charts > 0:
            if database_partial:
                self.traits_distribution_subheader_label.setText(
                    "Active custom trait likelihood averages for selected chart(s) relative to a still-warming database average "
                    f"({database_count:,}/{requested_database_count:,} charts scored so far)."
                )
            else:
                self.traits_distribution_subheader_label.setText(
                    "Active custom trait likelihood averages for selected chart(s) relative to database average."
                )
        else:
            if database_partial:
                self.traits_distribution_subheader_label.setText(
                    "Average active custom trait likelihoods across a time-bounded sample while the cache warms "
                    f"({database_count:,}/{requested_database_count:,} non-placeholder database charts scored so far)."
                )
            else:
                self.traits_distribution_subheader_label.setText(
                    f"Average active custom trait likelihoods across {database_count:,} non-placeholder database charts."
                )
        self._clear_layout(self.traits_distribution_chart_layout)
        if ordered_labels and database_count > 0:
            color_lookup = dict(database_analytics.get("colors", {}))
            color_lookup.update(selection_analytics.get("colors", {}))
            canvas = self._build_dominant_planet_chart(
                selection_planets={name: selection_values.get(name, 0.0) for name in ordered_labels},
                database_planets={name: database_values.get(name, 0.0) for name in ordered_labels},
                selection_planet_counts={name: selection_count for name in ordered_labels},
                database_planet_counts={name: database_count for name in ordered_labels},
                loaded_charts=loaded_charts,
                labels=ordered_labels,
                force_value_fallback_colors=False,
                label_colors={name: color_lookup.get(name, DEFAULT_TRAIT_COLOR) for name in ordered_labels},
                include_count_prefixes=False,
                auto_height=True,
            )
            self.traits_distribution_chart_layout.addWidget(canvas, 0)
        else:
            self.traits_distribution_chart_layout.addWidget(
                self._build_text_analysis_widget(["No active traits available. Add or reactivate traits in Settings > Traits."]),
                0,
                Qt.AlignTop,
            )
        self._analysis_chart_export_rows["traits_distribution"] = self._build_analysis_export_rows(
            labels=ordered_labels,
            selection_values=[selection_values.get(label, 0.0) for label in ordered_labels],
            database_values=[database_values.get(label, 0.0) for label in ordered_labels],
            selection_counts=[selection_count for _label in ordered_labels],
            database_counts=[database_count for _label in ordered_labels],
            loaded_charts=loaded_charts,
        )

    @staticmethod
    def _extract_birthplace_components(raw_place: str) -> tuple[str | None, str | None, str | None]:
        parts = [part.strip() for part in (raw_place or "").split(",") if part.strip()]
        if not parts:
            return None, None, None
        city = parts[0] if parts else None
        state = parts[-2] if len(parts) >= 2 else None
        country = parts[-1] if len(parts) >= 2 else None
        if len(parts) == 1:
            country = None
            state = None
        return city, state, country

    @staticmethod
    def _bucket_age_value(age_value: int) -> str | None:
        for label, min_age, max_age in AGE_BRACKETS:
            if min_age is None:
                continue
            if age_value < min_age:
                continue
            if max_age is None or age_value < max_age:
                return label
        return None

    def _collect_age_analytics(self, chart_ids: list[int] | set[int]) -> dict[str, Any]:
        now_year = datetime.datetime.now(datetime.timezone.utc).year
        age_counts: Counter[int] = Counter()
        known_duration_counts: Counter[int] = Counter()
        age_bracket_counts: Counter[str] = Counter()
        generation_counts: Counter[str] = Counter()

        for chart_id in chart_ids:
            chart = self._get_chart_for_filter(int(chart_id))
            if chart is None:
                continue
            if self._is_placeholder_chart(chart):
                continue

            birth_year_value = getattr(chart, "birth_year", None)
            if not isinstance(birth_year_value, int):
                dt_value = getattr(chart, "dt", None)
                if isinstance(dt_value, datetime.datetime):
                    birth_year_value = int(dt_value.year)
            if isinstance(birth_year_value, int):
                age_value = int(math.floor(now_year - int(birth_year_value)))
                if age_value >= 0:
                    age_counts[age_value] += 1
                    age_bracket = self._bucket_age_value(age_value)
                    if age_bracket is not None:
                        age_bracket_counts[age_bracket] += 1
                generation_name = self._generation_for_birth_year(int(birth_year_value))
                if generation_name is not None:
                    generation_counts[generation_name] += 1

            year_first_encountered = getattr(chart, "year_first_encountered", None)
            if isinstance(year_first_encountered, int):
                known_duration = now_year - int(year_first_encountered)
                if known_duration >= 0:
                    known_duration_counts[known_duration] += 1

        return {
            "age_counts": dict(age_counts),
            "age_bracket_counts": dict(age_bracket_counts),
            "known_duration_counts": dict(known_duration_counts),
            "generation_counts": dict(generation_counts),
        }

    def _collect_birth_analytics(self, chart_ids: list[int] | set[int]) -> dict[str, Any]:
        birth_minutes: list[int] = []
        birth_month_counts: Counter[int] = Counter()
        birth_date_counts: Counter[str] = Counter()
        city_counts: Counter[str] = Counter()
        country_counts: Counter[str] = Counter()
        us_state_counts: Counter[str] = Counter()

        for chart_id in chart_ids:
            chart = self._get_chart_for_filter(int(chart_id))
            if chart is None:
                continue

            dt_value = getattr(chart, "dt", None)
            has_known_time = chart_uses_houses(chart)
            if isinstance(dt_value, datetime.datetime) and has_known_time:
                birth_minutes.append((int(dt_value.hour) * 60) + int(dt_value.minute))

            is_placeholder = self._is_placeholder_chart(chart)
            month_value = getattr(chart, "birth_month", None)
            day_value = getattr(chart, "birth_day", None)
            if (
                not is_placeholder
                and not isinstance(month_value, int)
                and isinstance(dt_value, datetime.datetime)
            ):
                month_value = int(dt_value.month)
            if (
                not is_placeholder
                and not isinstance(day_value, int)
                and isinstance(dt_value, datetime.datetime)
            ):
                day_value = int(dt_value.day)
            if isinstance(month_value, int) and 1 <= month_value <= 12:
                birth_month_counts[month_value] += 1
                if isinstance(day_value, int) and 1 <= day_value <= 31:
                    birth_date_counts[f"{month_value:02d}-{day_value:02d}"] += 1

            birthplace = str(getattr(chart, "birth_place", "") or "").strip()
            city, state, country = self._extract_birthplace_components(birthplace)
            canonical_city = normalize_city(city or "", country)
            if canonical_city:
                city_counts[canonical_city] += 1

            if country:
                canonical_country = normalize_country(country)
                if canonical_country:
                    country_counts[canonical_country] += 1

                resolved_country = resolve_country(country)
                if resolved_country and resolved_country.get("alpha_2") == "US":
                    canonical_state = normalize_us_state(state or birthplace)
                    if canonical_state:
                        us_state_counts[canonical_state] += 1

        mode_minutes = 0
        if birth_minutes:
            rounded_hours = [((minute + 30) // 60) % 24 for minute in birth_minutes]
            mode_hour = Counter(rounded_hours).most_common(1)[0][0]
            mode_minutes = mode_hour * 60

        return {
            "birth_minutes": birth_minutes,
            "mean_minutes": (sum(birth_minutes) / len(birth_minutes)) if birth_minutes else 0.0,
            "median_minutes": float(statistics.median(birth_minutes)) if birth_minutes else 0.0,
            "mode_hour_minutes": float(mode_minutes),
            "birth_month_counts": dict(birth_month_counts),
            "birth_date_counts": dict(birth_date_counts),
            "city_counts": dict(city_counts),
            "country_counts": dict(country_counts),
            "us_state_counts": dict(us_state_counts),
        }

    def _create_enneagram_database_analytics_section(self, panel: Any, layout: Any) -> None:
        enneagram_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "Enneagram",
            section_key="enneagram",
            expanded=self._is_database_metrics_section_expanded("enneagram"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "enneagram",
                checked,
            ),
        )
        self._database_metrics_section_expanded["enneagram"] = self._is_database_metrics_section_expanded("enneagram")
        self._database_metrics_section_visible["enneagram"] = self._is_database_metrics_section_visible("enneagram")
        self._create_analysis_chart_header(
            enneagram_section_layout,
            "Enneagram", #🎭Enneagram
            "enneagram",
            "enneagram",
            dropdown_options=[("Enneagram Predictions", "enneagram")],
            show_title=False,
        )
        self.enneagram_subheader_label = self._build_database_subheader_label(
            "Avg Enneagram type score predictions across the entire database of 0 (non-placeholder) charts."
        )
        enneagram_section_layout.addWidget(self.enneagram_subheader_label)
        (
            self.enneagram_distribution_chart_container,
            self.enneagram_distribution_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["enneagram"] = self.enneagram_distribution_chart_layout
        enneagram_section_layout.addWidget(self.enneagram_distribution_chart_container)

    @staticmethod
    def _normalize_enneagram_type(value: Any) -> int | None:
        try:
            type_num = int(value)
        except (TypeError, ValueError):
            return None
        if 1 <= type_num <= 9:
            return type_num
        return None

    @staticmethod
    def _normalize_enneagram_score(value: Any) -> float | None:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(score):
            return None
        return score

    def _extract_dominant_enneagram_type_from_chart_metadata(self, chart: Any) -> int | None:
        top_types = self._extract_top_enneagram_types_from_chart_metadata(chart, limit=1)
        if top_types:
            return top_types[0]
        return None

    def _calculate_enneagram_type_weights(self, chart: Any) -> dict[int, float]:
        scores = _calculate_enneagram_type_weights(
            chart,
            enneagram=ENNEAGRAM,
            calculate_sign_weights=_calculate_dominant_sign_weights,
            calculate_body_weights=_calculate_dominant_planet_weights,
            calculate_house_weights=_calculate_dominant_house_weights,
            chart_uses_houses=chart_uses_houses,
        )
        normalized_scores: dict[int, float] = {}
        if isinstance(scores, dict):
            for raw_type, raw_score in scores.items():
                normalized_type = self._normalize_enneagram_type(raw_type)
                normalized_score = self._normalize_enneagram_score(raw_score)
                if normalized_type is None or normalized_score is None:
                    continue
                normalized_scores[normalized_type] = normalized_score
        return normalized_scores

    def _cache_enneagram_prediction_metadata(self, chart: Any) -> dict[int, float]:
        scores = self._calculate_enneagram_type_weights(chart)
        ranked_scores = sorted(
            ((int(enneagram_type), float(score)) for enneagram_type, score in scores.items()),
            key=lambda item: (-item[1], item[0]),
        )
        if ranked_scores and ranked_scores[0][1] > 0:
            chart.enneagram_type_weights = {enneagram_type: score for enneagram_type, score in ranked_scores}
            chart.dominant_enneagram_type = ranked_scores[0][0]
            chart.top_three_enneagram_types = [
                enneagram_type
                for enneagram_type, score in ranked_scores[:3]
                if score > 0
            ]
        else:
            chart.enneagram_type_weights = {}
            chart.dominant_enneagram_type = None
            chart.top_three_enneagram_types = []
        return scores

    @staticmethod
    def _debug_chart_label(chart: Any) -> str:
        chart_id = getattr(chart, "id", None)
        chart_name = str(getattr(chart, "name", "") or "").strip()
        if chart_name:
            return f"{chart_name} (id={chart_id})"
        return f"id={chart_id}"

    def _refresh_chart_enneagram_prediction_metadata(self, chart: Any) -> bool:
        try:
            self._cache_enneagram_prediction_metadata(chart)
            return True
        except Exception:
            logger.exception(
                "Failed to cache Enneagram metadata for chart %s during database analytics refresh.",
                self._debug_chart_label(chart),
            )
            return False

    def _calculate_chart_enneagram_type_weights(self, chart: Any) -> dict[int, float]:
        try:
            return self._calculate_enneagram_type_weights(chart)
        except Exception:
            logger.exception(
                "Enneagram weight calculation failed for chart %s.",
                self._debug_chart_label(chart),
            )
            return {}

    def _resolve_chart_enneagram_weight_map(
        self,
        chart: Any,
    ) -> dict[int, float]:
        weight_map = getattr(chart, "enneagram_type_weights", None)
        if isinstance(weight_map, dict) and weight_map:
            return weight_map
        calculated = self._calculate_chart_enneagram_type_weights(chart)
        if calculated:
            try:
                chart.enneagram_type_weights = {
                    int(enneagram_type): float(score)
                    for enneagram_type, score in calculated.items()
                }
            except Exception:
                # Keep analytics resilient even if chart attributes are not writable.
                pass
            return calculated
        return {}

    def _extract_top_enneagram_types_from_chart_metadata(
        self,
        chart: Any,
        *,
        limit: int = 3,
    ) -> list[int]:
        normalized_limit = max(1, int(limit))

        direct_type = self._normalize_enneagram_type(
            getattr(chart, "dominant_enneagram_type", None)
        )
        top_types: list[int] = []
        if direct_type is not None:
            top_types.append(direct_type)

        top_three_candidates = (
            getattr(chart, "top_three_enneagram_types", None),
            getattr(chart, "top_3_enneagram_types", None),
            getattr(chart, "enneagram_top_three", None),
        )
        for candidate in top_three_candidates:
            if not isinstance(candidate, (list, tuple)):
                continue
            for entry in candidate:
                score_is_present = False
                normalized_score: float | None = None
                if isinstance(entry, (list, tuple)) and entry:
                    normalized = self._normalize_enneagram_type(entry[0])
                    if len(entry) > 1:
                        score_is_present = True
                        normalized_score = self._normalize_enneagram_score(entry[1])
                else:
                    normalized = self._normalize_enneagram_type(entry)
                if normalized is not None:
                    if score_is_present and (normalized_score is None or normalized_score <= 0):
                        continue
                    if normalized not in top_types:
                        top_types.append(normalized)
                    if len(top_types) >= normalized_limit:
                        return top_types[:normalized_limit]

        weight_candidates = (
            getattr(chart, "enneagram_type_weights", None),
            getattr(chart, "enneagram_scores", None),
        )
        for candidate in weight_candidates:
            if not isinstance(candidate, dict):
                continue
            ranked: list[tuple[int, float]] = []
            for raw_type, raw_weight in candidate.items():
                normalized_type = self._normalize_enneagram_type(raw_type)
                normalized_score = self._normalize_enneagram_score(raw_weight)
                if normalized_type is None or normalized_score is None:
                    continue
                ranked.append((normalized_type, normalized_score))
            ranked.sort(key=lambda item: (-item[1], item[0]))
            for normalized_type, normalized_score in ranked:
                if normalized_score <= 0:
                    continue
                if normalized_type not in top_types:
                    top_types.append(normalized_type)
                if len(top_types) >= normalized_limit:
                    return top_types[:normalized_limit]
        return top_types[:normalized_limit]

    def _populate_enneagram_snapshot(self, snapshot: dict[str, Any], chart: Any) -> None:
        if self._is_placeholder_chart(chart):
            return
        refresh_ok = self._refresh_chart_enneagram_prediction_metadata(chart)
        weight_map = self._resolve_chart_enneagram_weight_map(chart)
        weight_snapshot_populated = False
        if isinstance(weight_map, dict):
            normalized_weights: dict[int, float] = {}
            weight_total = 0.0
            for raw_type, raw_weight in weight_map.items():
                normalized_type = self._normalize_enneagram_type(raw_type)
                normalized_score = self._normalize_enneagram_score(raw_weight)
                if normalized_type is None or normalized_score is None or normalized_score <= 0:
                    continue
                normalized_weights[normalized_type] = normalized_score
                weight_total += normalized_score
            if weight_total > 0:
                for enneagram_type in range(1, 10):
                    normalized_weight = float(normalized_weights.get(enneagram_type, 0.0)) / float(weight_total)
                    snapshot["enneagram_weight_totals"][enneagram_type] += normalized_weight
                snapshot["enneagram_weight_chart_count"] += 1
                weight_snapshot_populated = True
        top_types = self._extract_top_enneagram_types_from_chart_metadata(chart, limit=3)
        if not weight_snapshot_populated and top_types:
            fallback_weight = 1.0 / float(len(top_types))
            for enneagram_type in top_types:
                if enneagram_type in snapshot["enneagram_weight_totals"]:
                    snapshot["enneagram_weight_totals"][enneagram_type] += fallback_weight
            snapshot["enneagram_weight_chart_count"] += 1
            warned_labels = getattr(self, "_enneagram_weight_fallback_warned_labels", set())
            chart_label = self._debug_chart_label(chart)
            if chart_label not in warned_labels:
                logger.warning(
                    "Enneagram weight map missing/empty for chart %s; using top-type fallback weights %s "
                    "(refresh_ok=%s).",
                    chart_label,
                    top_types,
                    refresh_ok,
                )
                warned_labels.add(chart_label)
                self._enneagram_weight_fallback_warned_labels = warned_labels
        elif not weight_snapshot_populated and not top_types and refresh_ok:
            logger.warning(
                "Enneagram metadata produced no usable weights or top types for chart %s.",
                self._debug_chart_label(chart),
            )
        for enneagram_type in top_types:
            if enneagram_type in snapshot["enneagram_totals"]:
                snapshot["enneagram_totals"][enneagram_type] += 1
                snapshot["enneagram_total_count"] += 1

    @staticmethod
    def _is_placeholder_chart(chart: Any) -> bool:
        return chart_is_non_aggregable(chart)

    def _render_enneagram_database_analytics(
        self,
        *,
        selection_cache: dict[str, Any],
        database_cache: dict[str, Any],
        loaded_charts: int,
        should_refresh: Callable[[str], bool],
    ) -> None:
        enneagram_labels = [
            (
                f"e{enneagram_type} "
                f"{str(ENNEAGRAM.get(enneagram_type, {}).get('name', '')).strip()} "
                f"({int(database_cache.get('enneagram_totals', {}).get(enneagram_type, 0)):,} in DB)"
            ).strip()
            for enneagram_type in range(1, 10)
        ]
        enneagram_label_by_type = {
            enneagram_type: enneagram_labels[enneagram_type - 1] for enneagram_type in range(1, 10)
        }
        selection_weight_chart_count = max(0, int(selection_cache.get("enneagram_weight_chart_count", 0)))
        database_weight_chart_count = max(0, int(database_cache.get("enneagram_weight_chart_count", 0)))
        selection_enneagram_counts = {
            enneagram_label_by_type[enneagram_type]: selection_weight_chart_count
            for enneagram_type in range(1, 10)
        }
        database_enneagram_counts = {
            enneagram_label_by_type[enneagram_type]: database_weight_chart_count
            for enneagram_type in range(1, 10)
        }
        selection_enneagram_values = {
            enneagram_label_by_type[enneagram_type]: (
                float(selection_cache["enneagram_weight_totals"].get(enneagram_type, 0.0))
                / float(selection_weight_chart_count)
                if selection_weight_chart_count
                else 0.0
            )
            for enneagram_type in range(1, 10)
        }
        database_enneagram_values = {
            enneagram_label_by_type[enneagram_type]: (
                float(database_cache["enneagram_weight_totals"].get(enneagram_type, 0.0))
                / float(database_weight_chart_count)
                if database_weight_chart_count
                else 0.0
            )
            for enneagram_type in range(1, 10)
        }
        selection_enneagram_total = int(selection_cache.get("enneagram_total_count", 0))
        database_enneagram_total = int(database_cache.get("enneagram_total_count", 0))
        if selection_weight_chart_count <= 0 and selection_enneagram_total > 0:
            logger.warning(
                "Selection Enneagram weighted chart count is zero; falling back to top-type frequency distribution."
            )
            selection_enneagram_values = {
                enneagram_label_by_type[enneagram_type]: (
                    float(selection_cache["enneagram_totals"].get(enneagram_type, 0.0))
                    / float(selection_enneagram_total)
                )
                for enneagram_type in range(1, 10)
            }
        if database_weight_chart_count <= 0 and database_enneagram_total > 0:
            logger.warning(
                "Database Enneagram weighted chart count is zero; falling back to top-type frequency distribution."
            )
            database_enneagram_values = {
                enneagram_label_by_type[enneagram_type]: (
                    float(database_cache["enneagram_totals"].get(enneagram_type, 0.0))
                    / float(database_enneagram_total)
                )
                for enneagram_type in range(1, 10)
            }
        enneagram_label_colors = {
            enneagram_label_by_type[enneagram_type]: str(
                ENNEAGRAM.get(enneagram_type, {}).get("color", CHART_THEME_COLORS["text"])
            ).strip() or CHART_THEME_COLORS["text"]
            for enneagram_type in range(1, 10)
        }
        selected_chart_count = max(0, int(loaded_charts))
        if selected_chart_count > 0:
            self.enneagram_subheader_label.setText(
                "Predicted Enneagram type scores for selected chart(s) relative to database average."
            )
        else:
            self.enneagram_subheader_label.setText(
                "Avg Enneagram type score predictions across the entire database of "
                f"{database_weight_chart_count:,} (non-placeholder) charts."
            )
        if should_refresh("enneagram"):
            enneagram_canvas = self._build_dominant_planet_chart(
                selection_planets=selection_enneagram_values,
                database_planets=database_enneagram_values,
                selection_planet_counts=selection_enneagram_counts,
                database_planet_counts=database_enneagram_counts,
                loaded_charts=loaded_charts,
                labels=enneagram_labels,
                force_value_fallback_colors=False,
                label_colors=enneagram_label_colors,
                include_count_prefixes=False,
            )
            self._clear_layout(self.enneagram_distribution_chart_layout)
            self.enneagram_distribution_chart_layout.addWidget(
                enneagram_canvas,
                0,
            )
        self._analysis_chart_export_rows["enneagram"] = self._build_analysis_export_rows(
            labels=enneagram_labels,
            selection_values=[selection_enneagram_values[label] for label in enneagram_labels],
            database_values=[database_enneagram_values[label] for label in enneagram_labels],
            selection_counts=[selection_enneagram_counts[label] for label in enneagram_labels],
            database_counts=[database_enneagram_counts[label] for label in enneagram_labels],
            loaded_charts=loaded_charts,
        )

    def _create_bazi_database_analytics_section(self, panel: Any, layout: Any) -> None:
        bazi_section_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "🐉BaZi",
            section_key="bazi",
            expanded=self._is_database_metrics_section_expanded("bazi"),
            on_toggled=lambda checked: self._set_database_metrics_section_expanded(
                "bazi",
                checked,
            ),
        )
        self._database_metrics_section_expanded["bazi"] = self._is_database_metrics_section_expanded("bazi")
        self._create_analysis_chart_header(
            bazi_section_layout,
            "BaZi",
            "bazi",
            "bazi",
            dropdown_options=[
                ("All Pillars", "all"),
                ("Year Pillar", "year"),
                ("Month Pillar", "month"),
                ("Day Pillar", "day"),
                ("Hour Pillar", "hour"),
                ("BaZi Elements", "elements"),
                ("BaZi Animal Signs", "animals"),
            ],
            show_title=False,
        )
        bazi_subheader = self._build_database_subheader_label(
            "BaZi pillar, animal-sign, and five-element distributions across selection/database."
        )
        bazi_section_layout.addWidget(bazi_subheader)
        (
            self.bazi_chart_container,
            self.bazi_chart_layout,
        ) = self._create_database_analytics_chart_container()
        self._database_metrics_chart_layouts["bazi"] = self.bazi_chart_layout
        bazi_section_layout.addWidget(self.bazi_chart_container)

    def _render_bazi_database_analytics(
        self,
        *,
        selection_cache: dict[str, Any],
        database_cache: dict[str, Any],
        loaded_charts: int,
        should_refresh: Callable[[str], bool],
    ) -> None:
        bazi_mode = self._bazi_mode
        if bazi_mode == "elements":
            selection_bazi_counts = {
                key: int(value)
                for key, value in selection_cache.get("bazi_element_counts", {}).items()
                if int(value) > 0
            }
            database_bazi_counts = {
                key: int(value)
                for key, value in database_cache.get("bazi_element_counts", {}).items()
                if int(value) > 0
            }
        elif bazi_mode == "animals":
            selection_bazi_counts: dict[str, int] = {}
            for pillar_label, value in selection_cache.get("bazi_sign_counts", {}).get("all", {}).items():
                normalized_pillar = str(pillar_label or "").strip()
                if len(normalized_pillar) != 2:
                    continue
                animal_label = normalized_pillar[1]
                selection_bazi_counts[animal_label] = int(selection_bazi_counts.get(animal_label, 0)) + int(value)
            database_bazi_counts: dict[str, int] = {}
            for pillar_label, value in database_cache.get("bazi_sign_counts", {}).get("all", {}).items():
                normalized_pillar = str(pillar_label or "").strip()
                if len(normalized_pillar) != 2:
                    continue
                animal_label = normalized_pillar[1]
                database_bazi_counts[animal_label] = int(database_bazi_counts.get(animal_label, 0)) + int(value)
            selection_bazi_counts = {key: value for key, value in selection_bazi_counts.items() if int(value) > 0}
            database_bazi_counts = {key: value for key, value in database_bazi_counts.items() if int(value) > 0}
        else:
            selection_bazi_counts = {
                key: int(value)
                for key, value in selection_cache.get("bazi_sign_counts", {}).get(bazi_mode, {}).items()
                if int(value) > 0
            }
            database_bazi_counts = {
                key: int(value)
                for key, value in database_cache.get("bazi_sign_counts", {}).get(bazi_mode, {}).items()
                if int(value) > 0
            }
        label_counts_source = (
            {
                label: int(selection_bazi_counts.get(label, 0)) + int(database_bazi_counts.get(label, 0))
                for label in (set(selection_bazi_counts.keys()) | set(database_bazi_counts.keys()))
            }
            if loaded_charts
            else database_bazi_counts
        )
        bazi_labels = [
            item[0]
            for item in sorted(
                label_counts_source.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]
        display_label_by_raw = {
            label: self._bazi_label_with_english(label, mode=bazi_mode)
            for label in bazi_labels
        }
        display_labels = [display_label_by_raw.get(label, label) for label in bazi_labels]
        selection_display_counts = {
            display_label_by_raw.get(label, label): int(selection_bazi_counts.get(label, 0))
            for label in bazi_labels
        }
        database_display_counts = {
            display_label_by_raw.get(label, label): int(database_bazi_counts.get(label, 0))
            for label in bazi_labels
        }
        bazi_bar_colors = None
        if bazi_mode == "animals":
            bazi_bar_colors = []
            for raw_label in bazi_labels:
                english_animal = str(self.BAZI_BRANCH_TRANSLATIONS.get(str(raw_label), "")).strip().casefold()
                color = str(
                    (BAZI_ZODIAC.get(english_animal, {}) or {}).get("color", "")
                ).strip()
                bazi_bar_colors.append(color or "#6fa8dc")
        if should_refresh("bazi"):
            self._clear_layout(self.bazi_chart_layout)
            if display_labels:
                bazi_canvas = self._build_count_distribution_chart(
                    labels=display_labels,
                    selection_counts=[selection_display_counts.get(label, 0) for label in display_labels],
                    database_counts=[database_display_counts.get(label, 0) for label in display_labels],
                    loaded_charts=loaded_charts,
                    auto_height=True,
                    bar_colors=bazi_bar_colors,
                    emoji_label_font_family=(
                        self._available_bazi_emoji_font_families()
                        if any(self._label_contains_emoji(label) for label in display_labels)
                        else None
                    ),
                )
                self.bazi_chart_layout.addWidget(bazi_canvas, 0)
            else:
                self.bazi_chart_layout.addWidget(
                    self._build_text_analysis_widget(["None available"]),
                    0,
                    Qt.AlignTop,
                )
        self._analysis_chart_export_rows["bazi"] = self._build_analysis_export_rows(
            labels=display_labels,
            selection_values=[float(selection_display_counts.get(label, 0)) for label in display_labels],
            database_values=[float(database_display_counts.get(label, 0)) for label in display_labels],
            selection_counts=[int(selection_display_counts.get(label, 0)) for label in display_labels],
            database_counts=[int(database_display_counts.get(label, 0)) for label in display_labels],
            loaded_charts=loaded_charts,
        )

    @staticmethod
    def _format_partial_birth_date(
        month_value: int | None,
        day_value: int | None,
        year_value: int | None,
    ) -> str:
        month_label = f"{month_value:02d}" if isinstance(month_value, int) and 1 <= month_value <= 12 else "?"
        day_label = f"{day_value:02d}" if isinstance(day_value, int) and 1 <= day_value <= 31 else "?"
        year_label = f"{year_value:04d}" if isinstance(year_value, int) and year_value > 0 else "?"
        return f"{month_label}.{day_label}.{year_label}"

    def _build_single_metric_chart(
        self,
        label: str,
        selection_value: float,
        database_value: float,
        loaded_charts: int,
    ) -> FigureCanvas:
        figure = Figure(figsize=(4.8, 1.8))
        figure.patch.set_facecolor(self._database_analytics_figure_facecolor())
        ax = figure.add_subplot(111)
        ax.set_facecolor(self._database_analytics_axes_facecolor())

        display_value = selection_value if loaded_charts else database_value
        labels = [f"({self._minutes_to_label(display_value)}) {label}"]
        positions = [0]
        bars = ax.barh(positions, [display_value], color="#6fa8dc", height=0.55)
        ax.set_xlim(0, 24 * 60)
        ax.set_yticks(positions, labels=labels)
        ax.tick_params(axis="y", labelsize=8, colors=CHART_THEME_COLORS["text"], pad=6)
        ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
        ax.set_xticks([0, 360, 720, 1080, 1439])
        ax.set_xticklabels(["00:00", "06:00", "12:00", "18:00", "23:59"])
        ax.set_xlabel("")
        for bar in bars:
            value = bar.get_width()
            ax.text(
                min(value + 20, (24 * 60) - 4),
                bar.get_y() + (bar.get_height() / 2),
                self._minutes_to_label(value),
                va="center",
                ha="left" if value < (24 * 60) - 40 else "right",
                color=CHART_THEME_COLORS["text"],
                fontsize=7.5,
            )
        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in ax.get_yticklabels():
            tick_label.set_ha("right")

        self._apply_tight_layout(figure)
        figure.subplots_adjust(left=0.51, bottom=0.24, right=0.97, top=0.98)
        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas

    def _build_count_distribution_chart(
        self,
        labels: list[str],
        selection_counts: list[int],
        database_counts: list[int],
        loaded_charts: int,
        auto_height: bool = False,
        use_earthtone_cycle: bool = False,
        bar_colors: list[str] | None = None,
        emoji_label_font_family: list[str] | None = None,
    ) -> FigureCanvas:
        chart_height = max(2.8, min(12.0, (len(labels) * 0.32) + 0.8)) if auto_height else 2.8
        figure = Figure(figsize=(1.5, chart_height))
        figure.patch.set_facecolor(self._database_analytics_figure_facecolor())
        ax = figure.add_subplot(111)
        ax.set_facecolor(self._database_analytics_axes_facecolor())

        display_labels = [
            self._format_selection_database_count_label(
                label,
                int(database_count),
                int(selection_count),
                loaded_charts > 0,
            )
            for label, selection_count, database_count in zip(labels, selection_counts, database_counts)
        ]
        positions = list(range(len(labels)))
        if bar_colors is not None:
            colors = list(bar_colors)
        else:
            values_for_color_scale = selection_counts if loaded_charts else database_counts
            value_min = float(min(values_for_color_scale, default=0))
            value_max = float(max(values_for_color_scale, default=1))
            colors = [
                self._value_length_color(float(value), value_min, value_max)
                for value in values_for_color_scale
            ]
        if loaded_charts == 0:
            bars = ax.barh(positions, database_counts, color=colors, height=0.55, zorder=2)
            max_value = max(database_counts, default=0)
            self._set_x_limits_with_padding(ax, 0.0, float(max(1, max_value)))
            for bar, value in zip(bars, database_counts):
                ax.text(
                    bar.get_width() + 0.06,
                    bar.get_y() + (bar.get_height() / 2),
                    str(value),
                    va="center",
                    ha="left",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        else:
            total_selection = float(sum(max(0, int(value)) for value in selection_counts))
            total_database = float(sum(max(0, int(value)) for value in database_counts))
            selection_values = [
                (float(value) / total_selection) if total_selection > 0 else 0.0
                for value in selection_counts
            ]
            database_values = [
                (float(value) / total_database) if total_database > 0 else 0.0
                for value in database_counts
            ]
            differences = [
                selection - database
                for selection, database in zip(selection_values, database_values)
            ]
            widths = [abs(value) for value in differences]
            bars = ax.barh(
                positions,
                widths,
                left=[0 if value >= 0 else -abs(value) for value in differences],
                color=colors,
                height=0.55,
                zorder=2,
            )
            axis_limit = self._configure_symmetric_percent_difference_axis(ax, differences)
            ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            self._draw_category_significance_guides(
                ax,
                selection_counts,
                database_counts,
                loaded_charts,
            )
            for bar, diff_value in zip(bars, differences):
                width = bar.get_width()
                if width <= 0:
                    continue
                label_x = width if diff_value >= 0 else -width
                label_x = self._difference_label_x(diff_value, axis_limit)
                ax.text(
                    label_x,
                    bar.get_y() + (bar.get_height() / 2),
                    _format_percent(abs(diff_value)),
                    va="center",
                    ha="left" if diff_value >= 0 else "right",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.5,
                )
        ax.set_yticks(positions, labels=display_labels)
        ax.invert_yaxis()
        self._set_compact_barh_y_limits(ax, len(labels), 0.55)
        ax.tick_params(axis="y", labelsize=7.5, colors=CHART_THEME_COLORS["text"], pad=6)
        ax.tick_params(axis="x", labelsize=7, colors=CHART_THEME_COLORS["muted_text"])
        ax.set_xlabel("")
        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in ax.get_yticklabels():
            tick_label.set_ha("right")
            if (
                emoji_label_font_family
                and self._label_contains_emoji(tick_label.get_text())
            ):
                tick_label.set_fontfamily(emoji_label_font_family)

        self._apply_tight_layout(figure)
        figure.subplots_adjust(left=0.36, bottom=0.10, right=0.97, top=0.97)
        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas

    def _available_bazi_emoji_font_families(self) -> list[str]:
        """Return emoji-capable font families that are available on this machine."""
        cached = self._BAZI_AVAILABLE_EMOJI_FONT_FAMILIES
        if cached is not None:
            return list(cached)

        available_names = {
            str(entry.name).strip()
            for entry in getattr(mpl_font_manager.fontManager, "ttflist", [])
            if getattr(entry, "name", None)
        }
        selected = tuple(
            family
            for family in self.BAZI_EMOJI_FONT_FAMILIES
            if family in available_names
        )
        self._BAZI_AVAILABLE_EMOJI_FONT_FAMILIES = selected
        return list(selected)

    def _build_tag_distribution_chart(
        self,
        *,
        category_label: str,
        labels: list[str],
        selection_values: list[float],
        database_values: list[float],
        selection_counts: list[int],
        database_counts: list[int],
        loaded_charts: int,
    ) -> FigureCanvas:
        chart_height = max(2.9, min(14.0, (len(labels) * 0.38) + 1.0))
        figure = Figure(figsize=(1.5, chart_height))
        figure.patch.set_facecolor(self._database_analytics_figure_facecolor())
        ax = figure.add_subplot(111)
        ax.set_facecolor(self._database_analytics_axes_facecolor())

        display_labels = [
            self._format_selection_database_count_label(
                label,
                int(database_count),
                int(selection_count),
                loaded_charts > 0,
            )
            for label, selection_count, database_count in zip(labels, selection_counts, database_counts)
        ]
        positions = list(range(len(labels)))
        if loaded_charts > 0:
            differences = [
                float(selection_value) - float(database_value)
                for selection_value, database_value in zip(selection_values, database_values)
            ]
            colors = [
                self._value_length_color(abs(float(value)), 0.0, max((abs(diff) for diff in differences), default=0.01))
                for value in differences
            ]
            bars = ax.barh(
                positions,
                [abs(value) for value in differences],
                left=[0 if value >= 0 else -abs(value) for value in differences],
                color=colors,
                height=0.55,
                zorder=2,
            )
            axis_limit = self._configure_symmetric_percent_difference_axis(ax, differences)
            ax.axvline(0, color=CHART_THEME_COLORS["spine"], linewidth=1.5, zorder=1)
            self._draw_category_significance_guides(
                ax,
                selection_counts,
                database_counts,
                loaded_charts,
            )
            for bar, diff_value in zip(bars, differences):
                if bar.get_width() <= 0:
                    continue
                ax.text(
                    self._difference_label_x(diff_value, axis_limit),
                    bar.get_y() + (bar.get_height() / 2),
                    _format_percent(abs(diff_value)),
                    va="center",
                    ha="left" if diff_value >= 0 else "right",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.2,
                )
        else:
            colors = [
                self._value_length_color(float(value), 0.0, max(database_values, default=0.01))
                for value in database_values
            ]
            bars = ax.barh(positions, database_values, color=colors, height=0.55, zorder=2)
            _, axis_max = self._configure_positive_percent_axis(ax, database_values)
            for bar, database_value in zip(bars, database_values):
                ax.text(
                    min(database_value + max(axis_max * 0.015, 0.003), axis_max * 0.985),
                    bar.get_y() + (bar.get_height() / 2),
                    f"{database_value * 100:.2f}%",
                    va="center",
                    ha="left",
                    color=CHART_THEME_COLORS["text"],
                    fontsize=7.2,
                )
        ax.set_yticks(positions, labels=display_labels)
        ax.tick_params(axis="y", labelsize=7.2, colors=CHART_THEME_COLORS["text"], pad=6)
        ax.tick_params(axis="x", labelsize=7.2, colors=CHART_THEME_COLORS["muted_text"])
        ax.set_title(str(category_label), color=CHART_THEME_COLORS["text"], fontsize=8, pad=6)
        ax.grid(axis="x", color=CHART_THEME_COLORS["spine"], linewidth=0.6, alpha=0.35, zorder=0)
        for spine in ax.spines.values():
            spine.set_color(CHART_THEME_COLORS["spine"])
        for tick_label in ax.get_yticklabels():
            tick_label.set_ha("right")
        self._apply_tight_layout(figure)
        figure.subplots_adjust(left=0.50, bottom=0.08, right=0.97, top=0.92)
        canvas = FigureCanvas(figure)
        self._configure_left_panel_canvas(canvas, figure)
        canvas.draw_idle()
        return canvas
    @staticmethod
    def _database_analytics_figure_facecolor() -> str:
        if DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS:
            return DATABASE_ANALYTICS_GRAPH_LABEL_REGION_DEBUG_COLOR
        return CHART_THEME_COLORS["background"]

    @staticmethod
    def _database_analytics_axes_facecolor() -> str:
        if DATABASE_ANALYTICS_DEBUG_VISUAL_BOUNDS:
            return DATABASE_ANALYTICS_GRAPH_AREA_DEBUG_COLOR
        return CHART_THEME_COLORS["background"]
