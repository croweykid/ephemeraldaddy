"""Body Dynamics popout info rendering helpers."""

from __future__ import annotations

import html
from typing import Any

from ephemeraldaddy.core.interpretations import (
    ASPECT_COLORS,
    ASPECT_SCORE_WEIGHTS,
    PLANET_COLORS,
    INNER_PLANETS,
    OUTER_PLANETS,
    PLANET_ORDER,
    aspect_orb_allowance,
)
from ephemeraldaddy.analysis.body_dynamics_reworked import (
    BODY_PAIR_DYNAMICS,
    PAIR_TYPE_DISTRIBUTION,
    normalize_body_pair,
)
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_planet_condition_weights,
    calculate_planet_dynamics_scores,
    classify_body_dynamics,
    normalize_body_name,
)
from ephemeraldaddy.gui.features.charts.text_summary import _display_body_name


def build_body_dynamics_popout_info_html(
    chart: Any,
    metric: str,
    target_body: str,
    *,
    chart_data_highlight_color: str,
    chart_theme_colors: dict[str, str],
    planet_dynamics_bar_colors: dict[str, str],
) -> str:
    metric_key = str(metric or "").strip().lower()
    target_key = str(target_body or "").strip()
    metric_label_map = {"antagonizing": "Antagonizing", "enabling": "Enabling", "escalating": "Escalating"}
    metric_label = metric_label_map.get(metric_key, metric_key.title() or "Dynamics")
    scores = getattr(chart, "planet_dynamics_scores", None) or calculate_planet_dynamics_scores(chart)
    if target_key == "all":
        return "Click a colored planet segment to view that body's score breakdown."

    body_scores = scores.get(target_key) or {"antagonizing": 0.0, "enabling": 0.0, "escalating": 0.0}
    metric_total = float(body_scores.get(metric_key, 0.0))
    body_total = sum(float(body_scores.get(k, 0.0)) for k in ("antagonizing", "enabling", "escalating"))
    share = (metric_total / body_total * 100.0) if body_total > 0 else 0.0
    metric_chart_total = sum(float((scores.get(body) or {}).get(metric_key, 0.0)) for body in scores)
    influence_share = (metric_total / metric_chart_total * 100.0) if metric_chart_total > 0 else 0.0
    condition_weights = calculate_planet_condition_weights(chart)


    tracked_bodies = {body for body in PLANET_ORDER if body in (INNER_PLANETS | OUTER_PLANETS) and body in chart.positions}
    rows = []
    for aspect in getattr(chart, "aspects", []) or []:
        p1 = normalize_body_name(str(aspect.get("p1", "")))
        p2 = normalize_body_name(str(aspect.get("p2", "")))
        if (
            target_key not in {p1, p2}
            or p1 not in tracked_bodies
            or p2 not in tracked_bodies
        ):
            continue
        key = normalize_body_pair(p1, p2)
        tone = BODY_PAIR_DYNAMICS.get(key)
        distribution = (PAIR_TYPE_DISTRIBUTION.get(key) or {}).get(str(aspect.get("type", "")).replace(" ", "_").lower())
        if not distribution:
            continue
        aspect_type = str(aspect.get("type", "")).replace(" ", "_").lower()
        allowance = aspect_orb_allowance(str(aspect.get("type", "")), p1, p2)
        orb = abs(float(aspect.get("delta", 0.0)))
        orb_weight = max(0.0, 1.0 - ((orb / allowance) ** 2)) if allowance > 0 else 0.0
        base = float(ASPECT_SCORE_WEIGHTS.get(aspect_type, 0.0))
        if orb_weight <= 0 or base <= 0:
            continue
        cw1 = max(float(condition_weights.get(p1, 0.0)), 0.0)
        cw2 = max(float(condition_weights.get(p2, 0.0)), 0.0)
        score = orb_weight * base * ((cw1 * cw2) ** 0.5)
        metric_weight = float(distribution.get(metric_label, 0.0))
        if metric_key == "escalating" and tone == "volatile_pair":
            metric_weight *= 1.15
        routed_value = score * metric_weight
        if routed_value <= 0.0:
            continue
        rows.append((routed_value, p1, p2, aspect_type.replace("_", " "), tone or "neutral_pair", orb_weight, cw1, cw2, distribution))

    rows.sort(key=lambda x: x[0], reverse=True)
    color = planet_dynamics_bar_colors.get(metric_key, chart_theme_colors.get("text", "#f5f5f5"))
    classification_color = {"antagonizing": "#ff6b6b", "enabling": "#6be39d", "escalating": "#ffbd59"}.get(metric_key, color)
    classification_word_color = {
        "antagonizing": "#ff6b6b",
        "enabling": "#6be39d",
        "escalating": "#ffbd59",
    }

    def _tone_label(raw_tone: str) -> str:
        cleaned = str(raw_tone or "neutral_pair").replace("_pair", "")
        tone_color = "#ffbd59" if cleaned == "volatile" else classification_word_color.get(cleaned, chart_theme_colors.get("text", "#f5f5f5"))
        return f"<span style='color:{tone_color};'>{html.escape(cleaned)}</span>"

    detail_items = []
    for value, p1, p2, aname, tone, orbw, cw1, cw2, distribution in rows:
        p1_color = PLANET_COLORS.get(p1, chart_theme_colors.get("text", "#f5f5f5"))
        p2_color = PLANET_COLORS.get(p2, chart_theme_colors.get("text", "#f5f5f5"))
        aspect_color = ASPECT_COLORS.get(aname, chart_theme_colors.get("text", "#f5f5f5"))
        p1_html = f"<span style='color:{html.escape(str(p1_color))};'>{html.escape(_display_body_name(p1))}</span>"
        p2_html = f"<span style='color:{html.escape(str(p2_color))};'>{html.escape(_display_body_name(p2))}</span>"
        aspect_html = f"<span style='color:{html.escape(str(aspect_color))};'>{html.escape(aname)}</span>"
        class_word = metric_label.lower()
        class_word_color = classification_word_color.get(metric_key, classification_color)
        class_html = f"<span style='color:{class_word_color};'><b>{html.escape(class_word)}</b></span>"
        metric_name_html = f"<span style='color:{class_word_color};'>{html.escape(metric_label)}</span>"
        detail_items.append(
            f"<li>{p1_html} {aspect_html} {p2_html}: {class_html} because {p1_html} ({cw1:.3f}) and {p2_html} ({cw2:.3f}) are a {_tone_label(tone)} pair with orb weight {orbw:.3f}, and this aspect distributes scores as E {float(distribution.get('Enabling', 0.0)):.2f} / A {float(distribution.get('Antagonizing', 0.0)):.2f} / X {float(distribution.get('Escalating', 0.0)):.2f}, contributing {value:.3f} to the {metric_name_html} score.</li>"
        )
    chart_name = html.escape(str(getattr(chart, "name", "This chart") or "This chart"))
    target_display = html.escape(_display_body_name(target_key).upper())
    body_label = classify_body_dynamics(body_scores)
    body_name = html.escape(_display_body_name(target_key))
    label_sentence = f"{body_name} is an {html.escape(body_label)} in {chart_name}'s chart."
    return (
        f"<div style='font-weight:bold; color:{chart_data_highlight_color};'>Body Dynamics • {html.escape(metric_label)} • {target_display}</div>"
        f"<div><b>{chart_name}'s {target_display}</b> is <span style='color:{classification_color};'>{share:.2f}%</span> <span style='color:{classification_color};'>{html.escape(metric_label)}</span>; <span style='color:{classification_color};'>{influence_share:.2f}%</span> of total <span style='color:{classification_color};'>{html.escape(metric_label)}</span> influences in chart.</div>"
        f"<div><b>{label_sentence}</b> <span style='color:{html.escape(color)};'>({metric_total:.3f})</span></div><br>"
        f"<div style='font-weight:bold; color:{chart_data_highlight_color};'>Score Breakdown:</div>"
        f"<ul>{''.join(detail_items) if detail_items else '<li>No matching aspect contributions for this selection.</li>'}</ul>"
    )
