"""Chart Information presenter for semantic Theme predictions.

Macrotheme clicks show the family and its subthemes. Subtheme clicks show only
the selected subtheme. Numeric labels use chart-share percentages and empirical
DB percentiles; the scorer's internal chart-normalized activations are never
presented as percentages to the user.
"""

from __future__ import annotations

import html
from typing import Any, Mapping

from ephemeraldaddy.analysis.theme_evidence import (
    ThemeFactorEvidence,
    calculate_theme_family_factor_evidence,
    calculate_theme_factor_evidence_from_context,
)
from ephemeraldaddy.analysis.theme_norms import (
    empirical_percentile,
    format_theme_percentile,
    theme_factor_distribution_key,
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


def _theme_description(theme: Mapping[str, Any]) -> str:
    value = theme.get("description", "")
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, tuple)):
        return " ".join(str(item).strip() for item in value if str(item).strip())
    return ""


def _factor_percentile(
    evidence: ThemeFactorEvidence,
    factor_values: Mapping[str, Any],
) -> float | None:
    key = theme_factor_distribution_key(evidence.property_name, evidence.item)
    samples = factor_values.get(key, ())
    if not isinstance(samples, (list, tuple)):
        return None
    return empirical_percentile(float(evidence.activation), samples)


def _evidence_item_html(
    evidence: ThemeFactorEvidence,
    factor_values: Mapping[str, Any],
) -> str:
    percentile = _factor_percentile(evidence, factor_values)
    label = html.escape(_factor_label(evidence.property_name, evidence.item))
    if percentile is None:
        suffix = ""
        color = COLOR_TEXT_SECONDARY
    else:
        color = _score_color(percentile)
        suffix = (
            " <span style='color:"
            f"{color};'>({html.escape(format_theme_percentile(percentile))} vs DB)</span>"
        )
    return f"<li style='margin:2px 0; color:{color};'>{label}{suffix}</li>"


def _share_percentile_html(
    share: float | None,
    samples: Any,
) -> str:
    if share is None:
        return f"<span style='color:{COLOR_TEXT_MUTED};'>—</span>"
    percentile = empirical_percentile(share, samples if isinstance(samples, (list, tuple)) else ())
    share_text = f"{float(share):.1f}% of chart"
    if percentile is None:
        return f"<span style='color:{CHART_DATA_HIGHLIGHT_COLOR};'>{share_text}</span>"
    color = _score_color(percentile)
    return (
        f"<span style='color:{CHART_DATA_HIGHLIGHT_COLOR};'>{share_text}</span>"
        f" <span style='color:{COLOR_TEXT_SECONDARY};'>·</span> "
        f"<span style='color:{color};'>{html.escape(format_theme_percentile(percentile))} vs DB</span>"
    )


def _subtheme_html(
    theme_key: str,
    share: float | None,
    evidence: tuple[ThemeFactorEvidence, ...],
    *,
    share_samples: Any = (),
    factor_values: Mapping[str, Any] | None = None,
    heading: bool = False,
) -> str:
    theme = THEMES[theme_key]
    label = html.escape(str(theme.get("label", theme_key)).strip() or theme_key)
    description = _theme_description(theme)
    metrics = _share_percentile_html(share, share_samples)
    factor_rows = factor_values if isinstance(factor_values, Mapping) else {}

    if evidence:
        evidence_html = (
            "<ul style='margin-top:4px; margin-bottom:8px; padding-left:20px;'>"
            + "".join(_evidence_item_html(item, factor_rows) for item in evidence)
            + "</ul>"
        )
    else:
        evidence_html = (
            "<ul style='margin-top:4px; margin-bottom:8px; padding-left:20px;'>"
            f"<li style='margin:2px 0; color:{COLOR_TEXT_MUTED};'>"
            "<i>No configured factors are active above baseline in this chart.</i>"
            "</li></ul>"
        )

    if heading:
        title_html = (
            f"<div style='font-size:16px; font-weight:700; color:{CHART_DATA_HIGHLIGHT_COLOR};'>"
            f"{label}</div>"
            f"<div style='margin-top:4px;'>{metrics}</div>"
        )
    else:
        title_html = (
            "<div style='margin-top:12px;'>"
            f"<span style='font-weight:700;'>{label}</span>"
            f" <span style='color:{COLOR_TEXT_SECONDARY};'>—</span> {metrics}"
            "</div>"
        )

    description_html = ""
    if description:
        description_html = (
            f"<div style='margin-top:4px; color:{COLOR_TEXT_SECONDARY}; font-style:italic;'>"
            f"{html.escape(description)}</div>"
        )
    return title_html + description_html + evidence_html


def build_theme_family_chart_info_html(
    chart: Any,
    family_key: str,
    *,
    theme_key: str | None = None,
    subtheme_scores: Mapping[str, float] | None = None,
    subtheme_shares: Mapping[str, float] | None = None,
    family_shares: Mapping[str, float] | None = None,
    share_norms: Mapping[str, Any] | None = None,
    activation_context: Mapping[str, Any] | None = None,
    evidence_by_theme: Mapping[str, tuple[ThemeFactorEvidence, ...]] | None = None,
) -> str:
    """Build Chart Info HTML for one macrotheme or one selected subtheme."""
    if family_key not in THEME_FAMILIES:
        return ""
    family_theme_keys = list(themes_in_family(family_key))
    if theme_key is not None and theme_key not in family_theme_keys:
        return ""

    # Retain the legacy score input only as a source for determining which themes
    # are scorable; raw prominence percentages are intentionally not displayed.
    _ = dict(subtheme_scores or calculate_theme_subtheme_scores(chart))
    shares = dict(subtheme_shares or {})
    family_share_rows = dict(family_shares or {})
    norms = dict(share_norms or {})
    subtheme_values = norms.get("subtheme_values", {})
    family_values = norms.get("family_values", {})
    factor_values = norms.get("factor_values", {})
    if not isinstance(subtheme_values, Mapping):
        subtheme_values = {}
    if not isinstance(family_values, Mapping):
        family_values = {}
    if not isinstance(factor_values, Mapping):
        factor_values = {}

    if evidence_by_theme is None:
        requested = (theme_key,) if theme_key is not None else tuple(family_theme_keys)
        if activation_context is not None:
            evidence_by_theme = calculate_theme_factor_evidence_from_context(
                activation_context, requested
            )
        elif theme_key is None:
            evidence_by_theme = calculate_theme_family_factor_evidence(chart, family_key)
        else:
            from ephemeraldaddy.analysis.theme_evidence import calculate_theme_factor_evidence

            evidence_by_theme = calculate_theme_factor_evidence(chart, requested)

    if theme_key is not None:
        return (
            "<div>"
            + _subtheme_html(
                theme_key,
                float(shares[theme_key]) if theme_key in shares else None,
                evidence_by_theme.get(theme_key, ()),
                share_samples=subtheme_values.get(theme_key, ()),
                factor_values=factor_values,
                heading=True,
            )
            + "</div>"
        )

    family = THEME_FAMILIES[family_key]
    family_label = html.escape(str(family.get("label", family_key)).strip() or family_key)
    description = str(family.get("description", "") or "").strip()
    family_share = float(family_share_rows[family_key]) if family_key in family_share_rows else None
    family_metrics = _share_percentile_html(
        family_share,
        family_values.get(family_key, ()),
    )

    definition_order = {key: index for index, key in enumerate(family_theme_keys)}
    family_theme_keys.sort(
        key=lambda key: (
            -(float(shares[key]) if key in shares else -1.0),
            definition_order[key],
        )
    )

    parts = [
        "<div>",
        f"<div style='font-size:16px; font-weight:700; color:{CHART_DATA_HIGHLIGHT_COLOR};'>"
        f"{family_label}</div>",
        f"<div style='margin-top:4px;'>{family_metrics}</div>",
    ]
    if description:
        parts.append(
            f"<div style='margin-top:4px; color:{COLOR_TEXT_SECONDARY}; font-style:italic;'>"
            f"{html.escape(description)}</div>"
        )

    for child_key in family_theme_keys:
        parts.append(
            _subtheme_html(
                child_key,
                float(shares[child_key]) if child_key in shares else None,
                evidence_by_theme.get(child_key, ()),
                share_samples=subtheme_values.get(child_key, ()),
                factor_values=factor_values,
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
    theme_key: str | None = None,
    subtheme_scores: Mapping[str, float] | None = None,
    subtheme_shares: Mapping[str, float] | None = None,
    family_shares: Mapping[str, float] | None = None,
    share_norms: Mapping[str, Any] | None = None,
    activation_context: Mapping[str, Any] | None = None,
    evidence_by_theme: Mapping[str, tuple[ThemeFactorEvidence, ...]] | None = None,
) -> bool:
    """Render one family or selected subtheme through Chart Information."""
    if chart is None or family_key not in THEME_FAMILIES:
        return False
    rendered = build_theme_family_chart_info_html(
        chart,
        family_key,
        theme_key=theme_key,
        subtheme_scores=subtheme_scores,
        subtheme_shares=subtheme_shares,
        family_shares=family_shares,
        share_norms=share_norms,
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
