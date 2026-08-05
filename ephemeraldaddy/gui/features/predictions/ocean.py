"""Chart Editor OCEAN personality prediction presentation."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtWidgets import QLabel

from ephemeraldaddy.analysis.oceanpredictor import OCEAN_BODIES, OCEAN_HOUSES, OCEAN_NAKSHATRAS, OCEAN_SIGNS
from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_house_weights,
    calculate_dominant_nakshatra_weights,
    calculate_dominant_planet_weights,
    calculate_dominant_sign_weights,
)
from ephemeraldaddy.gui.features.charts.prediction_loading_labels import stop_prediction_loading_blink

OCEAN_TRAITS = ("O", "C", "E", "A", "N")
OCEAN_AXIS_LABELS = {
    "O": ("Open", "Conservative"),
    "C": ("Conscientious", "Slack"),
    "E": ("Extraverted", "Introverted"),
    "A": ("Agreeable", "Disagreeable"),
    "N": ("Neurotic", "Stable"),
}
OCEAN_GRAPH_HEIGHT_PX = 260
OCEAN_NEUTRAL_SCORE = 5.0


def _weighted_trait_average(weights: dict[Any, float], factors: dict[Any, dict[str, Any]]) -> dict[str, float]:
    totals = {trait: 0.0 for trait in OCEAN_TRAITS}
    total_weight = 0.0
    for key, raw_weight in (weights or {}).items():
        factor = factors.get(key)
        if not isinstance(factor, dict):
            factor = factors.get(str(key))
        if not isinstance(factor, dict):
            continue
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            continue
        if weight <= 0:
            continue
        for trait in OCEAN_TRAITS:
            try:
                totals[trait] += weight * float(factor.get(trait, OCEAN_NEUTRAL_SCORE))
            except (TypeError, ValueError):
                totals[trait] += weight * OCEAN_NEUTRAL_SCORE
        total_weight += weight
    if total_weight <= 0:
        return {trait: OCEAN_NEUTRAL_SCORE for trait in OCEAN_TRAITS}
    return {trait: totals[trait] / total_weight for trait in OCEAN_TRAITS}


def calculate_ocean_scores(chart: Any | None) -> dict[str, float]:
    """Return centered -5..+5 OCEAN axis scores for a chart's dominance weights."""
    if chart is None:
        return {trait: 0.0 for trait in OCEAN_TRAITS}
    category_scores = [
        _weighted_trait_average(
            getattr(chart, "dominant_sign_weights", None) or calculate_dominant_sign_weights(chart),
            OCEAN_SIGNS,
        ),
        _weighted_trait_average(
            getattr(chart, "dominant_planet_weights", None) or calculate_dominant_planet_weights(chart),
            OCEAN_BODIES,
        ),
    ]
    category_scores.append(
        _weighted_trait_average(
            getattr(chart, "dominant_nakshatra_weights", None) or calculate_dominant_nakshatra_weights(chart),
            OCEAN_NAKSHATRAS,
        )
    )
    if chart_uses_houses(chart):
        category_scores.append(_weighted_trait_average(calculate_dominant_house_weights(chart), OCEAN_HOUSES))
    averaged = {
        trait: sum(category[trait] for category in category_scores) / max(1, len(category_scores))
        for trait in OCEAN_TRAITS
    }
    return {trait: averaged[trait] - OCEAN_NEUTRAL_SCORE for trait in OCEAN_TRAITS}


class OceanPredictionPanelAdapter:
    """Render Chart Editor OCEAN predictions as positive/negative axis bars."""

    def __init__(self, *, chart_layout: Any, label: QLabel | None, chart_theme_colors: dict[str, str], is_placeholder_chart: Callable[[Any], bool]) -> None:
        self.chart_layout = chart_layout
        self.label = label
        self.chart_theme_colors = chart_theme_colors
        self.is_placeholder_chart = is_placeholder_chart

    def draw(self, ax: Any, chart: Any | None) -> None:
        ax.clear()
        ax.set_facecolor(self.chart_theme_colors.get("background", "#111111"))
        scores = calculate_ocean_scores(chart)
        labels = list(OCEAN_TRAITS)
        values = [scores[trait] for trait in labels]
        colors = ["#34d399" if value >= 0 else "#f87171" for value in values]
        ax.bar(labels, values, color=colors)
        ax.axhline(0, color="#d8c8ff", linewidth=1)
        ax.set_ylim(-5, 5)
        ax.set_ylabel("Axis score")
        ax.tick_params(colors=self.chart_theme_colors.get("text", "#eeeeee"))
        ax.yaxis.label.set_color(self.chart_theme_colors.get("text", "#eeeeee"))
        for spine in ax.spines.values():
            spine.set_color("#5b4b7a")
        for index, trait in enumerate(labels):
            positive, negative = OCEAN_AXIS_LABELS[trait]
            value = values[index]
            va = "bottom" if value >= 0 else "top"
            y = value + (0.2 if value >= 0 else -0.2)
            ax.text(index, y, f"{positive if value >= 0 else negative}\n{value:+.2f}", ha="center", va=va, color=self.chart_theme_colors.get("text", "#eeeeee"), fontsize=8)

    def render(self, chart: Any | None, metric_panel_renderer: Callable[..., Any]) -> None:
        if self.chart_layout is None:
            return
        metric_panel_renderer(
            canvas_attr="ocean_prediction_canvas",
            container_layout=self.chart_layout,
            figsize=(5.5, 2.8),
            title="OCEAN Personality Predictor",
            draw_fn=self.draw,
            chart=chart,
            display_height=OCEAN_GRAPH_HEIGHT_PX,
        )
        if self.label is not None:
            stop_prediction_loading_blink(self.label)
            houses_text = "including house weights" if chart is not None and chart_uses_houses(chart) else "excluding house weights"
            self.label.setText(f"OCEAN dominance predictor ({houses_text}). Positive/negative axes: Open/Conservative, Conscientious/Slack, Extraverted/Introverted, Agreeable/Disagreeable, Neurotic/Stable.")
