"""Chart Editor OCEAN personality prediction presentation."""

from __future__ import annotations

import html

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
OCEAN_TRAIT_NAMES = {
    "O": "Openness",
    "C": "Conscientiousness",
    "E": "Extraversion",
    "A": "Agreeableness",
    "N": "Neuroticism",
}
OCEAN_TRAIT_EXPLAINERS = {
    "O": (
        "More exploratory, imaginative, novelty-seeking, symbolically curious, and receptive to unusual perspectives.",
        "More conventional, concrete, familiar-patterned, tradition-aware, and cautious about novelty.",
    ),
    "C": (
        "More structured, diligent, self-regulating, planful, and completion-oriented.",
        "More casual, spontaneous, flexible, distractible, and resistant to rigid duty cycles.",
    ),
    "E": (
        "More expressive, socially energized, externally active, visible, and momentum-seeking.",
        "More introverted, inwardly focused, selective with stimulation, private, and energy-conserving.",
    ),
    "A": (
        "More cooperative, conciliatory, empathic, warm, and relationship-preserving.",
        "More abrasive, skeptical, combative, blunt, and willing to prioritize friction over harmony.",
    ),
    "N": (
        "More reactive, sensitive to threat or uncertainty, emotionally porous, and stress-responsive.",
        "More stable, even-keeled, composed under pressure, emotionally contained, and threat-buffered.",
    ),
}
OCEAN_GRAPH_HEIGHT_PX = 320
OCEAN_MIN_SCORE = -10.0
OCEAN_MAX_SCORE = 10.0
LEGACY_OCEAN_NEUTRAL_SCORE = 5.0


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


def _score_intensity(score: float) -> str:
    magnitude = abs(score)
    if magnitude == 0.0:
        return "neutral"
    if magnitude <= 3.0:
        return "slight"
    if magnitude <= 6.0:
        return "moderate"
    return "strong"


def build_ocean_popout_info_html(chart: Any | None, trait: str | None = None) -> str:
    """Build Chart Info HTML for the OCEAN metric popout."""
    scores = calculate_ocean_scores(chart)
    mbti = ocean_scores_to_mbti(scores)
    houses_text = "included" if chart is not None and chart_uses_houses(chart) else "excluded"
    header = (
        "<h2>OCEAN Personality Predictor</h2>"
        f"<p><b>MBTI:</b> {html.escape(mbti)}</p>"
        "<p>Scores run from <b>-10</b> to <b>+10</b>, with <b>0</b> as neutral. "
        f"House weights are <b>{houses_text}</b> for this chart.</p>"
    )
    if trait in OCEAN_TRAITS:
        score = float(scores.get(str(trait), 0.0))
        negative_label, positive_label = OCEAN_AXIS_LABELS[str(trait)]
        positive_explainer, negative_explainer = OCEAN_TRAIT_EXPLAINERS[str(trait)]
        leaning = positive_label if score > 0 else negative_label if score < 0 else "Neutral"
        if score > 0:
            explainer = positive_explainer
        elif score < 0:
            explainer = negative_explainer
        else:
            explainer = (
                "This axis is exactly neutral in the current weighted blend; "
                "the MBTI translation uses x for this letter."
            )
        return (
            header
            + f"<h3>{html.escape(OCEAN_TRAIT_NAMES[str(trait)])}: {score:+.2f}</h3>"
            f"<p><b>Spectrum:</b> {html.escape(negative_label)} ← 0 → {html.escape(positive_label)}</p>"
            f"<p><b>Leaning:</b> {html.escape(_score_intensity(score).title())} {html.escape(leaning)}</p>"
            f"<p>{html.escape(explainer)}</p>"
        )
    rows = []
    for trait_key in OCEAN_TRAITS:
        score = float(scores.get(trait_key, 0.0))
        negative_label, positive_label = OCEAN_AXIS_LABELS[trait_key]
        leaning = positive_label if score > 0 else negative_label if score < 0 else "Neutral"
        rows.append(
            "<tr>"
            f"<td><b>{html.escape(trait_key)}</b></td>"
            f"<td>{html.escape(OCEAN_TRAIT_NAMES[trait_key])}</td>"
            f"<td>{score:+.2f}</td>"
            f"<td>{html.escape(_score_intensity(score).title())} {html.escape(leaning)}</td>"
            "</tr>"
        )
    return (
        header
        + "<p>Click an OCEAN spectrum bar or axis label to see what that specific score implies.</p>"
        "<table border='1' cellspacing='0' cellpadding='4'>"
        "<tr><th>Axis</th><th>Trait</th><th>Score</th><th>Reading</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def connect_ocean_popout_pick_handler(canvas: Any, info_panel: Any, *, chart: Any | None) -> None:
    """Connect OCEAN bar/label clicks to detailed Chart Info text."""
    if hasattr(info_panel, "setHtml"):
        info_panel.setHtml(build_ocean_popout_info_html(chart))

    def _on_pick(event: object) -> None:
        artist = getattr(event, "artist", None)
        artist_gid = artist.get_gid() if artist is not None and hasattr(artist, "get_gid") else None
        if not isinstance(artist_gid, str) or not artist_gid.startswith("ocean:"):
            return
        _prefix, trait = artist_gid.split(":", 1)
        if trait not in OCEAN_TRAITS or not hasattr(info_panel, "setHtml"):
            return
        info_panel.setHtml(build_ocean_popout_info_html(chart, trait))

    canvas.mpl_connect("pick_event", _on_pick)


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
        ax.clear()
        ax.set_facecolor(self.chart_theme_colors.get("background", "#111111"))
        scores = calculate_ocean_scores(chart)
        labels = list(OCEAN_TRAITS)
        values = [scores[trait] for trait in labels]
        colors = ["#34d399" if value >= 0 else "#f87171" for value in values]
        bars = ax.barh(labels, values, color=colors)
        for bar, trait in zip(bars, labels):
            bar.set_gid(f"ocean:{trait}")
            bar.set_picker(True)
        ax.axvline(0, color="#d8c8ff", linewidth=1.2)
        ax.set_xlim(OCEAN_MIN_SCORE, OCEAN_MAX_SCORE)
        ax.set_xlabel("Spectrum score")
        ax.tick_params(colors=self.chart_theme_colors.get("text", "#eeeeee"))
        ax.xaxis.label.set_color(self.chart_theme_colors.get("text", "#eeeeee"))
        ax.grid(axis="x", color="#5b4b7a", alpha=0.35, linewidth=0.6)
        for spine in ax.spines.values():
            spine.set_color("#5b4b7a")
        for tick_label, trait in zip(ax.get_yticklabels(), labels):
            tick_label.set_gid(f"ocean:{trait}")
            tick_label.set_picker(True)
        for index, trait in enumerate(labels):
            negative_label, positive_label = OCEAN_AXIS_LABELS[trait]
            negative_text = ax.text(
                OCEAN_MIN_SCORE,
                index,
                negative_label,
                ha="left",
                va="center",
                color="#fca5a5",
                fontsize=8,
            )
            negative_text.set_gid(f"ocean:{trait}")
            negative_text.set_picker(True)
            positive_text = ax.text(
                OCEAN_MAX_SCORE,
                index,
                positive_label,
                ha="right",
                va="center",
                color="#86efac",
                fontsize=8,
            )
            positive_text.set_gid(f"ocean:{trait}")
            positive_text.set_picker(True)
            value = values[index]
            ha = "left" if value >= 0 else "right"
            x = value + (0.35 if value >= 0 else -0.35)
            ax.text(
                x,
                index,
                f"{value:+.2f}",
                ha=ha,
                va="center",
                color=self.chart_theme_colors.get("text", "#eeeeee"),
                fontsize=8,
                fontweight="bold",
            )

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
