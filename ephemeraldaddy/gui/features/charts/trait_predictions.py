"""Chart View custom trait prediction rendering helpers."""

from __future__ import annotations

import html
from typing import Any

from PySide6.QtWidgets import QLabel

from ephemeraldaddy.analysis.traits import DEFAULT_TRAIT_COLOR, calculate_trait_likelihoods, list_traits, normalize_trait_color


def _trait_rank_row(rank: int, name: str, percentage: float, *, color: str) -> str:
    safe_name = html.escape(name)
    pct = max(0.0, min(100.0, percentage))
    safe_color = html.escape(normalize_trait_color(color))
    return (
        "<tr>"
        f"<td style='padding:1px 8px 1px 0; text-align:right; color:#d8d8d8;'>{rank}.</td>"
        f"<td style='padding:1px 8px 1px 0; white-space:nowrap; color:{safe_color};'>{safe_name}</td>"
        f"<td style='padding:1px 0; text-align:right; color:#d8d8d8;'>{pct:.1f}%</td>"
        "</tr>"
    )


def render_traits_predictions(owner: Any, chart: Any | None) -> None:
    """Render uploaded custom trait scores into Chart View's Predictions panel."""
    label = getattr(owner, "traits_prediction_label", None)
    if not isinstance(label, QLabel):
        return
    traits = list_traits(active_only=True)
    if not traits:
        if list_traits():
            label.setText("No active traits. Reactivate traits in Settings > Traits to include them in Predictions.")
        else:
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
    color_by_name = {
        str(trait.get("name", "")): normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR)))
        for trait in traits
    }
    ranked = sorted(likelihoods.items(), key=lambda item: item[1], reverse=True)
    if not ranked:
        label.setText("No scorable traits uploaded.")
        return
    top_rows = ranked[:7]
    bottom_rows = list(reversed(ranked[-7:])) if len(ranked) > 7 else []
    parts = [
        "<div style='color:#d8d8d8; padding-bottom:4px;'>"
        "Traits are ranked by evidence likelihood: higher percentages indicate stronger matches to supporting criteria, "
        "while lower percentages indicate stronger matches to anti-criteria."
        "</div>",
        "<p><b>Top 5 traits</b></p>",
        "<table cellspacing='0' cellpadding='0'>",
        *[
            _trait_rank_row(rank, name, pct, color=color_by_name.get(name, DEFAULT_TRAIT_COLOR))
            for rank, (name, pct) in enumerate(top_rows, start=1)
        ],
        "</table>",
    ]
    if bottom_rows:
        parts.extend([
            "<div style='padding-top:6px;'><b>Bottom 7 traits</b></div>",
            "<table cellspacing='0' cellpadding='0'>",
            *[
                _trait_rank_row(rank, name, pct, color=color_by_name.get(name, DEFAULT_TRAIT_COLOR))
                for rank, (name, pct) in enumerate(bottom_rows, start=1)
            ],
            "</table>",
        ])
    label.setText("".join(parts))
