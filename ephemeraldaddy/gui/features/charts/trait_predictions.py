"""Chart View custom trait prediction rendering helpers."""

from __future__ import annotations

import html
from typing import Any

from PySide6.QtWidgets import QLabel

from ephemeraldaddy.analysis.traits import calculate_trait_likelihoods, list_traits

_BAR_WIDTH_PX = 120


def _trait_bar(name: str, percentage: float, *, polarity: str) -> str:
    safe_name = html.escape(name)
    pct = max(0.0, min(100.0, percentage))
    fill_width = int(round((_BAR_WIDTH_PX * pct) / 100.0))
    color = "#79d28c" if polarity == "top" else "#d28c79"
    return (
        "<tr>"
        f"<td style='padding:1px 8px 1px 0; white-space:nowrap;'>{safe_name}</td>"
        f"<td style='padding:1px 8px 1px 0; text-align:right;'>{pct:.1f}%</td>"
        f"<td style='width:{_BAR_WIDTH_PX}px;'>"
        f"<div style='background:#333; width:{_BAR_WIDTH_PX}px; height:8px;'>"
        f"<div style='background:{color}; width:{fill_width}px; height:8px;'></div>"
        "</div></td></tr>"
    )


def render_traits_predictions(owner: Any, chart: Any | None) -> None:
    """Render uploaded custom trait scores into Chart View's Predictions panel."""
    label = getattr(owner, "traits_prediction_label", None)
    if not isinstance(label, QLabel):
        return
    traits = list_traits()
    if not traits:
        label.setText("No traits uploaded. Add traits in Settings > Traits.")
        return
    if chart is None or owner._is_placeholder_chart(chart):
        label.setText("Trait predictions unavailable for this chart.")
        return
    try:
        # calculate_trait_likelihoods wraps calculate_trait_scores and converts
        # the signed raw totals to user-facing percentages.
        likelihoods = calculate_trait_likelihoods(chart, traits)
    except Exception as exc:
        label.setText(f"Trait predictions unavailable: {html.escape(str(exc))}")
        return
    ranked = sorted(likelihoods.items(), key=lambda item: item[1], reverse=True)
    if not ranked:
        label.setText("No scorable traits uploaded.")
        return
    top_rows = ranked[:5]
    bottom_rows = list(reversed(ranked[-5:])) if len(ranked) > 5 else []
    parts = [
        "<div style='color:#d8d8d8; padding-bottom:4px;'>"
        "Percentages are evidence likelihoods: 50% is neutral, above 50% means the chart matched more supporting criteria, "
        "and below 50% means it matched more anti-criteria."
        "</div>",
        "<b>Top 5 traits</b>",
        "<table cellspacing='0' cellpadding='0'>",
        *[_trait_bar(name, pct, polarity="top") for name, pct in top_rows],
        "</table>",
    ]
    if bottom_rows:
        parts.extend([
            "<div style='padding-top:6px;'><b>Bottom 5 traits</b></div>",
            "<table cellspacing='0' cellpadding='0'>",
            *[_trait_bar(name, pct, polarity="bottom") for name, pct in bottom_rows],
            "</table>",
        ])
    label.setText("".join(parts))
