"""Chart Info presentation for Database Analytics popout charts.

This workflow module deliberately owns the user-facing HTML while the legacy
Database Analytics mixin continues to own chart collection and Qt mechanics.
Section-specific captions and definitions belong here as they are introduced.
"""

from __future__ import annotations

import html
import math
import re
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from ephemeraldaddy.analysis.enneagram import ENNEAGRAM
from ephemeraldaddy.core.interpretations import (
    ELEMENT_COLORS,
    MODE_COLORS,
    NAKSHATRA_PLANET_COLOR,
    PLANET_COLORS,
    SIGN_COLORS,
)
from ephemeraldaddy.gui.features.charts.enneagram_predictions import (
    build_enneagram_popout_info_html,
)
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR, CHART_THEME_COLORS


@dataclass(frozen=True, slots=True)
class DatabaseAnalyticsChartInfoTarget:
    """A generic Chart Info topic selected from an analytics graph."""

    kind: str
    value: str


@contextmanager
def generic_database_analytics_chart_context(owner: Any) -> Iterator[None]:
    """Suppress Chart Editor placement specificity while rendering DB info."""
    had_latest_chart = hasattr(owner, "_latest_chart")
    latest_chart = getattr(owner, "_latest_chart", None)
    if had_latest_chart:
        owner._latest_chart = None
    try:
        yield
    finally:
        if had_latest_chart:
            owner._latest_chart = latest_chart


def combine_database_analytics_chart_info_html(
    analytics_html: str, generic_html: str
) -> str:
    """Place population statistics before the generic reference material."""
    return f"{analytics_html}<hr>{generic_html}" if generic_html else analytics_html


def database_analytics_chart_info_target(
    *, chart_title: str, label: str, chart_mode: str | None = None
) -> DatabaseAnalyticsChartInfoTarget | None:
    """Map an analytics label to the appwide Chart Info topic vocabulary.

    ``chart_mode`` is deliberately preferred for Human Design because its
    numeric labels (gates and lines) are otherwise ambiguous.  The remaining
    categories can be identified from their centralized interpretation color
    maps, keeping this routing independent from Qt and from Chart Editor state.
    """
    clean_label = re.sub(r"^\([^)]*\)\s*", "", str(label or "").strip())
    mode = str(chart_mode or "").strip().casefold()
    if mode == "hd_gates" and clean_label.isdigit():
        return DatabaseAnalyticsChartInfoTarget("gate", clean_label)
    if mode == "hd_lines" and clean_label.isdigit():
        return DatabaseAnalyticsChartInfoTarget("hd-line", clean_label)
    if mode == "hd_channels" and re.fullmatch(r"\d{1,2}-\d{1,2}", clean_label):
        return DatabaseAnalyticsChartInfoTarget("hd-channel", clean_label)
    if mode == "hd_defined_centers":
        return DatabaseAnalyticsChartInfoTarget("hd-center", clean_label)
    hd_property_by_mode = {
        "hd_types": "type",
        "hd_profiles": "profile",
        "hd_authorities": "authority",
        "hd_incarnation_crosses": "incarnation_cross",
    }
    if mode in hd_property_by_mode:
        if mode == "hd_types" and clean_label == "MF Generator":
            clean_label = "Manifesting Generator"
        return DatabaseAnalyticsChartInfoTarget(
            f"hd-property:{hd_property_by_mode[mode]}", clean_label
        )

    if clean_label in SIGN_COLORS:
        return DatabaseAnalyticsChartInfoTarget("sign", clean_label)
    if clean_label in ELEMENT_COLORS:
        return DatabaseAnalyticsChartInfoTarget("element", clean_label)
    if clean_label.casefold() in MODE_COLORS:
        return DatabaseAnalyticsChartInfoTarget("mode", clean_label)
    if clean_label in NAKSHATRA_PLANET_COLOR:
        return DatabaseAnalyticsChartInfoTarget("nakshatra", clean_label)

    house_match = re.fullmatch(r"(?:house\s+)?(1[0-2]|[1-9])", clean_label, re.IGNORECASE)
    title = str(chart_title or "").casefold()
    if house_match and ("house" in title or "house" in clean_label.casefold()):
        return DatabaseAnalyticsChartInfoTarget("house", house_match.group(1))

    if clean_label in PLANET_COLORS:
        return DatabaseAnalyticsChartInfoTarget("planet", clean_label)
    return None


def _database_deviation_html(z_score: float | None) -> str:
    if z_score is None or not math.isfinite(z_score):
        return "Database deviation: unavailable"
    deviation_color = "#70d68a" if z_score > 0 else "#ff7b7b" if z_score < 0 else "#d0d0d0"
    direction = "above" if z_score > 0 else "below" if z_score < 0 else "at"
    return (
        f'Database deviation: <b style="color:{deviation_color};">'
        f"{abs(z_score):.2f} standard deviations {direction} the database norm</b>"
    )


def _section_detail_html(*, chart_title: str, enneagram_type: int | None) -> str:
    """Return optional section-specific detail beneath the standard summary."""
    if enneagram_type is None or "enneagram" not in chart_title.casefold():
        return ""
    return build_enneagram_popout_info_html(
        enneagram_type,
        enneagram=ENNEAGRAM,
        chart_theme_colors=CHART_THEME_COLORS,
        highlight_color=CHART_DATA_HIGHLIGHT_COLOR,
        debug_math_enabled=False,
        chart=None,
        calculate_type_weights=None,
    )


def build_database_analytics_popout_chart_info_html(
    *,
    chart_title: str,
    label: str,
    label_color: str,
    associated_charts: Sequence[tuple[str, str]],
    z_score: float | None,
    trait_description: str | None = None,
    enneagram_type: int | None = None,
) -> str:
    """Render the standardized Chart Info body for a clicked analytics bar."""
    associated_html = ", ".join(
        f'<a href="chart:{html.escape(chart_uid, quote=True)}">{html.escape(name)}</a>'
        for chart_uid, name in associated_charts
    ) or "None"
    description_html = (
        f"<p><i>{html.escape(trait_description)}</i></p>" if trait_description else ""
    )
    detail_html = _section_detail_html(
        chart_title=chart_title,
        enneagram_type=enneagram_type,
    )
    return (
        f'<h3 style="color:{html.escape(label_color)}; font-weight:800;">'
        f"{html.escape(label)}</h3>"
        f"{description_html}"
        f'<p><b style="color:{CHART_DATA_HIGHLIGHT_COLOR};">Associated charts:</b> '
        f"{associated_html}</p>"
        f"<p>{_database_deviation_html(z_score)}</p>"
        f"{detail_html}"
    )
