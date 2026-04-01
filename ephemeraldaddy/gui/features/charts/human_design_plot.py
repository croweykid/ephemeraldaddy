from __future__ import annotations

from matplotlib.patches import Rectangle
from matplotlib.figure import Figure

from ephemeraldaddy.core.human_design_system import CHANNELS
from ephemeraldaddy.core.human_design_system import HumanDesignResult


CENTER_POSITIONS: dict[str, tuple[float, float]] = {
    "Head": (0.5, 0.94),
    "Ajna": (0.5, 0.772),
    "Throat": (0.5, 0.604),
    "G": (0.5, 0.436),
    "Ego": (0.74, 0.436),
    "Spleen": (0.26, 0.30),
    "Solar Plexus": (0.74, 0.30),
    "Sacral": (0.5, 0.268),
    "Root": (0.5, 0.10),
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

CHART_CENTER = (0.5, 0.5)
CHANNEL_SPACING = 0.014


def _center_sort_key(center_name: str) -> tuple[float, float]:
    x, y = CENTER_POSITIONS[center_name]
    return (-y, x)


def _canonicalize_channel(
    gate_a: int,
    gate_b: int,
    center_a: str,
    center_b: str,
) -> tuple[int, int, str, str]:
    if _center_sort_key(center_a) <= _center_sort_key(center_b):
        return gate_a, gate_b, center_a, center_b
    return gate_b, gate_a, center_b, center_a


def _channel_key(gate_a: int, gate_b: int) -> tuple[int, int]:
    return tuple(sorted((gate_a, gate_b)))


PAIR_CHANNEL_ORDER_INNER_TO_OUTER: dict[tuple[str, str], list[tuple[int, int]]] = {
    ("Root", "Sacral"): [(3, 60), (42, 53), (9, 52)],
    ("Root", "Solar Plexus"): [(19, 49), (39, 55), (30, 41)],
    ("Root", "Spleen"): [(32, 54), (28, 38), (18, 58)],
    ("Sacral", "Spleen"): [(27, 50), (34, 57)],
}


def draw_human_design_chart(
    figure: Figure,
    hd_result: HumanDesignResult,
    *,
    chart_theme_colors: dict[str, str],
) -> None:
    figure.clear()
    ax = figure.add_axes((0.10, 0.10, 0.80, 0.80))
    ax.set_facecolor(chart_theme_colors["background"])
    figure.patch.set_facecolor(chart_theme_colors["background"])
    ax.set_xlim(0, 1)
    center_min_y = min(y - CENTER_HALF_HEIGHT for _center, (_x, y) in CENTER_POSITIONS.items())
    center_max_y = max(y + CENTER_HALF_HEIGHT for _center, (_x, y) in CENTER_POSITIONS.items())
    vertical_padding = 0.02
    ax.set_ylim(center_min_y - vertical_padding, center_max_y + vertical_padding)
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

    channels_by_pair: dict[tuple[str, str], list[tuple[int, int, str, str]]] = {}
    for gate_a, gate_b, center_a, center_b in unique_channels:
        normalized = _canonicalize_channel(gate_a, gate_b, center_a, center_b)
        pair_key = tuple(sorted((normalized[2], normalized[3])))
        channels_by_pair.setdefault(pair_key, []).append(normalized)

    ordered_channels: list[tuple[int, int, str, str, int, int]] = []
    for pair_key, pair_channels in channels_by_pair.items():
        channel_count = len(pair_channels)
        default_order = sorted(pair_channels, key=lambda channel: _channel_key(channel[0], channel[1]))
        explicit_order = PAIR_CHANNEL_ORDER_INNER_TO_OUTER.get(pair_key)
        if explicit_order:
            preferred_rank = {_channel_key(a, b): idx for idx, (a, b) in enumerate(explicit_order)}
            default_rank_base = len(preferred_rank)
            pair_ordered = sorted(
                pair_channels,
                key=lambda channel: (
                    preferred_rank.get(_channel_key(channel[0], channel[1]), default_rank_base),
                    _channel_key(channel[0], channel[1]),
                ),
            )
        else:
            pair_ordered = default_order
        for slot_index, channel in enumerate(pair_ordered):
            ordered_channels.append((*channel, slot_index, channel_count))

    for gate_a, gate_b, center_a, center_b, channel_index, channel_count in ordered_channels:
        channel_key = _channel_key(gate_a, gate_b)
        x1, y1 = CENTER_POSITIONS[center_a]
        x2, y2 = CENTER_POSITIONS[center_b]

        if channel_key == (20, 34):
            sacral_x, sacral_y = CENTER_POSITIONS["Sacral"]
            throat_x, throat_y = CENTER_POSITIONS["Throat"]
            start_x = sacral_x - CENTER_HALF_WIDTH - CHANNEL_CENTER_MARGIN
            start_y = sacral_y
            end_x = throat_x - CENTER_HALF_WIDTH - CHANNEL_CENTER_MARGIN
            end_y = throat_y
            elbow_x = min(start_x, end_x) - 0.065
            elbow_y = (start_y + end_y) * 0.5

            lower_gate = 34
            upper_gate = 20
            lower_gate_active = lower_gate in hd_result.active_gates
            upper_gate_active = upper_gate in hd_result.active_gates
            ax.plot(
                [start_x, elbow_x],
                [start_y, elbow_y],
                color=CHANNEL_ACTIVE_COLOR if lower_gate_active else CHANNEL_INACTIVE_COLOR,
                linewidth=3.0,
                alpha=0.95,
            )
            ax.plot(
                [elbow_x, end_x],
                [elbow_y, end_y],
                color=CHANNEL_ACTIVE_COLOR if upper_gate_active else CHANNEL_INACTIVE_COLOR,
                linewidth=3.0,
                alpha=0.95,
            )
            ax.text(
                start_x + ((elbow_x - start_x) * 0.55),
                start_y + ((elbow_y - start_y) * 0.55),
                f"{lower_gate}",
                color="#d6d6d6",
                fontsize=6,
                ha="center",
                va="center",
            )
            ax.text(
                elbow_x + ((end_x - elbow_x) * 0.45),
                elbow_y + ((end_y - elbow_y) * 0.45),
                f"{upper_gate}",
                color="#d6d6d6",
                fontsize=6,
                ha="center",
                va="center",
            )
            continue

        if channel_count > 1:
            dx = x2 - x1
            dy = y2 - y1
            segment_length = (dx ** 2 + dy ** 2) ** 0.5 or 1.0
            normal_x = -dy / segment_length
            normal_y = dx / segment_length
            offset_scales = [idx - ((channel_count - 1) / 2) for idx in range(channel_count)]
            inner_to_outer_scales = sorted(
                offset_scales,
                key=lambda scale: (
                    (
                        ((((x1 + x2) * 0.5) + (normal_x * CHANNEL_SPACING * scale) - CHART_CENTER[0]) ** 2)
                        + ((((y1 + y2) * 0.5) + (normal_y * CHANNEL_SPACING * scale) - CHART_CENTER[1]) ** 2)
                    ),
                    abs(scale),
                ),
            )
            offset_distance = CHANNEL_SPACING * inner_to_outer_scales[channel_index]
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

    
    ax.text(0.86, 0.97, "PERSONALITY", color="#f5f5f5", fontsize=7, ha="left", va="top", fontweight="bold")
    for idx, activation in enumerate(hd_result.personality_activations):
        ax.text(
            0.86,
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
