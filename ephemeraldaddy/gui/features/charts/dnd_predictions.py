"""D&D prediction chart rendering helpers for Chart View."""

from __future__ import annotations

from typing import Any

from ephemeraldaddy.analysis.dnd.dnd_class_axes_v2 import (
    DND_CLASSES,
    score_class_axes,
    score_class_families,
    score_dnd_classes,
    score_dnd_statblock,
)
from ephemeraldaddy.analysis.dnd.species_assigner_v2 import SpeciesAssigner
from ephemeraldaddy.gui.style import DND_STAT_EARTHTONE_COLORS, get_cycled_earthtone_colors


def draw_dnd_statblock_predictions(ax: Any, chart: Any, *, dnd_stat_keys: tuple[str, ...], apply_standard_bar_axes: Any) -> None:
    statblock = score_dnd_statblock(chart)
    labels = list(dnd_stat_keys)
    values = [float(statblock.scores.get(label, 0.0)) for label in labels]
    bars = ax.barh(labels, values)
    for idx, bar in enumerate(bars):
        bar.set_facecolor(DND_STAT_EARTHTONE_COLORS.get(labels[idx], "#6fa8dc"))
        bar.set_alpha(0.95)
    ax.set_title("D&D Statblock")
    apply_standard_bar_axes(ax, labels)


def draw_dnd_species_predictions(ax: Any, chart: Any, *, apply_standard_bar_axes: Any) -> None:
    top = SpeciesAssigner().assign(chart).ranked[:10]
    labels = [family for family, _card in top]
    values = [float(card.score) for _family, card in top]
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
