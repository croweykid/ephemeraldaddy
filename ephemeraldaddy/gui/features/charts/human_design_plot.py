from __future__ import annotations

from matplotlib.patches import Rectangle
from matplotlib.figure import Figure

from ephemeraldaddy.core.human_design_system import CHANNELS
from ephemeraldaddy.core.human_design_system import HumanDesignResult


CENTER_POSITIONS: dict[str, tuple[float, float]] = {
    "Head": (0.5, 1.05),
    "Ajna": (0.5, 0.85),
    "Throat": (0.5, 0.67),
    "G": (0.5, 0.50),
    "Ego": (0.74, 0.50),
    "Spleen": (0.26, 0.36),
    "Solar Plexus": (0.74, 0.33),
    "Sacral": (0.5, 0.32),
    "Root": (0.5, 0.13),
}

CENTER_HALF_WIDTH = 0.08
CENTER_HALF_HEIGHT = 0.045
CHANNEL_CENTER_MARGIN = 0.012
CHANNEL_INACTIVE_COLOR = "#5e5e5e"
CHANNEL_ACTIVE_COLOR = "#5dc26a"
BODY_TEXT_COLOR: dict[str, str] = {
    "Sun": "#f5c542",
    "Earth": "#c8914f",
    "Moon": "#6ea8ff",
    "Rahu": "#b07bff",
    "Ketu": "#8f5fd6",
    "Mercury": "#6ccf91",
    "Venus": "#e784d5",
    "Mars": "#e06c5b",
    "Jupiter": "#e0a95b",
    "Saturn": "#9fa7b3",
    "Uranus": "#6bc7d9",
    "Neptune": "#5d7ccf",
    "Pluto": "#b86b8f",
}


def draw_human_design_chart(
    figure: Figure,
    hd_result: HumanDesignResult,
    *,
    chart_theme_colors: dict[str, str],
) -> None:
    figure.clear()
    ax = figure.add_axes((0.0, 0.0, 1.0, 1.0))
    figure.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)
    ax.set_facecolor(chart_theme_colors["background"])
    figure.patch.set_facecolor(chart_theme_colors["background"])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.margins(x=0.0, y=0.0)
    ax.axis("off")

    unique_channels: list[tuple[int, int, str, str]] = []
    seen_channel_pairs: set[tuple[int, int]] = set()
    for gate_a, gate_b, center_a, center_b in CHANNELS:
        channel_key = tuple(sorted((gate_a, gate_b)))
        if channel_key in seen_channel_pairs:
            continue
        seen_channel_pairs.add(channel_key)
        unique_channels.append((gate_a, gate_b, center_a, center_b))

    center_pair_totals: dict[tuple[str, str], int] = {}
    for _gate_a, _gate_b, center_a, center_b in unique_channels:
        center_pair_key = tuple(sorted((center_a, center_b)))
        center_pair_totals[center_pair_key] = center_pair_totals.get(center_pair_key, 0) + 1

    center_pair_seen: dict[tuple[str, str], int] = {}
    for gate_a, gate_b, center_a, center_b in unique_channels:
        x1, y1 = CENTER_POSITIONS[center_a]
        x2, y2 = CENTER_POSITIONS[center_b]
        center_pair_key = tuple(sorted((center_a, center_b)))
        channel_count = center_pair_totals[center_pair_key]
        channel_index = center_pair_seen.get(center_pair_key, 0)
        center_pair_seen[center_pair_key] = channel_index + 1
        if channel_count > 1:
            dx = x2 - x1
            dy = y2 - y1
            segment_length = (dx ** 2 + dy ** 2) ** 0.5 or 1.0
            normal_x = -dy / segment_length
            normal_y = dx / segment_length
            offset_scale = channel_index - ((channel_count - 1) / 2)
            offset_distance = 0.014 * offset_scale
            x1 += normal_x * offset_distance
            y1 += normal_y * offset_distance
            x2 += normal_x * offset_distance
            y2 += normal_y * offset_distance

        dx = x2 - x1
        dy = y2 - y1
        segment_length = (dx ** 2 + dy ** 2) ** 0.5 or 1.0
        ux = dx / segment_length
        uy = dy / segment_length
        edge_distance_a = min(
            CENTER_HALF_WIDTH / (abs(ux) or 1e-6),
            CENTER_HALF_HEIGHT / (abs(uy) or 1e-6),
        )
        edge_distance_b = min(
            CENTER_HALF_WIDTH / (abs(ux) or 1e-6),
            CENTER_HALF_HEIGHT / (abs(uy) or 1e-6),
        )
        clipped_x1 = x1 + (ux * (edge_distance_a + CHANNEL_CENTER_MARGIN))
        clipped_y1 = y1 + (uy * (edge_distance_a + CHANNEL_CENTER_MARGIN))
        clipped_x2 = x2 - (ux * (edge_distance_b + CHANNEL_CENTER_MARGIN))
        clipped_y2 = y2 - (uy * (edge_distance_b + CHANNEL_CENTER_MARGIN))
        if ((clipped_x2 - clipped_x1) ** 2 + (clipped_y2 - clipped_y1) ** 2) < 1e-6:
            continue
        x1, y1, x2, y2 = clipped_x1, clipped_y1, clipped_x2, clipped_y2
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        gate_a_active = gate_a in hd_result.active_gates
        gate_b_active = gate_b in hd_result.active_gates
        ax.plot(
            [x1, mid_x],
            [y1, mid_y],
            color=CHANNEL_ACTIVE_COLOR if gate_a_active else CHANNEL_INACTIVE_COLOR,
            linewidth=3.0,
            alpha=0.95,
        )
        ax.plot(
            [mid_x, x2],
            [mid_y, y2],
            color=CHANNEL_ACTIVE_COLOR if gate_b_active else CHANNEL_INACTIVE_COLOR,
            linewidth=3.0,
            alpha=0.95,
        )
        ax.text(
            x1 + ((mid_x - x1) * 0.6),
            y1 + ((mid_y - y1) * 0.6),
            f"{gate_a}",
            color="#d6d6d6",
            fontsize=6,
            ha="center",
            va="center",
        )
        ax.text(
            mid_x + ((x2 - mid_x) * 0.4),
            mid_y + ((y2 - mid_y) * 0.4),
            f"{gate_b}",
            color="#d6d6d6",
            fontsize=6,
            ha="center",
            va="center",
        )

    for center_name, (x, y) in CENTER_POSITIONS.items():
        defined = center_name in hd_result.defined_centers
        edge = "#c8914f" if defined else chart_theme_colors["spine"]
        fill = "#2f3d45" if defined else "#2a2a2a"
        ax.add_patch(
            Rectangle(
                (x - 0.08, y - 0.045),
                CENTER_HALF_WIDTH * 2,
                CENTER_HALF_HEIGHT * 2,
                linewidth=1.4,
                edgecolor=edge,
                facecolor=fill,
            )
        )
        ax.text(x, y, center_name, color="#ffffff", fontsize=7, ha="center", va="center", fontweight="bold")

    ax.text(0.03, 0.97, "PERSONALITY", color="#f5f5f5", fontsize=7, ha="left", va="top", fontweight="bold")
    for idx, activation in enumerate(hd_result.personality_activations):
        ax.text(
            0.03,
            0.94 - (idx * 0.028),
            f"{activation.body:>10}  {activation.gate}.{activation.line}.{activation.color}.{activation.tone}.{activation.base}",
            color=BODY_TEXT_COLOR.get(activation.body, "#f0f0f0"),
            fontsize=6,
            ha="left",
            va="top",
        )

    ax.text(0.72, 0.97, "DESIGN", color="#f5f5f5", fontsize=7, ha="left", va="top", fontweight="bold")
    for idx, activation in enumerate(hd_result.design_activations):
        ax.text(
            0.72,
            0.94 - (idx * 0.028),
            f"{activation.body:>10}  {activation.gate}.{activation.line}.{activation.color}.{activation.tone}.{activation.base}",
            color=BODY_TEXT_COLOR.get(activation.body, "#f0f0f0"),
            fontsize=6,
            ha="left",
            va="top",
        )

    ax.text(
        0.5,
        0.06,
        (
            f"Type: {hd_result.hd_type}   Authority: {hd_result.authority}   "
            f"Profile: {hd_result.profile}   {hd_result.split_definition}"
        ),
        color="#f4e0c6",
        fontsize=7,
        ha="center",
        va="center",
        fontweight="bold",
    )
    ax.text(
        0.5,
        0.03,
        f"Strategy: {hd_result.strategy}   Incarnation: {hd_result.incarnation_cross}",
        color="#f4e0c6",
        fontsize=6,
        ha="center",
        va="center",
    )
