"""D&D prediction chart rendering helpers for Chart View."""

from __future__ import annotations

import html
from typing import Any, Callable

from PySide6.QtCore import Qt

from ephemeraldaddy.analysis.dnd.dnd_definitions import (
    DND_CLASS_SUBCLASS_STATS,
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
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR, DND_STAT_EARTHTONE_COLORS, get_cycled_earthtone_colors

def draw_dnd_statblock_predictions(ax: Any, chart: Any, *, dnd_stat_keys: tuple[str, ...], apply_standard_bar_axes: Any) -> None:
    statblock = score_dnd_statblock(chart)
    labels = list(dnd_stat_keys)
    values = [float(statblock.scores.get(label, 0.0)) for label in labels]
    bars = ax.barh(labels, values)
    max_value = max(values, default=0.0)
    value_label_offset = max(0.25, max_value * 0.03)
    for idx, bar in enumerate(bars):
        stat_key = labels[idx]
        stat_value = values[idx]
        bar.set_facecolor(DND_STAT_EARTHTONE_COLORS.get(stat_key, "#6fa8dc"))
        bar.set_alpha(0.95)
        bar.set_gid(f"dnd_stat:{stat_key}")
        bar.set_picker(True)
        ax.text(
            stat_value + value_label_offset,
            bar.get_y() + (bar.get_height() / 2.0),
            f"{int(stat_value)}",
            va="center",
            ha="left",
            color="#f5f5f5",
            fontsize=9,
            fontweight="bold",
        )
    ax.set_title("D&D Statblock")
    apply_standard_bar_axes(ax, labels)
    ax.set_xlim(right=max_value + (value_label_offset * 4.0))
    ax.set_xticks([])
    ax.tick_params(axis="x", bottom=False, top=False, labelbottom=False)

def draw_dnd_species_predictions(ax: Any, chart: Any, *, apply_standard_bar_axes: Any) -> None:
    pick = SpeciesAssigner().assign(chart)
    top = pick.top_three[:10]
    labels = [f"{family} ({subtype})" if subtype else family for family, subtype, _score in top]
    values = [float(score) for _family, _subtype, score in top]
    colors = get_cycled_earthtone_colors(len(labels))
    bars = ax.barh(labels, values)
    for idx, bar in enumerate(bars):
        bar.set_facecolor(colors[idx])
        bar.set_alpha(0.95)
    ax.set_title("Top 10 Species")
    apply_standard_bar_axes(ax, labels)


def draw_dnd_classes_predictions(ax: Any, chart: Any, *, apply_standard_bar_axes: Any) -> None:
    axis_scores = score_class_axes(chart)
    family_scores = score_class_families(axis_scores)
    class_scores = score_dnd_classes(axis_scores, family_scores)
    ranked = sorted(class_scores.items(), key=lambda item: item[1], reverse=True)[:10]
    labels = [DND_CLASSES[key].display_name if key in DND_CLASSES else key for key, _ in ranked]
    values = [float(score) for _key, score in ranked]
    colors = get_cycled_earthtone_colors(len(labels))
    bars = ax.barh(labels, values)
    for idx, bar in enumerate(bars):
        bar.set_facecolor(colors[idx])
        bar.set_alpha(0.95)
    ax.set_title("Top 10 Classes")
    apply_standard_bar_axes(ax, labels)



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


def build_dnd_statblock_popout_info_html(chart: Any, stat_key: str) -> str:
    if chart is None:
        return "No chart is available for this D&D stat interpretation."
    stat_definition = _stat_definition_for_key(stat_key)
    if stat_definition is None:
        return f"No D&D stat interpretation data available for {html.escape(str(stat_key))}."

    statblock = score_dnd_statblock(chart)
    normalized_stat_key = str(stat_key or "").strip().upper()
    stat_value = int(statblock.scores.get(normalized_stat_key, 0))
    chart_name = str(getattr(chart, "name", "Chart") or "Chart").strip() or "Chart"
    stat_name = str(stat_definition.get("label") or normalized_stat_key).strip()
    text_color = "#ffffff"
    header_style = f"font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};"
    body_style = f"color:{text_color};font-weight:400;"

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
        )
    if stat_value < 10:
        return (
            f"<div><span style='{header_style}'>{html.escape(chart_name)}'s "
            f"{html.escape(stat_name)} is lower than average, suggesting:</span>"
            f"<div style='{body_style}'>{_html_list(stat_definition.get('low_score_suggests'))}</div></div>"
        )
    return (
        f"<div><span style='{header_style}'>{html.escape(chart_name)}'s "
        f"{html.escape(stat_name)} is about average.</span></div>"
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
    header = "D&D Statblock"
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
    label.setText(build_dnd_top_three_summary_html(chart, linked=True))

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