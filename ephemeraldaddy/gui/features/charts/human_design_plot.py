from __future__ import annotations

from matplotlib.patches import Rectangle
from matplotlib.figure import Figure

from ephemeraldaddy.analysis.human_design_reference import HD_CENTERS
from ephemeraldaddy.core.human_design_system import CHANNELS
from ephemeraldaddy.core.human_design_system import HumanDesignResult


BASE_CENTER_POSITIONS: dict[str, tuple[float, float]] = {
    "Head": (0.5, 1.0),
    "Ajna": (0.5, 0.8),
    "Throat": (0.5, 0.6),
    "G": (0.5, 0.4),
    "Ego": (0.74, 0.4),
    "Spleen": (0.26, 0.26),
    "Solar Plexus": (0.74, 0.2),
    "Sacral": (0.5, 0.2),
    "Root": (0.5, 0.00),
}

CENTER_LAYOUT_ANCHOR_X = 0.5
CENTER_LAYOUT_ANCHOR_Y = 0.94
CENTER_HORIZONTAL_SPREAD = 1.5
CENTER_VERTICAL_SPREAD = 1.2
CENTER_DEPTH_RIGHT_DRIFT = 0.02

CENTER_COLUMN_CENTERS = frozenset({"Head", "Ajna", "Throat", "G", "Sacral", "Root"})

def _spread_center_positions(base_positions: dict[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
    spread_positions: dict[str, tuple[float, float]] = {}
    for center_name, (x_value, y_value) in base_positions.items():
        depth = CENTER_LAYOUT_ANCHOR_Y - y_value
        spread_x = (
            CENTER_LAYOUT_ANCHOR_X
            + ((x_value - CENTER_LAYOUT_ANCHOR_X) * CENTER_HORIZONTAL_SPREAD)
            + (depth * CENTER_DEPTH_RIGHT_DRIFT)
        )
        if center_name in CENTER_COLUMN_CENTERS:
            spread_x = CENTER_LAYOUT_ANCHOR_X
        spread_y = CENTER_LAYOUT_ANCHOR_Y - (depth * CENTER_VERTICAL_SPREAD)
        spread_positions[center_name] = (spread_x, spread_y)
    return spread_positions


CENTER_POSITIONS = _spread_center_positions(BASE_CENTER_POSITIONS)

CENTER_HALF_WIDTH = 0.08
CENTER_HALF_HEIGHT = 0.045
CHANNEL_CENTER_MARGIN = 0.012
CHANNEL_INACTIVE_COLOR = "#5e5e5e"
CHANNEL_PERSONALITY_ACTIVE_COLOR = "#5dc26a"
CHANNEL_DESIGN_ACTIVE_COLOR = "#d65b5b"
DUAL_ACTIVATION_RED_DASH_PATTERN = (2.0, 2.0)
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

CENTER_FILL_COLORS: dict[str, str] = {center_name: center_data["color"] for center_name, center_data in HD_CENTERS.items()}

CHANNEL_SPACING = 0.014
CHANNEL_EXTRA_SPACING_PIXELS = 6.0
BODYGRAPH_VERTICAL_OFFSET = -0.07
BODYGRAPH_CONTENT_SCALE = 0.74 #scales the bodygraph chart
BODYGRAPH_AXES_BOUNDS = (0.02, 0.02, 0.66, 0.96)
ACTIVATION_AXES_BOUNDS = (0.70, 0.02, 0.28, 0.96)


def _offset_center_y(y_value: float) -> float:
    return y_value + BODYGRAPH_VERTICAL_OFFSET


def _center_sort_key(center_name: str) -> tuple[float, float]:
    x, y = CENTER_POSITIONS[center_name]
    y = _offset_center_y(y)
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


def _offset_segment_in_display_pixels(
    ax: object,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    normal_x: float,
    normal_y: float,
    offset_pixels: float,
) -> tuple[float, float, float, float]:
    if abs(offset_pixels) < 1e-9:
        return x1, y1, x2, y2
    transform = ax.transData
    p1_display = transform.transform((x1, y1))
    p2_display = transform.transform((x2, y2))
    p_mid_display = transform.transform(((x1 + x2) * 0.5, (y1 + y2) * 0.5))
    p_normal_display = transform.transform((((x1 + x2) * 0.5) + normal_x, (((y1 + y2) * 0.5) + normal_y)))
    normal_display_x = p_normal_display[0] - p_mid_display[0]
    normal_display_y = p_normal_display[1] - p_mid_display[1]
    normal_display_length = (normal_display_x ** 2 + normal_display_y ** 2) ** 0.5 or 1.0
    unit_normal_display_x = normal_display_x / normal_display_length
    unit_normal_display_y = normal_display_y / normal_display_length
    display_offset_x = unit_normal_display_x * offset_pixels
    display_offset_y = unit_normal_display_y * offset_pixels
    inv_transform = transform.inverted()
    p1_data = inv_transform.transform((p1_display[0] + display_offset_x, p1_display[1] + display_offset_y))
    p2_data = inv_transform.transform((p2_display[0] + display_offset_x, p2_display[1] + display_offset_y))
    return p1_data[0], p1_data[1], p2_data[0], p2_data[1]


PAIR_CHANNEL_ORDER_LEFT_TO_RIGHT: dict[tuple[str, str], list[tuple[int, int]]] = {
    ("Ajna", "Head"): [(64, 47), (61, 24), (63, 4)],
    ("Ajna", "Throat"): [(17, 62), (43, 23), (11, 56)],
    ("G", "Sacral"): [(15, 5), (2, 14)],
    ("G", "Throat"): [(20,10),(31, 7), (8, 1), (13, 33)],
    ("Root", "Sacral"): [(42, 53), (3, 60), (9, 52)],
    ("Root", "Solar Plexus"): [(19, 49), (39, 55), (30, 41)],
    ("Root", "Spleen"): [(18, 58), (28, 38), (32, 54)],
    ("Sacral", "Spleen"): [(27, 50), (34, 57)],
    ("Spleen", "Throat"): [(16, 48), (20, 57)],
}


def draw_human_design_chart(
    figure: Figure,
    hd_result: HumanDesignResult,
    *,
    chart_theme_colors: dict[str, str],
) -> None:
    figure.clear()
    figure.patch.set_facecolor(chart_theme_colors["background"])
    ax = figure.add_axes(BODYGRAPH_AXES_BOUNDS)
    ax.set_facecolor(chart_theme_colors["background"])
    text_ax = figure.add_axes(ACTIVATION_AXES_BOUNDS)
    text_ax.set_facecolor(chart_theme_colors["background"])
    center_min_x = min(x - CENTER_HALF_WIDTH for _center, (x, _y) in BASE_CENTER_POSITIONS.items()) - 0.03
    center_max_x = max(x + CENTER_HALF_WIDTH for _center, (x, _y) in BASE_CENTER_POSITIONS.items()) + 0.03
    center_min_y = min(_offset_center_y(y) - CENTER_HALF_HEIGHT for _center, (_x, y) in BASE_CENTER_POSITIONS.items()) - 0.03
    center_max_y = max(_offset_center_y(y) + CENTER_HALF_HEIGHT for _center, (_x, y) in BASE_CENTER_POSITIONS.items()) + 0.03
    content_center_x = (center_min_x + center_max_x) / 2.0
    content_center_y = (center_min_y + center_max_y) / 2.0
    scaled_half_width = ((center_max_x - center_min_x) / BODYGRAPH_CONTENT_SCALE) / 2.0
    scaled_half_height = ((center_max_y - center_min_y) / BODYGRAPH_CONTENT_SCALE) / 2.0
    ax.set_xlim(content_center_x - scaled_half_width, content_center_x + scaled_half_width)
    ax.set_ylim(content_center_y - scaled_half_height, content_center_y + scaled_half_height)
    ax.margins(x=0.0, y=0.0)
    ax.axis("off")
    text_ax.set_xlim(0.0, 1.0)
    text_ax.set_ylim(0.0, 1.0)
    text_ax.axis("off")
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
        explicit_order = PAIR_CHANNEL_ORDER_LEFT_TO_RIGHT.get(pair_key)
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

    personality_gate_set = {activation.gate for activation in hd_result.personality_activations}
    design_gate_set = {activation.gate for activation in hd_result.design_activations}

    def _draw_gate_segment(
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        gate: int,
    ) -> None:
        has_personality = gate in personality_gate_set
        has_design = gate in design_gate_set
        if not has_personality and not has_design:
            ax.plot(
                [start_x, end_x],
                [start_y, end_y],
                color=CHANNEL_INACTIVE_COLOR,
                linewidth=3.0,
                alpha=0.95,
                gid=f"gate-segment:{gate}",
            )
            return
        if has_personality and has_design:
            ax.plot(
                [start_x, end_x],
                [start_y, end_y],
                color=CHANNEL_PERSONALITY_ACTIVE_COLOR,
                linewidth=3.0,
                alpha=0.95,
                gid=f"gate-segment:{gate}",
            )
            ax.plot(
                [start_x, end_x],
                [start_y, end_y],
                color=CHANNEL_DESIGN_ACTIVE_COLOR,
                linewidth=2.4,
                alpha=0.95,
                linestyle=(0, DUAL_ACTIVATION_RED_DASH_PATTERN),
                solid_capstyle="butt",
                dash_capstyle="butt",
                gid=f"gate-segment:{gate}",
            )
            return
        active_color = CHANNEL_PERSONALITY_ACTIVE_COLOR if has_personality else CHANNEL_DESIGN_ACTIVE_COLOR
        ax.plot(
            [start_x, end_x],
            [start_y, end_y],
            color=active_color,
            linewidth=3.0,
            alpha=0.95,
            gid=f"gate-segment:{gate}",
        )

    for gate_a, gate_b, center_a, center_b, channel_index, channel_count in ordered_channels:
        channel_key = _channel_key(gate_a, gate_b)
        x1, y1 = CENTER_POSITIONS[center_a]
        x2, y2 = CENTER_POSITIONS[center_b]
        y1 = _offset_center_y(y1)
        y2 = _offset_center_y(y2)

        if channel_key == (10, 34):
            # Drawn as part of the 20-34 custom bridge geometry (with gate 10).
            continue

        if channel_key == (20, 34):
            sacral_x, sacral_y = CENTER_POSITIONS["Sacral"]
            throat_x, throat_y = CENTER_POSITIONS["Throat"]
            g_x, g_y = CENTER_POSITIONS["G"]
            sacral_y = _offset_center_y(sacral_y)
            throat_y = _offset_center_y(throat_y)
            g_y = _offset_center_y(g_y)
            start_x = sacral_x - CENTER_HALF_WIDTH - CHANNEL_CENTER_MARGIN
            start_y = sacral_y
            end_x = throat_x - CENTER_HALF_WIDTH - CHANNEL_CENTER_MARGIN
            end_y = throat_y
            elbow_x = min(start_x, end_x) - 0.065
            elbow_y = g_y
            g_bridge_end_x = g_x - CENTER_HALF_WIDTH - CHANNEL_CENTER_MARGIN

            lower_gate = 34
            upper_gate = 20
            bridge_gate = 10
            _draw_gate_segment(start_x, start_y, elbow_x, elbow_y, lower_gate)
            _draw_gate_segment(elbow_x, elbow_y, end_x, end_y, upper_gate)
            _draw_gate_segment(elbow_x, elbow_y, g_bridge_end_x, elbow_y, bridge_gate)
            ax.text(
                start_x + ((elbow_x - start_x) * 0.55),
                start_y + ((elbow_y - start_y) * 0.55),
                f"{lower_gate}",
                color="#ffffff",
                fontsize=6,
                ha="center",
                va="center",
            )
            ax.text(
                elbow_x + ((end_x - elbow_x) * 0.45),
                elbow_y + ((end_y - elbow_y) * 0.45),
                f"{upper_gate}",
                color="#ffffff",
                fontsize=6,
                ha="center",
                va="center",
            )
            ax.text(
                elbow_x + ((g_bridge_end_x - elbow_x) * 0.6),
                elbow_y,
                f"{bridge_gate}",
                color="#ffffff",
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
            left_to_right_scales = sorted(
                offset_scales,
                key=lambda scale: (
                    (((x1 + x2) * 0.5) + (normal_x * CHANNEL_SPACING * scale)),
                    -(((y1 + y2) * 0.5) + (normal_y * CHANNEL_SPACING * scale)),
                ),
            )
            offset_distance = CHANNEL_SPACING * left_to_right_scales[channel_index]
            x1 += normal_x * offset_distance
            y1 += normal_y * offset_distance
            x2 += normal_x * offset_distance
            y2 += normal_y * offset_distance
            pixel_offset_distance = CHANNEL_EXTRA_SPACING_PIXELS * left_to_right_scales[channel_index]
            x1, y1, x2, y2 = _offset_segment_in_display_pixels(
                ax,
                x1,
                y1,
                x2,
                y2,
                normal_x,
                normal_y,
                pixel_offset_distance,
            )

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
        _draw_gate_segment(x1, y1, mid_x, mid_y, gate_a)
        _draw_gate_segment(mid_x, mid_y, x2, y2, gate_b)
        ax.text(
            x1 + ((mid_x - x1) * 0.6),
            y1 + ((mid_y - y1) * 0.6),
            f"{gate_a}",
            color="#ffffff",
            fontsize=6,
            ha="center",
            va="center",
        )
        ax.text(
            mid_x + ((x2 - mid_x) * 0.4),
            mid_y + ((y2 - mid_y) * 0.4),
            f"{gate_b}",
            color="#ffffff",
            fontsize=6,
            ha="center",
            va="center",
        )

    for center_name, (x, y) in CENTER_POSITIONS.items():
        y = _offset_center_y(y)
        defined = center_name in hd_result.defined_centers
        edge = "#c8914f" if defined else chart_theme_colors["spine"]
        fill = CENTER_FILL_COLORS.get(center_name, "#2f3d45") #"#2f3d45" if defined else "#2a2a2a"
        ax.add_patch(
            Rectangle(
                (x - 0.08, y - 0.045),
                CENTER_HALF_WIDTH * 2,
                CENTER_HALF_HEIGHT * 2,
                linewidth=1.4,
                edgecolor=edge,
                facecolor=fill,
                alpha=1.0 if defined else 0.15,
            )
        )
        ax.text(x, y, center_name, color="#ffffff", fontsize=7, ha="center", va="center", fontweight="bold")

    
    text_ax.text(0.52, 0.98, "PERSONALITY", color="#f5f5f5", fontsize=7, ha="left", va="top", fontweight="bold")
    for idx, activation in enumerate(hd_result.personality_activations):
        text_ax.text(
            0.52,
            0.95 - (idx * 0.028),
            f"{activation.body:>10}  {activation.gate}.{activation.line}.{activation.color}.{activation.tone}.{activation.base}",
            color=BODY_TEXT_COLOR.get(activation.body, "#f0f0f0"),
            fontsize=6,
            ha="left",
            va="top",
        )

    text_ax.text(0.02, 0.98, "DESIGN", color="#f5f5f5", fontsize=7, ha="left", va="top", fontweight="bold")
    for idx, activation in enumerate(hd_result.design_activations):
        text_ax.text(
            0.02,
            0.95 - (idx * 0.028),
            f"{activation.body:>10}  {activation.gate}.{activation.line}.{activation.color}.{activation.tone}.{activation.base}",
            color=BODY_TEXT_COLOR.get(activation.body, "#f0f0f0"),
            fontsize=6,
            ha="left",
            va="top",
        )
