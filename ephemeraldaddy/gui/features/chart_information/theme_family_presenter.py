"""Narrow Chart Information presenter for semantic Theme predictions.

A click on a macrotheme row opens the standard Chart Info! surface and shows:
* the editable macrotheme label and optional family description,
* every subtheme in the family with its chart score,
* the positively active configured factors that produced that score.

The Theme table stores stable family keys, so presentation labels and taxonomy
membership can evolve without coupling click behavior to rendered text.
"""

from __future__ import annotations

import html
from typing import Any, Mapping

from ephemeraldaddy.analysis.theme_evidence import (
    ThemeFactorEvidence,
    calculate_theme_family_factor_evidence,
    calculate_theme_factor_evidence_from_context,
)
from ephemeraldaddy.analysis.theme_prominence import calculate_theme_subtheme_scores
from ephemeraldaddy.analysis.weighted_chart_predictor import normalize_channel_value
from ephemeraldaddy.core.theme_reference import THEMES, THEME_FAMILIES, themes_in_family
from ephemeraldaddy.gui.style import (
    CHART_DATA_HIGHLIGHT_COLOR,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_SECONDARY,
    appwide_red_green_rgb_for_range,
    set_chart_info_html,
)


def _score_color(value: float) -> str:
    red, green, blue = appwide_red_green_rgb_for_range(float(value), 0.0, 100.0)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _factor_label(property_name: str, item: Any) -> str:
    """Return a concise human-facing label for one Theme evidence item."""

    if property_name == "signs":
        return f"Sign: {item}"
    if property_name == "houses":
        return f"House {item}"
    if property_name == "bodies":
        return f"Body: {item}"
    if property_name == "elements":
        return f"Element: {str(item).title()}"
    if property_name == "modes":
        return f"Mode: {str(item).title()}"
    if property_name == "nakshatras":
        return f"Nakshatra: {item}"
    if property_name == "gates":
        return f"Gate {item}"
    if property_name == "channels":
        channel = normalize_channel_value(item)
        if channel is not None:
            return f"Channel {channel[0]}-{channel[1]}"
        return f"Channel {item}"
    if property_name == "crosses":
        return f"Incarnation Cross: {item}"
    if property_name == "centers":
        return f"{item} Center"
    if property_name == "profiles":
        return f"Profile {item}"
    if property_name == "authorities":
        return f"{item} Authority"
    if property_name == "bazisigns":
        return f"BaZi: {str(item).title()}"
    return f"{property_name.replace('_', ' ').title()}: {item}"


def _evidence_item_html(evidence: ThemeFactorEvidence) -> str:
    activation = max(0.0, min(1.0, float(evidence.activation)))
    activation_pct = activation * 100.0
    color = _score_color(activation_pct)
    label = html.escape(_factor_label(evidence.property_name, evidence.item))
    # ``set_chart_info_html`` subsequently applies canonical semantic colors to
    # recognized signs, bodies, gates, authorities, etc. The activation color
    # remains the fallback/list-marker color and communicates relative strength.
    return (
        f"<li style='margin:2px 0; color:{color};'>"
        f"{label}"
        f" <span style='color:{color};'>({activation_pct:.0f}%)</span>"
        "</li>"
    )


def _subtheme_html(
    theme_key: str,
    score: float | None,
    evidence: tuple[ThemeFactorEvidence, ...],
) -> str:
    theme = THEMES[theme_key]
    label = html.escape(str(theme.get("label", theme_key)).strip() or theme_key)
    if score is None:
        score_html = f"<span style='color:{COLOR_TEXT_MUTED};'>—</span>"
    else:
        bounded_score = max(0.0, min(100.0, float(score)))
        score_html = (
            f"<span style='color:{_score_color(bounded_score)};'>{bounded_score:.1f}%</span>"
        )

    if evidence:
        evidence_html = (
            "<ul style='margin-top:4px; margin-bottom:8px; padding-left:20px;'>"
            + "".join(_evidence_item_html(item) for item in evidence)
            + "</ul>"
        )
    else:
        evidence_html = (
            "<ul style='margin-top:4px; margin-bottom:8px; padding-left:20px;'>"
            f"<li style='margin:2px 0; color:{COLOR_TEXT_MUTED};'>"
            "<i>No configured factors are active above baseline in this chart.</i>"
            "</li></ul>"
        )

    return (
        "<div style='margin-top:12px;'>"
        f"<span style='font-weight:700;'>{label}</span>"
        f" <span style='color:{COLOR_TEXT_SECONDARY};'>—</span> {score_html}"
        "</div>"
        f"{evidence_html}"
    )


def build_theme_family_chart_info_html(
    chart: Any,
    family_key: str,
    *,
    subtheme_scores: Mapping[str, float] | None = None,
    activation_context: Mapping[str, Any] | None = None,
    evidence_by_theme: Mapping[str, tuple[ThemeFactorEvidence, ...]] | None = None,
) -> str:
    """Build the Chart Info HTML for one macrotheme family."""

    if family_key not in THEME_FAMILIES:
        return ""

    family = THEME_FAMILIES[family_key]
    family_label = html.escape(str(family.get("label", family_key)).strip() or family_key)
    description = str(family.get("description", "") or "").strip()
    scores = dict(subtheme_scores or calculate_theme_subtheme_scores(chart))
    if evidence_by_theme is None:
        theme_keys_for_evidence = tuple(themes_in_family(family_key))
        if activation_context is not None:
            evidence_by_theme = calculate_theme_factor_evidence_from_context(
                activation_context, theme_keys_for_evidence
            )
        else:
            evidence_by_theme = calculate_theme_family_factor_evidence(chart, family_key)

    theme_keys = list(themes_in_family(family_key))
    # Strongest subthemes first. Missing/unscorable subthemes remain visible at
    # the end, preserving the requirement that the drill-down shows every one.
    definition_order = {theme_key: index for index, theme_key in enumerate(theme_keys)}
    theme_keys.sort(
        key=lambda theme_key: (
            -(float(scores[theme_key]) if theme_key in scores else -1.0),
            definition_order[theme_key],
        )
    )

    parts = [
        "<div>",
        f"<div style='font-size:16px; font-weight:700; color:{CHART_DATA_HIGHLIGHT_COLOR};'>"
        f"{family_label}</div>",
    ]
    if description:
        parts.append(
            f"<div style='margin-top:4px; color:{COLOR_TEXT_SECONDARY}; font-style:italic;'>"
            f"{html.escape(description)}</div>"
        )

    for theme_key in theme_keys:
        raw_score = scores.get(theme_key)
        score = float(raw_score) if raw_score is not None else None
        parts.append(
            _subtheme_html(
                theme_key,
                score,
                evidence_by_theme.get(theme_key, ()),
            )
        )
    parts.append("</div>")
    return "".join(parts)


def present_theme_family_chart_info(
    *,
    chart: Any,
    family_key: str,
    output: Any,
    set_panel_mode: Any = None,
    subtheme_scores: Mapping[str, float] | None = None,
    activation_context: Mapping[str, Any] | None = None,
    evidence_by_theme: Mapping[str, tuple[ThemeFactorEvidence, ...]] | None = None,
) -> bool:
    """Render one family through explicit Chart Information dependencies."""
    if chart is None or family_key not in THEME_FAMILIES:
        return False
    rendered = build_theme_family_chart_info_html(
        chart,
        family_key,
        subtheme_scores=subtheme_scores,
        activation_context=activation_context,
        evidence_by_theme=evidence_by_theme,
    )
    if not rendered or output is None:
        return False
    if callable(set_panel_mode):
        set_panel_mode("chart_info")
    if hasattr(output, "setHtml") or hasattr(output, "setPlainText"):
        set_chart_info_html(output, rendered)
        return True
    return False
