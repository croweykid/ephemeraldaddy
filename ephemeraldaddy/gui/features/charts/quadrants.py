"""House-based quadrant analytics for Chart View."""

from __future__ import annotations

from collections.abc import Mapping
from html import escape
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
    try:
        house_number = int(house)
    except (TypeError, ValueError):
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


def draw_quadrants_popout(owner: object, ax: Any, chart: object) -> None:
    """Draw the registered Quadrants popout with pickable bars and labels."""
    ax.clear()
    if not chart_uses_houses(chart):
        ax.set_axis_off()
        ax.text(
            0.5,
            0.5,
            "Birth time required for house-based quadrant analysis.",
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
    values = [float(values_by_quadrant.get(quadrant, 0.0)) for quadrant in quadrant_keys]
    bars = ax.bar(quadrant_keys, values, color="#6fa8dc")

    apply_axes = getattr(owner, "_apply_standard_ncv_bar_chart_axes", None)
    if callable(apply_axes):
        apply_axes(ax, quadrant_keys)
    else:
        ax.tick_params(axis="x", labelsize=8, colors="#f5f5f5")
        ax.tick_params(axis="y", labelsize=8, colors="#f5f5f5")

    for bar, quadrant in zip(bars, quadrant_keys, strict=True):
        bar.set_gid(f"quadrant:{quadrant}")
        bar.set_picker(True)
    for label, quadrant in zip(ax.get_xticklabels(), quadrant_keys, strict=True):
        label.set_gid(f"quadrant:{quadrant}")
        label.set_picker(True)

    max_value = max(values) if values else 0.0
    ax.set_ylim(0, max(1.0, max_value * 1.18))
    offset = max(0.05, max_value * 0.025)
    weighted = mode == "dominant_quadrants"
    for bar, quadrant, value in zip(bars, quadrant_keys, values, strict=True):
        value_text = f"{value:.1f}" if weighted else f"{value:g}"
        ax.text(
            bar.get_x() + (bar.get_width() / 2),
            value + offset,
            f"{value_text} · {percentages[quadrant]:.0f}%",
            ha="center",
            va="bottom",
            color="#f5f5f5",
            fontsize=8,
        )
    mode_title = "Weighted" if weighted else "Object Count"
    ax.set_title(f"Quadrants — {mode_title}", color="#f5f5f5", fontsize=10, pad=8)
    ax.figure.tight_layout()


def clear_quadrants_display(owner: object) -> None:
    """Clear the Quadrants layout/canvas during the owner's common display reset."""
    layout = getattr(owner, "quadrants_chart_container_layout", None)
    clear_layout_widgets = getattr(owner, "_clear_layout_widgets", None)
    if layout is not None and callable(clear_layout_widgets):
        clear_layout_widgets(layout)
    setattr(owner, "quadrants_canvas", None)


def install_quadrants_owner_reset_hook(controller: object) -> None:
    """Extend MainWindow's common display reset without duplicating its reset logic."""
    owner = getattr(controller, "_owner", None)
    if owner is None or getattr(owner, "_quadrants_reset_hook_installed", False):
        return
    clear_chart_displays = getattr(owner, "_clear_chart_displays", None)
    if not callable(clear_chart_displays):
        return

    def clear_with_quadrants(*args: object, **kwargs: object) -> object:
        result = clear_chart_displays(*args, **kwargs)
        clear_quadrants_display(owner)
        return result

    owner._clear_chart_displays = clear_with_quadrants
    owner._quadrants_reset_hook_installed = True


def install_quadrants_controller_bridge() -> None:
    """Attach the reset hook at the controller's existing owner-hook installation seam."""
    from ephemeraldaddy.gui.features.controllers.main_window import ChartAnalysisSectionsController

    if getattr(ChartAnalysisSectionsController, "_quadrants_reset_bridge_installed", False):
        return
    original_install = ChartAnalysisSectionsController._install_quadrants_refresh_hook

    def install_with_reset(self: object) -> None:
        original_install(self)
        install_quadrants_owner_reset_hook(self)

    ChartAnalysisSectionsController._install_quadrants_refresh_hook = install_with_reset
    ChartAnalysisSectionsController._quadrants_reset_bridge_installed = True
