"""D&D prediction chart rendering helpers for Chart View."""

from __future__ import annotations

import html
from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from ephemeraldaddy.analysis.dnd.dnd_definitions import (
    DND_CLASS_SUBCLASS_STATS,
    DND_STAT_PREDICTORS,
    DND_STAT_EXPLANATIONS,
    SPECIES_DESCRIPTIONS,
)
from ephemeraldaddy.analysis.dnd.dnd_class_axes_v2 import (
    DND_CLASSES,
    DND_CLASS_SUBCLASS_EXPLAINERS,
    DnDClassScorer,
    build_class_axis_profile_lines,
    resolve_class_key,
    score_class_axes,
    score_class_families,
    score_dnd_classes,
    score_dnd_statblock,
)
from ephemeraldaddy.analysis.dnd.species_assigner_v2 import (
    SpeciesAssigner,
    assign_top_three_species,
    assign_top_three_species_with_evidence,
)
from ephemeraldaddy.analysis.weighted_chart_predictor import (
    active_bazi_sign_weights,
    active_human_design_channels,
    active_human_design_gates,
    active_human_design_properties,
    calculate_dominant_house_weights,
    calculate_dominant_nakshatra_weights,
    calculate_dominant_planet_weights,
    calculate_dominant_sign_weights,
    default_chart_uses_houses,
    normalize_weight_map_for_dominance_activation,
    parse_aspect_spec,
    normalize_factor_value,
    weighted_bazi_sign_entries,
    weighted_channel_entries,
    weighted_gate_entries,
    weighted_hd_authority_entries,
    weighted_hd_center_entries,
    weighted_hd_profile_entries,
    weighted_hd_type_entries,
    weighted_house_entries,
    weighted_position_entries,
    weighted_string_entries,
)
from ephemeraldaddy.analysis.weighted_chart_predictor import (
    _position_match_weight,
    _weighted_text_entries,
)
from ephemeraldaddy.core.interpretations import ASPECT_SCORE_WEIGHTS
from ephemeraldaddy.gui.style import (
    CHART_DATA_HIGHLIGHT_COLOR,
    DND_STAT_EARTHTONE_COLORS,
    apply_chart_info_link_cursor,
    get_cycled_earthtone_colors,
)


DND_STAT_KEYS: tuple[str, ...] = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


def _style_prediction_bar_chart(ax: Any, *, labels: list[str], max_value: float, apply_standard_bar_axes: Any) -> None:
    """Apply the same vertical-bar styling used by Chart Analytics graphs."""
    apply_standard_bar_axes(ax, labels)
    ax.set_ylim(0, max(1.0, float(max_value) + 1.0))
    ax.set_anchor("W")
    for spine in ax.spines.values():
        spine.set_color("#444444")
    ax.figure.tight_layout()
    ax.figure.subplots_adjust(left=0.18, bottom=0.20, top=0.92, right=0.96)


def draw_dnd_statblock_predictions(
    ax: Any,
    chart: Any,
    *,
    dnd_stat_keys: tuple[str, ...],
    apply_standard_bar_axes: Any,
    norm_charts: Any = None,
    statblock: Any = None,
) -> None:
    if statblock is None:
        statblock = score_dnd_statblock(chart, norm_charts=norm_charts)
    labels = list(dnd_stat_keys)
    values = [float(statblock.scores.get(label, 0.0)) for label in labels]
    max_value = max(values, default=0.0)
    bars = ax.bar(labels, values)
    value_label_offset = max(0.25, max_value * 0.03)
    for idx, bar in enumerate(bars):
        stat_key = labels[idx]
        stat_value = values[idx]
        bar.set_facecolor(DND_STAT_EARTHTONE_COLORS.get(stat_key, "#6fa8dc"))
        bar.set_alpha(0.95)
        bar.set_gid(f"dnd_stat:{stat_key}")
        bar.set_picker(True)
        ax.text(
            bar.get_x() + (bar.get_width() / 2.0),
            stat_value + value_label_offset,
            f"{int(stat_value)}",
            va="bottom",
            ha="center",
            color="#f5f5f5",
            fontsize=9,
            fontweight="bold",
        )
    ax.set_title("", color="#f5f5f5", fontsize=10, pad=8)
    _style_prediction_bar_chart(
        ax,
        labels=labels,
        max_value=max_value + value_label_offset,
        apply_standard_bar_axes=apply_standard_bar_axes,
    )


def draw_dnd_species_predictions(ax: Any, chart: Any, *, apply_standard_bar_axes: Any) -> None:
    pick = SpeciesAssigner().assign(chart)
    top = pick.top_three[:10]
    labels = [f"{family} ({subtype})" if subtype else family for family, subtype, _score in top]
    values = [float(score) for _family, _subtype, score in top]
    colors = get_cycled_earthtone_colors(len(labels))
    bars = ax.bar(labels, values)
    for idx, bar in enumerate(bars):
        bar.set_facecolor(colors[idx])
        bar.set_alpha(0.95)
    ax.set_title("Top 10 Species", color="#f5f5f5", fontsize=10, pad=8)
    _style_prediction_bar_chart(
        ax,
        labels=labels,
        max_value=max(values, default=0.0),
        apply_standard_bar_axes=apply_standard_bar_axes,
    )


def draw_dnd_classes_predictions(ax: Any, chart: Any, *, apply_standard_bar_axes: Any) -> None:
    axis_scores = score_class_axes(chart)
    family_scores = score_class_families(axis_scores)
    class_scores = score_dnd_classes(axis_scores, family_scores)
    ranked = sorted(class_scores.items(), key=lambda item: item[1], reverse=True)[:10]
    labels = [DND_CLASSES[key].display_name if key in DND_CLASSES else key for key, _ in ranked]
    values = [float(score) for _key, score in ranked]
    colors = get_cycled_earthtone_colors(len(labels))
    bars = ax.bar(labels, values)
    for idx, bar in enumerate(bars):
        bar.set_facecolor(colors[idx])
        bar.set_alpha(0.95)
    ax.set_title("Top 10 Classes", color="#f5f5f5", fontsize=10, pad=8)
    _style_prediction_bar_chart(
        ax,
        labels=labels,
        max_value=max(values, default=0.0),
        apply_standard_bar_axes=apply_standard_bar_axes,
    )


def _stat_definition_for_key(stat_key: str) -> dict[str, Any] | None:
    normalized_key = str(stat_key or "").strip().upper()
    for definition in DND_STAT_EXPLANATIONS.values():
        if str(definition.get("abbrev", "")).strip().upper() == normalized_key:
            return definition
    return None


def _html_list(values: Any) -> str:
    if isinstance(values, (list, tuple, set)):
        items = [str(value).strip() for value in values if str(value).strip()]
    else:
        item = str(values or "").strip()
        items = [item] if item else []
    if not items:
        return "<ul><li>—</li></ul>"
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


def _format_signed_delta(value: float) -> str:
    return f"{value:+.2f}"


def _evidence_line(label: str, contribution: float, detail: str = "") -> str:
    direction = "supports" if contribution >= 0 else "drags down"
    detail_text = f"; {detail}" if detail else ""
    return (
        f"<li><b>{html.escape(label)}</b>: {direction} "
        f"({_format_signed_delta(contribution)} raw evidence{html.escape(detail_text)})</li>"
    )


def _build_dnd_stat_evidence_html(chart: Any, stat_key: str, *, max_items_per_category: int = 8) -> str:
    """Explain the chart-specific predictor evidence behind one D&D stat score."""
    factors = DND_STAT_PREDICTORS.get(stat_key, {})
    if not isinstance(factors, dict):
        return ""

    use_houses = default_chart_uses_houses(chart)
    sign_weights = normalize_weight_map_for_dominance_activation(
        getattr(chart, "dominant_sign_weights", None) or calculate_dominant_sign_weights(chart),
        "range",
    )
    body_weights = normalize_weight_map_for_dominance_activation(
        getattr(chart, "dominant_planet_weights", None) or calculate_dominant_planet_weights(chart),
        "range",
    )
    house_weights = normalize_weight_map_for_dominance_activation(
        calculate_dominant_house_weights(chart) if use_houses else {},
        "range",
    )
    nakshatra_weights = normalize_weight_map_for_dominance_activation(
        getattr(chart, "dominant_nakshatra_weights", None) or calculate_dominant_nakshatra_weights(chart),
        "range",
    )
    body_house_lookup: dict[str, int] = {}
    if use_houses:
        from ephemeraldaddy.analysis.weighted_chart_predictor import house_for_longitude

        for raw_body, lon in (getattr(chart, "positions", None) or {}).items():
            body = normalize_factor_value(str(raw_body))
            try:
                house_num = house_for_longitude(getattr(chart, "houses", None), float(lon))
            except (TypeError, ValueError):
                continue
            if house_num is not None:
                body_house_lookup[body] = house_num

    active_gates = active_human_design_gates(chart)
    active_channels = active_human_design_channels(chart)
    active_hd_type, active_centers, active_profile, active_authority = active_human_design_properties(chart)
    bazi_weights = active_bazi_sign_weights(chart)

    sections: list[tuple[str, list[tuple[float, str]]]] = []

    def add_weight_matches(title: str, positive_key: str, negative_key: str, weights: dict[Any, float], entry_fn: Any) -> None:
        rows: list[tuple[float, str]] = []
        for key, criterion_weight in entry_fn(factors.get(positive_key, {})).items():
            activation = float(weights.get(key, 0.0))
            if activation:
                contribution = activation * float(criterion_weight)
                rows.append((contribution, _evidence_line(f"{key} {positive_key}", contribution, f"dominance {activation:.2f} × predictor weight {float(criterion_weight):+.2f}")))
        for key, criterion_weight in entry_fn(factors.get(negative_key, {})).items():
            activation = float(weights.get(key, 0.0))
            if activation:
                contribution = -activation * abs(float(criterion_weight))
                rows.append((contribution, _evidence_line(f"{key} {negative_key}", contribution, f"dominance {activation:.2f} × anti weight {float(criterion_weight):+.2f}")))
        if rows:
            sections.append((title, rows))

    add_weight_matches("Dominance weights: signs", "signs", "antisigns", sign_weights, weighted_string_entries)
    add_weight_matches("Dominance weights: bodies", "bodies", "antibodies", body_weights, weighted_string_entries)
    add_weight_matches("Dominance weights: nakshatras", "nakshatras", "antinakshatras", nakshatra_weights, weighted_string_entries)
    if use_houses:
        add_weight_matches("Dominance weights: houses", "houses", "antihouses", house_weights, weighted_house_entries)

    position_rows: list[tuple[float, str]] = []
    for bucket, sign in (("positions", 1.0), ("antipositions", -1.0)):
        for spec, criterion_weight in weighted_position_entries(factors.get(bucket, {})).items():
            activation = _position_match_weight(spec, chart, use_houses, body_house_lookup, body_weights, sign_weights, house_weights, use_dominance_weighting=True)
            if activation:
                contribution = sign * activation * abs(float(criterion_weight))
                position_rows.append((contribution, _evidence_line(spec, contribution, f"matched position activation {activation:.2f} × predictor weight {float(criterion_weight):+.2f}")))
    if position_rows:
        sections.append(("Specific positions", position_rows))

    aspect_rows: list[tuple[float, str]] = []
    chart_aspects = getattr(chart, "aspects", []) or []
    for bucket, sign in (("aspects", 1.0), ("antiaspects", -1.0)):
        for spec, criterion_weight in _weighted_text_entries(factors.get(bucket, {})).items():
            parsed = parse_aspect_spec(spec)
            if parsed is None:
                continue
            left_body, aspect_type, right_body = parsed
            for aspect in chart_aspects:
                p1 = normalize_factor_value(str(aspect.get("p1", "")))
                p2 = normalize_factor_value(str(aspect.get("p2", "")))
                if str(aspect.get("type", "")).strip().lower() == aspect_type and {p1, p2} == {left_body, right_body}:
                    activation = float(body_weights.get(left_body, 0.0)) + float(ASPECT_SCORE_WEIGHTS.get(aspect_type, 0.0)) + float(body_weights.get(right_body, 0.0))
                    contribution = sign * activation * abs(float(criterion_weight))
                    aspect_rows.append((contribution, _evidence_line(spec, contribution, f"aspect/body activation {activation:.2f} × predictor weight {float(criterion_weight):+.2f}")))
                    break
    if aspect_rows:
        sections.append(("Aspects", aspect_rows))

    def add_membership(title: str, positive_key: str, negative_key: str, active: Any, entry_fn: Any, formatter: Any = str) -> None:
        rows: list[tuple[float, str]] = []
        active_set = active if isinstance(active, set) else {active}
        for key, criterion_weight in entry_fn(factors.get(positive_key, {})).items():
            if key in active_set:
                contribution = float(criterion_weight)
                rows.append((contribution, _evidence_line(formatter(key), contribution, f"active match × predictor weight {float(criterion_weight):+.2f}")))
        for key, criterion_weight in entry_fn(factors.get(negative_key, {})).items():
            if key in active_set:
                contribution = -abs(float(criterion_weight))
                rows.append((contribution, _evidence_line(formatter(key), contribution, f"active anti-match × anti weight {float(criterion_weight):+.2f}")))
        if rows:
            sections.append((title, rows))

    add_membership("Human Design gates", "gates", "antigates", active_gates, weighted_gate_entries, lambda gate: f"Gate {gate}")
    add_membership("Human Design channels", "channels", "antichannels", active_channels, weighted_channel_entries, lambda channel: f"Channel {channel[0]}-{channel[1]}")
    add_membership("Human Design type", "hdtypes", "antihdtypes", active_hd_type, weighted_hd_type_entries)
    add_membership("Human Design centers", "centers", "anticenters", active_centers, weighted_hd_center_entries)
    add_membership("Human Design profile", "profiles", "antiprofiles", active_profile, weighted_hd_profile_entries)
    add_membership("Human Design authority", "authorities", "antiauthorities", active_authority, weighted_hd_authority_entries)
    add_weight_matches("BaZi sign weights", "bazisigns", "antibazisigns", bazi_weights, weighted_bazi_sign_entries)

    if not sections:
        return "<div>No chart-specific predictor matches were found for this stat; the score is mostly baseline/normalization.</div>"

    html_sections: list[str] = []
    for title, rows in sections:
        rows = sorted(rows, key=lambda row: abs(row[0]), reverse=True)
        omitted = max(0, len(rows) - max_items_per_category)
        rendered_rows = [line for _contribution, line in rows[:max_items_per_category]]
        if omitted:
            rendered_rows.append(f"<li>…{omitted} smaller matched item(s) omitted.</li>")
        subtotal = sum(contribution for contribution, _line in rows)
        html_sections.append(
            f"<div><b>{html.escape(title)}</b> "
            f"<span style='opacity:0.85;'>(subtotal {_format_signed_delta(subtotal)})</span>"
            f"<ul>{''.join(rendered_rows)}</ul></div>"
        )
    return "".join(html_sections)


def build_dnd_statblock_popout_info_html(
    chart: Any,
    stat_key: str,
    *,
    norm_charts: Any = None,
    statblock: Any = None,
    show_explainers: bool = True,
) -> str:
    if chart is None:
        return "No chart is available for this D&D stat interpretation."
    stat_definition = _stat_definition_for_key(stat_key)
    if stat_definition is None:
        return f"No D&D stat interpretation data available for {html.escape(str(stat_key))}."

    if statblock is None:
        statblock = score_dnd_statblock(chart, norm_charts=norm_charts)
    normalized_stat_key = str(stat_key or "").strip().upper()
    stat_value = int(statblock.scores.get(normalized_stat_key, 0))
    chart_name = str(getattr(chart, "name", "Chart") or "Chart").strip() or "Chart"
    stat_name = str(stat_definition.get("label") or normalized_stat_key).strip()
    text_color = "#ffffff"
    header_style = f"font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};"
    body_style = f"color:{text_color};font-weight:400;"

    raw_score = float(statblock.raw_scores.get(normalized_stat_key, 0.0))
    modifier = int(statblock.modifiers.get(normalized_stat_key, 0))
    if show_explainers:
        evidence_html = _build_dnd_stat_evidence_html(chart, normalized_stat_key)
        explainer_html = (
            f"<div style='height:10px;'></div><br>"
            f"<p><div style='{header_style}'><b>Why this chart got this score</b>{evidence_html}</div></p>"
        )
    else:
        explainer_html = (
            f"<div style='height:10px;'></div><br>"
            f"<div style='{body_style};opacity:0.85;'>D&amp;D Statblock explainers are disabled in "
            "Settings &gt; Analytics Visibility.</div>"
        )
    score_context_html = (
        f"<div style='{header_style}'>Final stat: <b>{stat_value}</b> "
        f"(modifier {modifier:+d}); normalized predictor score {raw_score:.3f}. "
        f"{explainer_html}"
    )

    if stat_value > 11:
        return (
            f"<div><span style='{header_style}'>{html.escape(chart_name)}'s "
            f"{html.escape(stat_name)} is higher than average, suggesting:</span>"
            f"<div style='{body_style}'>{_html_list(stat_definition.get('high_score_suggests'))}</div></div>"
            f"<div style='height:10px;'></div>"
            f"<div style='{body_style}'>This suggests skill at: "
            f"{_html_list(stat_definition.get('skills'))}"
            f"and saving throws triggered by: "
            f"{_html_list(stat_definition.get('save_triggers'))}</div>"
            f"<div style='height:12px;'></div>"
            f"{score_context_html}"
        )
    if stat_value < 10:
        return (
            f"<div><span style='{header_style}'>{html.escape(chart_name)}'s "
            f"{html.escape(stat_name)} is lower than average, suggesting:</span>"
            f"<div style='{body_style}'>{_html_list(stat_definition.get('low_score_suggests'))}</div></div>"
            f"<div style='height:12px;'></div>"
            f"{score_context_html}"
        )
    return (
        f"<div><span style='{header_style}'>{html.escape(chart_name)}'s "
        f"{html.escape(stat_name)} is about average.</span></div>"
        f"<div style='height:12px;'></div>"
        f"{score_context_html}"
    )


def format_dnd_species_info_text(
    family: str,
    subtype: str,
    score: float,
    evidence: list[str],
) -> str:
    label = f"{family} ({subtype})" if subtype else family
    header = f"{label} • {score:.2f}"
    species_description = SPECIES_DESCRIPTIONS.get(family, "")
    subtype_key = f"{family}::{subtype}" if subtype else ""
    subtype_description = SPECIES_DESCRIPTIONS.get(subtype_key, "")
    description_parts = [part for part in (species_description, subtype_description) if part]
    description_line = (
        " ".join(description_parts)
        if description_parts
        else "Species flavor text unavailable."
    )
    if evidence:
        lines = [f"• {line}" for line in evidence]
        return "\n".join([header, description_line, "", "Evidence:"] + lines)
    return "\n".join(
        [
            header,
            description_line,
            "",
            "• Evidence is unavailable for this species assignment.",
        ]
    )


def format_dnd_class_info_text(
    class_name: str,
    class_key: str,
    axis_scores: dict[str, float],
) -> str:
    resolved_class_key = (
        resolve_class_key(class_key)
        or resolve_class_key(class_name)
        or class_name
    )
    class_definition = DND_CLASSES.get(resolved_class_key)
    header = (
        class_definition.display_name
        if class_definition is not None
        else class_name
    )
    class_description = DND_CLASS_SUBCLASS_EXPLAINERS.get(
        header,
        "Class flavor text unavailable.",
    )
    evidence_lines = build_class_axis_profile_lines(header, axis_scores)
    if evidence_lines:
        return "\n".join([header, "", class_description, "", *evidence_lines])
    return "\n".join(
        [
            header,
            "",
            class_description,
            "",
            "‣ Axis profile unavailable for this class assignment.",
        ]
    )


def format_dnd_statblock_info_text(profile_lines: list[str]) -> str:
    header = ""
    if profile_lines:
        return "\n".join([header, "", *profile_lines])
    return "\n".join([header, "", "‣ Stat block profile unavailable for this chart."])


def _dnd_label_link(text: str, href: str) -> str:
    return (
        f'<a href="{html.escape(href, quote=True)}" '
        f'style="color:{CHART_DATA_HIGHLIGHT_COLOR};text-decoration:none;">'
        f"{html.escape(text)}</a>"
    )


def _collect_top_three_class_payloads(chart: Any) -> tuple[dict[str, float], list[dict[str, Any]]]:
    try:
        axis_scores = score_class_axes(chart)
        class_scores = DnDClassScorer().score_classes(axis_scores)
        ranked_classes = sorted(
            class_scores.values(),
            key=lambda scored_class: scored_class.score,
            reverse=True,
        )
    except Exception:
        return {}, []

    payloads: list[dict[str, Any]] = []
    for scored_class in ranked_classes[:3]:
        class_definition = DND_CLASSES.get(scored_class.key)
        class_display_name = (
            class_definition.display_name
            if class_definition is not None
            else scored_class.key.replace("_", " ").title()
        )
        payloads.append(
            {
                "name": class_display_name,
                "class_key": scored_class.key,
                "score": float(scored_class.score),
                "axis_scores": {
                    axis_key: float(value) for axis_key, value in axis_scores.items()
                },
            }
        )
    return {axis_key: float(value) for axis_key, value in axis_scores.items()}, payloads


def _collect_top_three_species_payloads(chart: Any) -> list[dict[str, Any]]:
    try:
        species_top_three = assign_top_three_species_with_evidence(chart)
    except Exception:
        try:
            species_top_three = [(*species[:3], []) for species in assign_top_three_species(chart)]
        except Exception:
            species_top_three = []

    payloads: list[dict[str, Any]] = []
    for family, subtype, score, evidence in species_top_three[:3]:
        subtype_text = str(subtype or "").strip()
        label = f"{family} ({subtype_text})" if subtype_text else str(family)
        payloads.append(
            {
                "label": label,
                "family": str(family),
                "subtype": subtype_text,
                "score": float(score),
                "evidence": list(evidence or []),
            }
        )
    return payloads


def build_dnd_top_three_summary_html(chart: Any, *, linked: bool = False) -> str:
    species_payloads = _collect_top_three_species_payloads(chart)
    _axis_scores, class_payloads = _collect_top_three_class_payloads(chart)

    species_lines: list[str] = []
    for rank, payload in enumerate(species_payloads, start=1):
        label = str(payload["label"])
        rendered_label = (
            _dnd_label_link(label, f"dnd-species:{rank - 1}")
            if linked
            else html.escape(label)
        )
        species_lines.append(f"{rank}) {rendered_label}")

    class_lines: list[str] = []
    for rank, payload in enumerate(class_payloads, start=1):
        label = str(payload["name"])
        rendered_label = (
            _dnd_label_link(label, f"dnd-class:{rank - 1}")
            if linked
            else html.escape(label)
        )
        class_lines.append(f"{rank}) {rendered_label}")

    if not species_lines:
        species_lines.append("No species prediction available.")
    if not class_lines:
        class_lines.append("No class prediction available.")

    return (
        "<b>Top 3 Species/Subspecies</b><br>"
        + "<br>".join(species_lines)
        + "<br><br><b>Top 3 Classes</b><br>"
        + "<br>".join(class_lines)
    )


def configure_dnd_top_three_summary_label(
    label: Any,
    chart: Any,
    *,
    info_panel: Any,
    before_show: Callable[[], None] | None = None,
) -> None:
    """Render clickable top-three D&D species/classes into a Predictions label."""

    species_payloads = _collect_top_three_species_payloads(chart)
    _axis_scores, class_payloads = _collect_top_three_class_payloads(chart)

    previous_handler = getattr(label, "_dnd_top_three_link_handler", None)
    if previous_handler is not None:
        try:
            label.linkActivated.disconnect(previous_handler)
        except (RuntimeError, TypeError):
            pass

    def _show_text(text: str) -> None:
        if before_show is not None:
            before_show()
        info_panel.setPlainText(text)

    def _on_link_activated(href: str) -> None:
        prefix, _separator, index_text = str(href).partition(":")
        try:
            index = int(index_text)
        except ValueError:
            return
        if prefix == "dnd-species" and 0 <= index < len(species_payloads):
            payload = species_payloads[index]
            _show_text(
                format_dnd_species_info_text(
                    str(payload.get("family", "Unknown Species")),
                    str(payload.get("subtype", "")),
                    float(payload.get("score", 0.0)),
                    list(payload.get("evidence", [])),
                )
            )
        elif prefix == "dnd-class" and 0 <= index < len(class_payloads):
            payload = class_payloads[index]
            _show_text(
                format_dnd_class_info_text(
                    str(payload.get("name", "Unknown Class")),
                    str(payload.get("class_key", "")),
                    dict(payload.get("axis_scores", {})),
                )
            )

    label._dnd_top_three_link_handler = _on_link_activated
    label.linkActivated.connect(_on_link_activated)
    label.setTextFormat(Qt.RichText)
    label.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.TextSelectableByMouse)
    label.setOpenExternalLinks(False)
    apply_chart_info_link_cursor(label)
    label.setText(build_dnd_top_three_summary_html(chart, linked=True))


class DndPredictionPanelAdapter:
    """Own the D&D prediction panel lifecycle for Chart View."""

    def __init__(
        self,
        *,
        chart_layout: Any,
        summary_label: Any = None,
        info_panel: Any = None,
        before_show: Callable[[], None] | None = None,
        chart_theme_colors: dict[str, str],
        apply_standard_bar_axes: Callable[[Any, list[str]], None],
        is_placeholder_chart: Callable[[Any], bool],
        dnd_stat_keys: tuple[str, ...] = DND_STAT_KEYS,
        norm_charts_provider: Callable[[], Any] | None = None,
    ) -> None:
        self.chart_layout = chart_layout
        self.summary_label = summary_label
        self.info_panel = info_panel
        self.before_show = before_show
        self.chart_theme_colors = chart_theme_colors
        self.apply_standard_bar_axes = apply_standard_bar_axes
        self.is_placeholder_chart = is_placeholder_chart
        self.dnd_stat_keys = dnd_stat_keys
        self.norm_charts_provider = norm_charts_provider

    def _norm_charts(self) -> Any:
        if self.norm_charts_provider is None:
            return None
        try:
            return self.norm_charts_provider()
        except Exception:
            return None

    def _ensure_summary_label(self) -> Any:
        summary_label_is_usable = False
        if self.summary_label is not None:
            try:
                summary_label_is_usable = self.summary_label.parent() is not None
            except RuntimeError:
                summary_label_is_usable = False
        if not summary_label_is_usable:
            self.summary_label = QLabel()
            self.summary_label.setWordWrap(True)
            self.summary_label.setTextFormat(Qt.RichText)
        return self.summary_label

    def _draw_no_data(self, ax: Any, _chart: Any | None) -> None:
        ax.clear()
        ax.set_facecolor(self.chart_theme_colors["panel"])
        ax.set_axis_off()
        ax.text(
            0.5,
            0.5,
            "No data",
            transform=ax.transAxes,
            ha="center",
            va="center",
            color=self.chart_theme_colors["text"],
            fontsize=11,
            fontweight="bold",
        )

    def _statblock_cache_key(self, norm_charts: Any) -> tuple[Any, ...]:
        try:
            norm_count = len(norm_charts) if norm_charts is not None else 0
        except TypeError:
            norm_count = None
        return (id(norm_charts), norm_count, tuple(self.dnd_stat_keys))

    def _score_statblock(self, chart: Any, norm_charts: Any = None) -> Any:
        cache_key = self._statblock_cache_key(norm_charts)
        cached = getattr(chart, "_dnd_statblock_prediction_cache", None)
        if isinstance(cached, dict) and cached.get("key") == cache_key and cached.get("statblock") is not None:
            return cached["statblock"]
        statblock = score_dnd_statblock(chart, norm_charts=norm_charts)
        try:
            setattr(chart, "_dnd_statblock_prediction_cache", {"key": cache_key, "statblock": statblock})
        except Exception:
            pass
        return statblock

    def draw(self, ax: Any, chart: Any) -> None:
        norm_charts = self._norm_charts()
        draw_dnd_statblock_predictions(
            ax,
            chart,
            dnd_stat_keys=self.dnd_stat_keys,
            apply_standard_bar_axes=self.apply_standard_bar_axes,
            norm_charts=norm_charts,
            statblock=self._score_statblock(chart, norm_charts),
        )

    def build_popout_info(self, chart: Any | None, target: str, *, show_explainers: bool = True) -> str:
        if chart is None:
            return build_dnd_statblock_popout_info_html(chart, target, show_explainers=show_explainers)
        norm_charts = self._norm_charts()
        statblock = self._score_statblock(chart, norm_charts)
        cache_key = (
            *self._statblock_cache_key(norm_charts),
            str(target or "").strip().upper(),
            bool(show_explainers),
        )
        cached = getattr(chart, "_dnd_statblock_popout_info_cache", None)
        if isinstance(cached, dict) and cached.get("key") == cache_key and cached.get("html"):
            return str(cached["html"])
        info_html = build_dnd_statblock_popout_info_html(
            chart,
            target,
            norm_charts=norm_charts,
            statblock=statblock,
            show_explainers=show_explainers,
        )
        try:
            setattr(chart, "_dnd_statblock_popout_info_cache", {"key": cache_key, "html": info_html})
        except Exception:
            pass
        return info_html

    def cache_metadata(self, chart: Any) -> dict[str, float]:
        norm_charts = self._norm_charts()
        statblock = self._score_statblock(chart, norm_charts)
        return {stat_key: float(statblock.scores.get(stat_key, 0.0)) for stat_key in self.dnd_stat_keys}

    def render(self, chart: Any | None, metric_panel_renderer: Callable[..., Any]) -> Any:
        if self.chart_layout is None:
            return self.summary_label
        summary_label = self._ensure_summary_label()
        if chart is None or self.is_placeholder_chart(chart):
            metric_panel_renderer(
                canvas_attr="dnd_prediction_statblock_canvas",
                container_layout=self.chart_layout,
                figsize=(5.5, 2.8),
                title="D&D Statblock",
                draw_fn=self._draw_no_data,
                chart=chart,
            )
            if self.chart_layout.indexOf(summary_label) < 0:
                self.chart_layout.addWidget(summary_label)
            summary_label.setText("<b>Top three:</b> —" if chart is None else "<b>Top three:</b> No data")
            return summary_label
        metric_panel_renderer(
            canvas_attr="dnd_prediction_statblock_canvas",
            container_layout=self.chart_layout,
            figsize=(5.5, 2.8),
            title="D&D Statblock",
            draw_fn=self.draw,
            chart=chart,
        )
        self.cache_metadata(chart)
        if self.chart_layout.indexOf(summary_label) < 0:
            self.chart_layout.addWidget(summary_label)
        if self.info_panel is not None:
            configure_dnd_top_three_summary_label(
                summary_label,
                chart,
                info_panel=self.info_panel,
                before_show=self.before_show,
            )
        return summary_label

def connect_dnd_statblock_popout_pick_handler(
    popout_canvas: Any,
    info_panel: Any,
    *,
    build_info_html: Any,
) -> None:
    """Attach D&D stat-block bar click behavior to the popout chart canvas."""

    def _on_pick(event) -> None:
        artist = getattr(event, "artist", None)
        artist_gid = artist.get_gid() if artist is not None else None
        if not isinstance(artist_gid, str) or not artist_gid.startswith("dnd_stat:"):
            return
        _prefix, stat_key = artist_gid.split(":", 1)
        info_panel.setHtml(build_info_html(stat_key))

    popout_canvas.mpl_connect("pick_event", _on_pick)
