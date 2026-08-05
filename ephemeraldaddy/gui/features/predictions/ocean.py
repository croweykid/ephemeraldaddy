"""Chart Editor OCEAN personality prediction presentation."""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from PySide6.QtWidgets import QLabel
else:
    QLabel = Any

from ephemeraldaddy.analysis.oceanpredictor import (
    OCEAN_BODIES,
    OCEAN_HOUSES,
    OCEAN_NAKSHATRAS,
    OCEAN_SIGNS,
)
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
    "O": ("Conventionality", "Openness"),
    "C": ("Casualness", "Conscientiousness"),
    "E": ("Introversion", "Extraversion"),
    "A": ("Abrasiveness", "Agreeableness"),
    "N": ("Stability", "Neuroticism"),
}
OCEAN_GRAPH_HEIGHT_PX = 320
OCEAN_MIN_SCORE = -10.0
OCEAN_MAX_SCORE = 10.0
LEGACY_OCEAN_NEUTRAL_SCORE = 5.0
OCEAN_POP_OUT_TITLE = "OCEAN Personality Predictor"

OCEAN_TRAIT_NAMES = {
    "O": "Openness",
    "C": "Conscientiousness",
    "E": "Extraversion",
    "A": "Agreeableness",
    "N": "Neuroticism",
}
OCEAN_TRAIT_EXPLAINERS = {
    "O": (
        "Openness tracks appetite for novelty, symbolism, complexity, aesthetic play, "
        "and imaginative range."
    ),
    "C": (
        "Conscientiousness tracks structure, follow-through, duty, precision, and preference "
        "for ordered plans."
    ),
    "E": (
        "Extraversion tracks outward activation, expressiveness, social charge, and comfort "
        "with direct engagement."
    ),
    "A": (
        "Agreeableness tracks cooperation, warmth, accommodation, softness, and relational "
        "ease."
    ),
    "N": (
        "Neuroticism tracks emotional sensitivity, volatility, threat scanning, and nervous "
        "system reactivity."
    ),
}


def _score_band(score: float) -> str:
    magnitude = abs(score)
    if magnitude >= 7.0:
        return "strong"
    if magnitude >= 3.0:
        return "moderate"
    if magnitude > 0.0:
        return "subtle"
    return "neutral"


def _score_direction(trait: str, score: float) -> str:
    negative_label, positive_label = OCEAN_AXIS_LABELS.get(trait, ("Low pole", "High pole"))
    if score > 0:
        return positive_label
    if score < 0:
        return negative_label
    return "Neutral"


def _factor_table_uses_centered_scores(factors: dict[Any, dict[str, Any]]) -> bool:
    for factor in factors.values():
        if not isinstance(factor, dict):
            continue
        for trait in OCEAN_TRAITS:
            try:
                if float(factor.get(trait, 0.0)) < 0:
                    return True
            except (TypeError, ValueError):
                continue
    return False


def _coerce_ocean_factor_score(value: Any, *, centered_scores: bool) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0 if centered_scores else LEGACY_OCEAN_NEUTRAL_SCORE
    if not centered_scores:
        score = (score - LEGACY_OCEAN_NEUTRAL_SCORE) * 2.0
    return max(OCEAN_MIN_SCORE, min(OCEAN_MAX_SCORE, score))


def _weighted_trait_average(
    weights: dict[Any, float],
    factors: dict[Any, dict[str, Any]],
) -> dict[str, float]:
    centered_scores = _factor_table_uses_centered_scores(factors)
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
            totals[trait] += weight * _coerce_ocean_factor_score(
                factor.get(trait),
                centered_scores=centered_scores,
            )
        total_weight += weight
    if total_weight <= 0:
        return {trait: 0.0 for trait in OCEAN_TRAITS}
    return {trait: totals[trait] / total_weight for trait in OCEAN_TRAITS}


def calculate_ocean_scores(chart: Any | None) -> dict[str, float]:
    """Return centered -10..+10 OCEAN spectrum scores for a chart's dominance weights."""
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
    return {trait: max(OCEAN_MIN_SCORE, min(OCEAN_MAX_SCORE, averaged[trait])) for trait in OCEAN_TRAITS}


def ocean_scores_to_mbti(scores: dict[str, float]) -> str:
    """Translate OCEAN spectra into an MBTI-style four-letter code."""
    axes = (
        ("E", "E", "I"),
        ("O", "N", "S"),
        ("A", "F", "T"),
        ("C", "J", "P"),
    )
    letters: list[str] = []
    for trait, high_letter, low_letter in axes:
        try:
            score = float(scores.get(trait, 0.0))
        except (TypeError, ValueError):
            score = 0.0
        if score == 0.0:
            letters.append("x")
            continue
        letter = high_letter if score > 0.0 else low_letter
        if abs(score) <= 3.0:
            letter = letter.lower()
        letters.append(letter)
    return "".join(letters)


def draw_ocean_prediction_bars(
    ax: Any,
    chart: Any | None,
    *,
    chart_theme_colors: dict[str, str],
) -> None:
    """Draw OCEAN horizontal spectrum bars with pickable trait artists."""
    ax.clear()
    ax.set_facecolor(chart_theme_colors.get("background", "#111111"))
    scores = calculate_ocean_scores(chart)
    labels = list(OCEAN_TRAITS)
    values = [scores[trait] for trait in labels]
    colors = ["#34d399" if value >= 0 else "#f87171" for value in values]
    bars = ax.barh(labels, values, color=colors)
    for bar, trait in zip(bars, labels, strict=True):
        bar.set_gid(f"ocean:{trait}")
        bar.set_picker(True)
    ax.axvline(0, color="#d8c8ff", linewidth=1.2)
    ax.set_xlim(OCEAN_MIN_SCORE, OCEAN_MAX_SCORE)
    ax.set_xlabel("Spectrum score")
    ax.tick_params(colors=chart_theme_colors.get("text", "#eeeeee"))
    ax.xaxis.label.set_color(chart_theme_colors.get("text", "#eeeeee"))
    ax.grid(axis="x", color="#5b4b7a", alpha=0.35, linewidth=0.6)
    for spine in ax.spines.values():
        spine.set_color("#5b4b7a")
    for tick_label, trait in zip(ax.get_yticklabels(), labels, strict=True):
        tick_label.set_gid(f"ocean:{trait}")
        tick_label.set_picker(True)
    for index, trait in enumerate(labels):
        negative_label, positive_label = OCEAN_AXIS_LABELS[trait]
        left_label = ax.text(
            OCEAN_MIN_SCORE,
            index,
            negative_label,
            ha="left",
            va="center",
            color="#fca5a5",
            fontsize=8,
        )
        left_label.set_gid(f"ocean:{trait}")
        left_label.set_picker(True)
        right_label = ax.text(
            OCEAN_MAX_SCORE,
            index,
            positive_label,
            ha="right",
            va="center",
            color="#86efac",
            fontsize=8,
        )
        right_label.set_gid(f"ocean:{trait}")
        right_label.set_picker(True)
        value = values[index]
        ha = "left" if value >= 0 else "right"
        x = value + (0.35 if value >= 0 else -0.35)
        value_label = ax.text(
            x,
            index,
            f"{value:+.2f}",
            ha=ha,
            va="center",
            color=chart_theme_colors.get("text", "#eeeeee"),
            fontsize=8,
            fontweight="bold",
        )
        value_label.set_gid(f"ocean:{trait}")
        value_label.set_picker(True)
    ax.figure.tight_layout()


def build_ocean_trait_popout_info(chart: Any | None, trait: str) -> str:
    """Return the popout Chart Info explainer for one OCEAN bar."""
    trait_key = str(trait or "").strip().upper()
    if trait_key not in OCEAN_TRAITS:
        return build_ocean_summary_popout_info(chart)
    scores = calculate_ocean_scores(chart)
    score = float(scores.get(trait_key, 0.0))
    negative_label, positive_label = OCEAN_AXIS_LABELS[trait_key]
    direction = _score_direction(trait_key, score)
    band = _score_band(score)
    mbti = ocean_scores_to_mbti(scores)
    houses_text = "included" if chart is not None and chart_uses_houses(chart) else "excluded"
    return (
        f"<h2>{escape(OCEAN_TRAIT_NAMES[trait_key])} ({trait_key})</h2>"
        f"<p><b>Score:</b> {score:+.2f} / 10 — {escape(band)} lean toward "
        f"<b>{escape(direction)}</b>.</p>"
        f"<p><b>Axis:</b> {escape(negative_label)} ← 0 → {escape(positive_label)}</p>"
        f"<p>{escape(OCEAN_TRAIT_EXPLAINERS[trait_key])}</p>"
        f"<p><b>Interpretation:</b> Positive bars emphasize {escape(positive_label.lower())}; "
        f"negative bars emphasize {escape(negative_label.lower())}; near-zero bars imply a flexible "
        "or context-dependent expression rather than a fixed trait signature.</p>"
        f"<p><b>MBTI bridge:</b> Current translation is <b>{escape(mbti)}</b>. "
        "O maps to N/S, C to J/P, E to E/I, and A to F/T. Scores within 3 points "
        "of neutral are shown lowercase.</p>"
        f"<p><b>Inputs:</b> Sign, body, and nakshatra dominance weights are used; house weights are "
        f"{escape(houses_text)} according to this chart's chart_uses_houses value.</p>"
    )


def build_ocean_summary_popout_info(chart: Any | None) -> str:
    """Return the default OCEAN popout explainer before a specific bar is picked."""
    scores = calculate_ocean_scores(chart)
    mbti = ocean_scores_to_mbti(scores)
    rows = "".join(
        f"<li><b>{trait}</b>: {scores[trait]:+.2f} toward {escape(_score_direction(trait, scores[trait]))}</li>"
        for trait in OCEAN_TRAITS
    )
    houses_text = "included" if chart is not None and chart_uses_houses(chart) else "excluded"
    return (
        "<h2>OCEAN Personality Predictor</h2>"
        f"<p><b>MBTI translation:</b> {escape(mbti)}</p>"
        "<p>Click any bar or axis label for a trait-specific interpretation.</p>"
        f"<ul>{rows}</ul>"
        f"<p>House weights are {escape(houses_text)} for this chart.</p>"
    )


class OceanPredictionPanelAdapter:
    """Render Chart Editor OCEAN predictions as horizontal spectrum bars."""

    def __init__(
        self,
        *,
        chart_layout: Any,
        label: QLabel | None,
        chart_theme_colors: dict[str, str],
        is_placeholder_chart: Callable[[Any], bool],
    ) -> None:
        self.chart_layout = chart_layout
        self.label = label
        self.chart_theme_colors = chart_theme_colors
        self.is_placeholder_chart = is_placeholder_chart

    def draw(self, ax: Any, chart: Any | None) -> None:
        draw_ocean_prediction_bars(ax, chart, chart_theme_colors=self.chart_theme_colors)

    def render(self, chart: Any | None, metric_panel_renderer: Callable[..., Any]) -> None:
        if self.chart_layout is None:
            return
        metric_panel_renderer(
            canvas_attr="ocean_prediction_canvas",
            container_layout=self.chart_layout,
            figsize=(5.5, 2.8),
            title=OCEAN_POP_OUT_TITLE,
            draw_fn=self.draw,
            chart=chart,
            display_height=OCEAN_GRAPH_HEIGHT_PX,
        )
        if self.label is not None:
            stop_prediction_loading_blink(self.label)
            houses_text = (
                "including house weights"
                if chart is not None and chart_uses_houses(chart)
                else "excluding house weights"
            )
            mbti = ocean_scores_to_mbti(calculate_ocean_scores(chart))
            self.label.setText(
                f"<b>MBTI: {mbti}</b><br>"
                f"OCEAN dominance predictor ({houses_text}). Horizontal spectra run from -10 to +10 "
                "with 0 as neutral: Openness/Conventionality, Conscientiousness/Casualness, "
                "Extraversion/Introversion, Agreeableness/Abrasiveness, Neuroticism/Stability. "
                "MBTI translation uses E→E/I, O→N/S, A→F/T, and C→J/P; exact neutral is x, "
                "and scores within 3 points of neutral are lowercase."
            )
