"""D&D prediction chart rendering helpers for Chart View."""

from __future__ import annotations

import html
from typing import Any

from ephemeraldaddy.analysis.dnd.dnd_definitions import DND_STAT_EXPLANATIONS
from ephemeraldaddy.analysis.dnd.dnd_class_axes_v2 import (
    DND_CLASSES,
    DND_CLASS_SUBCLASS_STATS,
    score_class_axes,
    score_class_families,
    score_dnd_classes,
    score_dnd_statblock,
)
from ephemeraldaddy.analysis.dnd.species_assigner_v2 import SpeciesAssigner
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