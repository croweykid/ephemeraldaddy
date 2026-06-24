"""Chart View custom trait prediction rendering helpers."""

from __future__ import annotations

import html
from typing import Any

from PySide6.QtWidgets import QLabel

from ephemeraldaddy.analysis.traits import calculate_trait_scores, list_traits


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
        scores = calculate_trait_scores(chart, traits)
    except Exception as exc:
        label.setText(f"Trait predictions unavailable: {html.escape(str(exc))}")
        return
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    rows = [f"<b>{html.escape(name)}</b>: {score:.2f}" for name, score in ranked]
    label.setText("<br>".join(rows) if rows else "No scorable traits uploaded.")
