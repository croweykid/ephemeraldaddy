"""House-based quadrant analytics for Chart View."""

from __future__ import annotations

from collections.abc import Mapping
from html import escape
from numbers import Integral
from typing import Any

from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_house_weights,
    calculate_house_prevalence_counts,
)

QUADRANT_DEFINITIONS: tuple[tuple[str, str, tuple[int, int, int]], ...] = (
    ("I", "Personal Identity", (1, 2, 3)),
    ("II", "Personal Expression", (4, 5, 6)),
    ("III", "Social Identity", (7, 8, 9)),
    ("IV", "Social Expression", (10, 11, 12)),
)

QUADRANT_AXES: dict[str, tuple[str, str]] = {
    "I": ("Personal / Private", "Self-Directed"),
    "II": ("Personal / Private", "Other-Responsive"),
    "III": ("Social / Public", "Other-Responsive"),
    "IV": ("Social / Public", "Self-Directed"),
}

QUADRANT_EXPLANATIONS: dict[str, str] = {
    "I": "Developing, defining, and asserting the individual self through Houses 1–3.",
    "II": "Expressing personal life through roots, creativity, work, and the immediate environment in Houses 4–6.",
    "III": "Developing social identity through partners, other people, and wider perspectives in Houses 7–9.",
    "IV": "Expressing the self publicly through vocation, collective participation, and social contribution in Houses 10–12.",
}


def quadrant_for_house(house: object) -> str | None:
    """Return the Roman-numeral quadrant for a 1-based house number."""
    if isinstance(house, bool):
        return None
    if isinstance(house, Integral):
        house_number = int(house)
    elif isinstance(house, str) and house.strip().isdigit():
        house_number = int(house.strip())
    else:
        return None
    if house_number < 1 or house_number > 12:
        return None
    return QUADRANT_DEFINITIONS[(house_number - 1) // 3][0]


def aggregate_house_values_by_quadrant(
    house_values: Mapping[object, object] | None,
) -> dict[str, float]:
    """Aggregate house-indexed values into the four standard house quadrants."""
    totals = {quadrant: 0.0 for quadrant, _meaning, _houses in QUADRANT_DEFINITIONS}
    for raw_house, raw_value in (house_values or {}).items():
        quadrant = quadrant_for_house(raw_house)
        if quadrant is None:
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        totals[quadrant] += value
    return totals


def calculate_quadrant_prevalence_counts(chart: object) -> dict[str, float]:
    """Return unweighted object counts grouped into quadrants."""
    return aggregate_house_values_by_quadrant(calculate_house_prevalence_counts(chart))


def calculate_dominant_quadrant_weights(chart: object) -> dict[str, float]:
    """Return existing house-dominance weights grouped into quadrants."""
    return aggregate_house_values_by_quadrant(calculate_dominant_house_weights(chart))


def quadrant_percentages(values: Mapping[str, object] | None) -> dict[str, float]:
    """Normalize quadrant values to percentages without dividing by zero."""
    normalized: dict[str, float] = {}
    for quadrant, _meaning, _houses in QUADRANT_DEFINITIONS:
        try:
            normalized[quadrant] = max(0.0, float((values or {}).get(quadrant, 0.0)))
        except (TypeError, ValueError):
            normalized[quadrant] = 0.0
    total = sum(normalized.values())
    if total <= 0:
        return {quadrant: 0.0 for quadrant in normalized}
    return {quadrant: (value / total) * 100.0 for quadrant, value in normalized.items()}


def build_quadrant_export_rows(chart: object, mode: str) -> list[list[object]]:
    """Build the specialized CSV rows, returning no data for an untimed chart."""
    if not chart_uses_houses(chart):
        return []
    values = (
        calculate_dominant_quadrant_weights(chart)
        if mode == "dominant_quadrants"
        else calculate_quadrant_prevalence_counts(chart)
    )
    percentages = quadrant_percentages(values)
    return [
        [
            f"Q{quadrant}",
            meaning,
            f"H{houses[0]}–H{houses[-1]}",
            round(float(values.get(quadrant, 0.0)), 1),
            round(percentages[quadrant], 1),
        ]
        for quadrant, meaning, houses in QUADRANT_DEFINITIONS
    ]


def build_quadrant_info_html(quadrant: str) -> str:
    """Build the Chart Analytics popout description for one quadrant."""
    normalized = str(quadrant or "").strip().upper()
    definition = next(
        (
            (meaning, houses)
            for key, meaning, houses in QUADRANT_DEFINITIONS
            if key == normalized
        ),
        None,
    )
    if definition is None:
        return "<b>Quadrant</b><br>No interpretation is available."

    meaning, houses = definition
    vertical_axis, horizontal_axis = QUADRANT_AXES[normalized]
    explanation = QUADRANT_EXPLANATIONS[normalized]
    house_range = f"Houses {houses[0]}–{houses[-1]}"
    return (
        f"<b>Quadrant {escape(normalized)} — {escape(meaning)}</b><br>"
        f"{escape(house_range)}<br><br>"
        f"<b>Orientation:</b> {escape(vertical_axis)} × {escape(horizontal_axis)}<br><br>"
        f"{escape(explanation)}"
    )


def selected_quadrant_mode(owner: object) -> str:
    """Read the Chart Analytics Quadrants dropdown without depending on Qt types."""
    dropdowns = getattr(owner, "_chart_analysis_chart_dropdowns", {})
    dropdown = dropdowns.get("quadrants") if isinstance(dropdowns, dict) else None
    current_data = getattr(dropdown, "currentData", None)
    if callable(current_data):
        mode = current_data()
        if isinstance(mode, str) and mode:
            return mode
    return "quadrant_prevalence"


def draw_quadrants(
    owner: object,
    ax: Any,
    chart: object,
    *,
    interactive: bool = False,
) -> None:
    """Draw the shared clockwise house-quadrant signature visualization."""
    ax.clear()
    if not chart_uses_houses(chart):
        ax.set_axis_off()
        ax.text(
            0.5,
            0.5,
            "Sorry, quadrants cannot be calculated without birth time. :(",
            transform=ax.transAxes,
            ha="center",
            va="center",
            color="#f5f5f5",
            fontsize=10,
        )
        return

    mode = selected_quadrant_mode(owner)
    values_by_quadrant = (
        calculate_dominant_quadrant_weights(chart)
        if mode == "dominant_quadrants"
        else calculate_quadrant_prevalence_counts(chart)
    )
    percentages = quadrant_percentages(values_by_quadrant)
    quadrant_keys = [quadrant for quadrant, _meaning, _houses in QUADRANT_DEFINITIONS]
    directions = {"I": (-1.0, -1.0), "II": (1.0, -1.0), "III": (1.0, 1.0), "IV": (-1.0, 1.0)}
    points = [
        (directions[key][0] * percentages[key] / 100.0, directions[key][1] * percentages[key] / 100.0)
        for key in quadrant_keys
    ]
    closed_points = [*points, points[0]]
    ax.plot(
        [point[0] for point in closed_points],
        [point[1] for point in closed_points],
        color="#6fa8dc",
        linewidth=2,
        zorder=3,
    )
    ax.fill(
        [point[0] for point in closed_points],
        [point[1] for point in closed_points],
        color="#6fa8dc",
        alpha=0.22,
        zorder=2,
    )
    for diagonal_x, diagonal_y in directions.values():
        ax.plot([0, diagonal_x], [0, diagonal_y], color="#536273", linewidth=0.8, alpha=0.65)
    for quadrant, (point_x, point_y) in zip(quadrant_keys, points, strict=True):
        point, = ax.plot(point_x, point_y, "o", color="#a9d5ff", markersize=7, zorder=4)
        label = ax.text(
            directions[quadrant][0] * 0.76,
            directions[quadrant][1] * 0.76,
            f"Q{quadrant}",
            color="#f5f5f5",
            fontsize=9,
            fontweight="bold",
            ha="center",
            va="center",
        )
        if interactive:
            for artist in (point, label):
                artist.set_gid(f"quadrant:{quadrant}")
                artist.set_picker(True)

    ax.text(0, 1.05, "PUBLIC", color="#aeb8c4", ha="center", va="bottom", fontsize=8)
    ax.text(0, -1.05, "PRIVATE", color="#aeb8c4", ha="center", va="top", fontsize=8)
    ax.text(-1.05, 0, "INDIVIDUAL", color="#aeb8c4", ha="right", va="center", fontsize=8)
    ax.text(1.05, 0, "RELATIONAL", color="#aeb8c4", ha="left", va="center", fontsize=8)
    ax.set_xlim(-1.28, 1.28)
    ax.set_ylim(-1.38, 1.18)
    ax.set_aspect("equal")
    ax.set_axis_off()
    weighted = mode == "dominant_quadrants"
    breakdown = []
    for quadrant in quadrant_keys:
        value = float(values_by_quadrant.get(quadrant, 0.0))
        value_text = f"{value:.1f}" if weighted else f"{value:g}"
        breakdown.append(f"Q{quadrant}  {value_text} · {percentages[quadrant]:.0f}%")
    ax.text(0.5, -0.04, "     ".join(breakdown), transform=ax.transAxes, ha="center", va="top", color="#f5f5f5", fontsize=8)
    mode_title = "Dominant Quadrants" if weighted else "Quadrant Prevalence"
    ax.set_title(mode_title, color="#f5f5f5", fontsize=10, pad=8)
    ax.figure.tight_layout()


def draw_quadrants_popout(owner: object, ax: Any, chart: object) -> None:
    """Draw the registered Quadrants popout with pickable points and labels."""
    draw_quadrants(owner, ax, chart, interactive=True)


def clear_quadrants_display(owner: object) -> None:
    """Clear the Quadrants layout/canvas during the owner's common display reset."""
    layout = getattr(owner, "quadrants_chart_container_layout", None)
    clear_layout_widgets = getattr(owner, "_clear_layout_widgets", None)
    if layout is not None and callable(clear_layout_widgets):
        clear_layout_widgets(layout)
    setattr(owner, "quadrants_canvas", None)
