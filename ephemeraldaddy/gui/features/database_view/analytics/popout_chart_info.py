"""Chart Info presentation for Database Analytics popout charts.

This workflow module deliberately owns the user-facing HTML while the legacy
Database Analytics mixin continues to own chart collection and Qt mechanics.
Section-specific captions and definitions belong here as they are introduced.
"""

from __future__ import annotations

import html
import math
from collections.abc import Sequence

from ephemeraldaddy.analysis.enneagram import ENNEAGRAM
from ephemeraldaddy.gui.features.charts.enneagram_predictions import (
    build_enneagram_popout_info_html,
)
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR, CHART_THEME_COLORS


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
