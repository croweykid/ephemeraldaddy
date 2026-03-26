from __future__ import annotations

from matplotlib.patches import Rectangle
from matplotlib.figure import Figure

from ephemeraldaddy.core.human_design_system import HumanDesignResult


CENTER_POSITIONS: dict[str, tuple[float, float]] = {
    "Head": (0.5, 0.93),
    "Ajna": (0.5, 0.80),
    "Throat": (0.5, 0.66),
    "G": (0.5, 0.51),
    "Ego": (0.67, 0.51),
    "Spleen": (0.33, 0.38),
    "Solar Plexus": (0.67, 0.38),
    "Sacral": (0.5, 0.36),
    "Root": (0.5, 0.19),
}

STYLE_COLOR = {"black": "#101010", "red": "#d14d4d", "combined": "#8c4fd1"}


def draw_human_design_chart(
    figure: Figure,
    hd_result: HumanDesignResult,
    *,
    chart_theme_colors: dict[str, str],
) -> None:
    figure.clear()
    ax = figure.add_subplot(111)
    ax.set_facecolor(chart_theme_colors["background"])
    figure.patch.set_facecolor(chart_theme_colors["background"])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    gate_style: dict[int, str] = {}
    for activation in hd_result.personality_activations:
        gate_style[activation.gate] = "black" if gate_style.get(activation.gate) != "red" else "combined"
    for activation in hd_result.design_activations:
        gate_style[activation.gate] = "red" if gate_style.get(activation.gate) != "black" else "combined"

    for gate_a, gate_b, center_a, center_b in hd_result.defined_channels:
        x1, y1 = CENTER_POSITIONS[center_a]
        x2, y2 = CENTER_POSITIONS[center_b]
        style_a = gate_style.get(gate_a, "black")
        style_b = gate_style.get(gate_b, "black")
        channel_style = "combined" if style_a != style_b else style_a
        ax.plot([x1, x2], [y1, y2], color=STYLE_COLOR[channel_style], linewidth=3.0, alpha=0.95)
        ax.text((x1 + x2) / 2, (y1 + y2) / 2, f"{gate_a}-{gate_b}", color="#d6d6d6", fontsize=6, ha="center", va="center")

    for center_name, (x, y) in CENTER_POSITIONS.items():
        defined = center_name in hd_result.defined_centers
        edge = "#c8914f" if defined else chart_theme_colors["spine"]
        fill = "#2f3d45" if defined else "#2a2a2a"
        ax.add_patch(
            Rectangle(
                (x - 0.08, y - 0.045),
                0.16,
                0.09,
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
            color=STYLE_COLOR.get(activation.style, "#f0f0f0"),
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
            color=STYLE_COLOR.get(activation.style, "#f0f0f0"),
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
