"""Total chart TXT/Markdown export builders for Database View."""

from __future__ import annotations

import datetime
import html
import re

from ephemeraldaddy.analysis.dnd.dnd_class_axes_v2 import score_dnd_statblock
from ephemeraldaddy.analysis.human_design import (
    build_human_design_chart_data_output,
    build_human_design_result,
)
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.interpretations import ASPECT_PATTERN_DEFS, PLANET_ORDER
from ephemeraldaddy.gui.features.charts.algorithmic_transparency import (
    build_gender_guesser_breakdown_text,
)
from ephemeraldaddy.gui.features.charts.bazi_window import build_bazi_export_payload_for_chart
from ephemeraldaddy.gui.features.charts.dnd_predictions import build_dnd_top_three_summary_html
from ephemeraldaddy.gui.features.charts.enneagram_predictions import (
    calculate_enneagram_type_weights,
    enneagram_realm_summary_html,
    tritype_text_for_scores,
)
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_element_weights,
    calculate_dominant_house_weights,
    calculate_dominant_nakshatra_weights,
    calculate_dominant_planet_weights,
    calculate_dominant_sign_weights,
    calculate_element_prevalence_counts,
    calculate_house_prevalence_counts,
    calculate_modal_prevalence_counts,
    calculate_mode_weights,
    calculate_nakshatra_prevalence_counts,
    calculate_planet_dynamics_scores,
    calculate_sidereal_planet_prevalence_counts,
    calculate_sign_prevalence_counts,
)
from ephemeraldaddy.gui.features.charts.provenance import chart_is_non_aggregable
from ephemeraldaddy.gui.features.charts.text_summary import _display_body_name, format_chart_text

_DND_STAT_EXPORT_ORDER: tuple[str, ...] = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


def _plain_text_from_htmlish(value: object) -> str:
    text = str(value or "")
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</\s*(p|div|li|h[1-6])\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _format_ranked_values(values: dict[str, object], *, limit: int | None = None) -> list[str]:
    ranked = sorted(
        ((str(label), float(raw_value or 0.0)) for label, raw_value in (values or {}).items()),
        key=lambda item: item[1],
        reverse=True,
    )
    if limit is not None:
        ranked = ranked[:limit]
    if not ranked:
        return ["- No data"]
    return [f"- {label}: {value:.2f}" for label, value in ranked]


def _section(title: str, body: str, *, markdown: bool) -> str:
    clean_body = str(body or "").strip() or "No data available."
    if markdown:
        return f"## {title}\n\n{clean_body}"
    return f"{title.upper()}\n{'=' * len(title)}\n\n{clean_body}"


def _build_analytics_export_text(chart: Chart, *, markdown: bool) -> str:
    sections: list[str] = []
    analytics_groups = [
        ("Dominant Signs", calculate_dominant_sign_weights(chart)),
        ("Sign Prevalence", calculate_sign_prevalence_counts(chart)),
        ("Dominant Bodies", calculate_dominant_planet_weights(chart)),
        ("Dominant Bodies by Nakshatra", calculate_sidereal_planet_prevalence_counts(chart)),
        ("Dominant Houses", calculate_dominant_house_weights(chart)),
        ("House Prevalence", calculate_house_prevalence_counts(chart)),
        ("Dominant Elements", calculate_dominant_element_weights(chart)),
        ("Element Prevalence", calculate_element_prevalence_counts(chart)),
        ("Dominant Nakshatras", calculate_dominant_nakshatra_weights(chart)),
        ("Nakshatra Prevalence", calculate_nakshatra_prevalence_counts(chart)),
        ("Dominant Modes", calculate_mode_weights(chart)),
        ("Modal Prevalence", calculate_modal_prevalence_counts(chart)),
    ]
    for title, values in analytics_groups:
        sections.append(
            _section(
                title,
                "\n".join(_format_ranked_values(values)),
                markdown=markdown,
            )
        )

    dynamics_scores = calculate_planet_dynamics_scores(chart)
    dynamics_lines: list[str] = []
    for body in PLANET_ORDER:
        metric_scores = dynamics_scores.get(body)
        if not metric_scores:
            continue
        dynamics_lines.append(
            f"- {_display_body_name(body)}: "
            f"antagonizing {float(metric_scores.get('antagonizing', 0.0)):.2f}; "
            f"enabling {float(metric_scores.get('enabling', 0.0)):.2f}; "
            f"escalating {float(metric_scores.get('escalating', 0.0)):.2f}"
        )
    sections.append(_section("Body Dynamics", "\n".join(dynamics_lines), markdown=markdown))

    chart_type = chart_type_summary_text(chart)
    sections.append(_section("Chart Type", chart_type, markdown=markdown))

    try:
        gender_text = build_gender_guesser_breakdown_text(chart)
    except Exception as exc:
        gender_text = f"Gender guesser unavailable: {exc}"
    sections.append(_section("Gender Guesser", gender_text, markdown=markdown))
    return "\n\n".join(sections)


def chart_type_summary_text(chart: Chart) -> str:
    from ephemeraldaddy.analysis.chart_type_identifier import chart_type_summary

    chart_type = chart_type_summary(chart)
    shape_key = str(chart_type.get("shape", "unknown") or "unknown")
    pattern_names = [
        str(ASPECT_PATTERN_DEFS.get(pattern_key, {}).get("name", pattern_key))
        for pattern_key in chart_type.get("patterns", []) or []
    ]
    chart_type_lines = [
        f"- Shape: {shape_key.replace('_', ' ').title()}",
        "- Aspect patterns: " + (", ".join(pattern_names) if pattern_names else "None detected"),
    ]
    return "\n".join(chart_type_lines)


def _build_predictions_export_text(chart: Chart, *, markdown: bool) -> str:
    lines: list[str] = []
    if chart_is_non_aggregable(chart):
        lines.append("Predictions are unavailable for placeholder/hypothetical charts.")
    else:
        try:
            enneagram_scores = calculate_enneagram_type_weights(chart)
            lines.append(f"Predicted Tritype: {tritype_text_for_scores(enneagram_scores)}")
            lines.append(_plain_text_from_htmlish(enneagram_realm_summary_html(enneagram_scores)))
            lines.append("")
            lines.append("Enneagram type scores:")
            for enneagram_type, score in sorted(
                enneagram_scores.items(),
                key=lambda item: float(item[1]),
                reverse=True,
            ):
                lines.append(f"- Type {enneagram_type}: {float(score):.2f}")
        except Exception as exc:
            lines.append(f"Enneagram predictions unavailable: {exc}")
        lines.append("")
        try:
            statblock = score_dnd_statblock(chart)
            lines.append("D&D Statblock:")
            for stat_key in _DND_STAT_EXPORT_ORDER:
                lines.append(
                    f"- {stat_key}: {int(statblock.scores.get(stat_key, 0))} "
                    f"(modifier {int(statblock.modifiers.get(stat_key, 0)):+d})"
                )
            lines.append("")
            lines.append(_plain_text_from_htmlish(build_dnd_top_three_summary_html(chart, linked=False)))
        except Exception as exc:
            lines.append(f"D&D predictions unavailable: {exc}")
    return _section("Predictions Panel", "\n".join(lines), markdown=markdown)


def _build_human_design_export_text(chart: Chart, *, markdown: bool) -> str:
    try:
        hd_text, _position_info_map, _aspect_info_map, _species_info_map, _offset = build_human_design_chart_data_output(
            chart,
            aspect_sort="Priority",
        )
        hd_result = build_human_design_result(chart)
        activations = (*hd_result.personality_activations, *hd_result.design_activations)
        line_counts = {line: 0 for line in range(1, 7)}
        color_counts: dict[int, int] = {}
        tone_counts: dict[int, int] = {}
        for activation in activations:
            line = int(getattr(activation, "line", 0) or 0)
            color = int(getattr(activation, "color", 0) or 0)
            tone = int(getattr(activation, "tone", 0) or 0)
            if line in line_counts:
                line_counts[line] += 1
            if color:
                color_counts[color] = color_counts.get(color, 0) + 1
            if tone:
                tone_counts[tone] = tone_counts.get(tone, 0) + 1
        analytics_lines = [
            "Human Design Analytics",
            "",
            "Line Distribution:",
            *[f"- Line {line}: {count}" for line, count in sorted(line_counts.items())],
            "",
            "Color Distribution:",
            *[f"- Color {color}: {count}" for color, count in sorted(color_counts.items())],
            "",
            "Tone Distribution:",
            *[f"- Tone {tone}: {count}" for tone, count in sorted(tone_counts.items())],
        ]
        body = "\n\n".join([hd_text.strip(), "\n".join(analytics_lines)])
    except Exception as exc:
        body = f"Human Design chart unavailable: {exc}"
    return _section("Human Design Chart Popout", body, markdown=markdown)


def _build_bazi_export_text(chart: Chart, *, markdown: bool) -> str:
    try:
        txt_payload, md_payload = build_bazi_export_payload_for_chart(chart)
        body = md_payload if markdown else txt_payload
    except Exception as exc:
        body = f"BaZi chart unavailable: {exc}"
    return _section("BaZi Window", body, markdown=markdown)


def build_total_chart_export_text(
    chart: Chart,
    *,
    markdown: bool,
    show_cursedness: bool = True,
    show_dnd_output: bool = False,
) -> str:
    """Build the complete single-chart export payload for TXT/Markdown files."""
    chart_name = (getattr(chart, "name", None) or "Chart").strip() or "Chart"
    chart_data_text, _position_info_map, _aspect_info_map, _species_info_map = format_chart_text(
        chart,
        aspect_sort="Priority",
        show_cursedness=show_cursedness,
        show_dnd_output=show_dnd_output,
    )
    generated_on = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if markdown:
        header = f"# Total Chart Export: {chart_name}\n\nGenerated: {generated_on}"
    else:
        title = f"TOTAL CHART EXPORT: {chart_name}"
        header = f"{title}\n{'=' * len(title)}\n\nGenerated: {generated_on}"
    sections = [
        header,
        _section("Chart Data Output", chart_data_text, markdown=markdown),
        _section(
            "Chart Analytics Panel",
            _build_analytics_export_text(chart, markdown=markdown),
            markdown=markdown,
        ),
        _build_predictions_export_text(chart, markdown=markdown),
        _build_human_design_export_text(chart, markdown=markdown),
        _build_bazi_export_text(chart, markdown=markdown),
    ]
    return "\n\n".join(section.strip() for section in sections if str(section).strip()) + "\n"
