"""Total chart TXT/Markdown export builders for Database View."""

from __future__ import annotations

import datetime
import html
import re
from collections.abc import Callable
from typing import Any

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
        return ["No data"]
    return [f"{rank} {label}: {value:.2f}" for rank, (label, value) in enumerate(ranked, start=1)]


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
    shape_meta = chart_type.get("shape_meta", {}) or {}
    chart_type_lines = [
        f"- Shape: {shape_key.replace('_', ' ').title()}",
        "- Aspect patterns: " + (", ".join(pattern_names) if pattern_names else "None detected"),
    ]
    if shape_key == "locomotive":
        leader = str(shape_meta.get("leader", "") or "").strip()
        chart_type_lines.append("- Leader: " + (leader if leader else "Unknown"))
    return "\n".join(chart_type_lines)


def _build_predictions_export_text(
    chart: Chart,
    *,
    markdown: bool,
    calculate_enneagram_scores: Callable[[Chart], dict[int, float]] | None,
) -> str:
    lines: list[str] = []
    if chart_is_non_aggregable(chart):
        lines.append("Predictions are unavailable for placeholder/hypothetical charts.")
    else:
        try:
            if calculate_enneagram_scores is None:
                raise RuntimeError("Enneagram score provider is unavailable.")
            enneagram_scores = calculate_enneagram_scores(chart)
            lines.append(f"Predicted Tritype: {tritype_text_for_scores(enneagram_scores)}")
            lines.append(_plain_text_from_htmlish(enneagram_realm_summary_html(enneagram_scores)))
            lines.append("")
            lines.append("Enneagram type scores:")
            for rank, (enneagram_type, score) in enumerate(
                sorted(
                    enneagram_scores.items(),
                    key=lambda item: float(item[1]),
                    reverse=True,
                ),
                start=1,
            ):
                lines.append(f"{rank} Type {enneagram_type}: {float(score):.2f}")
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


def _remove_bazi_identifying_header(body: str, *, markdown: bool) -> str:
    text = str(body or "").strip()
    if not text:
        return text
    if markdown:
        year_match = re.search(r"^- \*\*Year:\*\*\s*(.+)$", text, flags=re.MULTILINE)
        details_match = re.search(r"^## BAZI CHART DETAILS\s*$", text, flags=re.MULTILINE)
        if details_match:
            prefix = f"**Year:** {year_match.group(1).strip()}\n\n" if year_match else ""
            return prefix + text[details_match.start():].lstrip()
        return text

    lines = text.splitlines()
    year_line = next((line for line in lines if line.startswith("Year: ")), "")
    details_index = next((idx for idx, line in enumerate(lines) if line.strip() == "BAZI CHART DETAILS"), None)
    if details_index is None:
        return text
    kept: list[str] = []
    if year_line:
        kept.append(year_line)
        kept.append("")
    kept.extend(lines[details_index:])
    return "\n".join(kept).strip()


def _build_bazi_export_text(chart: Chart, *, markdown: bool) -> str:
    try:
        txt_payload, md_payload = build_bazi_export_payload_for_chart(chart)
        body = _remove_bazi_identifying_header(md_payload if markdown else txt_payload, markdown=markdown)
    except Exception as exc:
        body = f"BaZi chart unavailable: {exc}"
    return _section("BaZi Window", body, markdown=markdown)


def _format_similarity_scoring_method(
    *,
    algorithm_mode: str | None,
    similarity_settings: Any | None,
) -> str:
    mode = str(algorithm_mode or "default").strip().lower() or "default"
    mode_label = {
        "default": "Default",
        "comprehensive": "Comprehensive",
        "custom": "Custom",
    }.get(mode, mode.replace("_", " ").title())
    lines = [f"Current Settings > Similarities Calculator scoring system: {mode_label}."]

    settings = similarity_settings
    if mode == "comprehensive" or (mode == "custom" and settings is not None):
        try:
            enabled = settings.enabled_components()
            weights = settings.weights_by_component()
            active = [
                (key.replace("_", " "), float(weights.get(key, 0.0)))
                for key, is_enabled in enabled.items()
                if bool(is_enabled) and float(weights.get(key, 0.0)) > 0.0
            ]
            total = sum(weight for _key, weight in active)
            if active and total > 0:
                component_text = ", ".join(
                    f"{label} {weight / total * 100.0:.1f}%"
                    for label, weight in active
                )
                lines.append(f"Enabled normalized component weights: {component_text}.")
            placement_mode = getattr(settings, "placement_weighting_mode", None)
            if placement_mode:
                lines.append(f"Placement weighting mode: {str(placement_mode).replace('_', ' ')}.")
        except Exception:
            pass
    else:
        lines.append("Default mode combines placement, aspect, distribution, and dominance similarity components.")
    return "\n".join(lines)


def _format_similar_chart_rows(rows: list[dict[str, Any]], *, markdown: bool) -> list[str]:
    if markdown:
        lines = [
            "| Rank | Chart ID | Chart | Similarity | Band | Z-score | Placement | Aspects | Distribution | Dominance |",
            "|---:|---:|---|---:|---|---:|---:|---:|---:|---:|",
        ]
        for row in rows:
            z_score = row.get("similarity_z_score")
            z_score_text = "" if z_score is None else f"{float(z_score):+.3f}"
            dominance = row.get("dominance_percent")
            dominance_text = "" if dominance is None else f"{float(dominance):.1f}%"
            lines.append(
                f"| {row.get('rank', '')} | {row.get('chart_id', '')} | {row.get('chart_name', '')} | "
                f"{float(row.get('similarity_percent', 0.0)):.1f}% | {row.get('similarity_band', '')} | "
                f"{z_score_text} | {float(row.get('placement_percent', 0.0)):.1f}% | "
                f"{float(row.get('aspect_percent', 0.0)):.1f}% | "
                f"{float(row.get('distribution_percent', 0.0)):.1f}% | {dominance_text} |"
            )
        return lines

    lines: list[str] = []
    for row in rows:
        z_score = row.get("similarity_z_score")
        z_score_text = "" if z_score is None else f"; z={float(z_score):+.3f}"
        dominance = row.get("dominance_percent")
        dominance_text = "" if dominance is None else f", dominance {float(dominance):.1f}%"
        lines.append(
            f"{row.get('rank', '')}. #{row.get('chart_id', '')} — {row.get('chart_name', '')}: "
            f"Similarity {float(row.get('similarity_percent', 0.0)):.1f}% "
            f"[{row.get('similarity_band', 'unclassified')}{z_score_text}] "
            f"(placements {float(row.get('placement_percent', 0.0)):.1f}%, "
            f"aspects {float(row.get('aspect_percent', 0.0)):.1f}%, "
            f"distribution {float(row.get('distribution_percent', 0.0)):.1f}%{dominance_text})"
        )
    return lines or ["No similar charts available."]


def build_total_chart_similar_charts_section(
    *,
    subject_name: str,
    most_rows: list[dict[str, Any]],
    least_rows: list[dict[str, Any]],
    markdown: bool,
    algorithm_mode: str | None = None,
    similarity_settings: Any | None = None,
) -> str:
    scoring_text = _format_similarity_scoring_method(
        algorithm_mode=algorithm_mode,
        similarity_settings=similarity_settings,
    )
    if markdown:
        lines = ["# Similar Charts", "", "## 25 Most Similar", ""]
        lines.extend(_format_similar_chart_rows(most_rows, markdown=True))
        lines.extend(["", "## 25 Least Similar", ""])
        lines.extend(_format_similar_chart_rows(least_rows, markdown=True))
        lines.extend(["", "## Chart Similarities Scoring Method", "", scoring_text])
        return "\n".join(lines).strip()

    lines = ["SIMILAR CHARTS", "==============", "", "25 Most Similar", ""]
    lines.extend(_format_similar_chart_rows(most_rows, markdown=False))
    lines.extend(["", "25 Least Similar", ""])
    lines.extend(_format_similar_chart_rows(least_rows, markdown=False))
    lines.extend(["", "Chart Similarities Scoring Method", "", scoring_text])
    return "\n".join(lines).strip()


def build_total_chart_export_text(
    chart: Chart,
    *,
    markdown: bool,
    show_cursedness: bool = False,
    show_dnd_output: bool = False,
    calculate_enneagram_scores: Callable[[Chart], dict[int, float]] | None = None,
    similar_charts_section: str | None = None,
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
        _build_predictions_export_text(
            chart,
            markdown=markdown,
            calculate_enneagram_scores=calculate_enneagram_scores,
        ),
        _build_human_design_export_text(chart, markdown=markdown),
        _build_bazi_export_text(chart, markdown=markdown),
    ]
    if similar_charts_section:
        sections.append(str(similar_charts_section))
    return "\n\n".join(section.strip() for section in sections if str(section).strip()) + "\n"
