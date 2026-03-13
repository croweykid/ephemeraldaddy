from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge

from ..core.interpretations import PLANET_COLORS, SIGN_COLORS

PLANET_DIAMETERS = {
    "Sun": 350,
    "Moon": 545,
    "Mercury": 765,
    "Venus": 945,
    "Mars": 1140,
    "Jupiter": 1270,
    "Saturn": 1370,
    "Uranus": 1430,
    "Neptune": 1540,
    "Pluto": 1630,
}

ZODIAC_SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]


# Aries begins in the 12-1 o'clock sector (60° to 90° in matplotlib's coordinate space).
ARIES_THETA_START = 60
SLICE_SPAN_DEGREES = 30
ZODIAC_OVERLAY_ZORDER = 100


def _fit_window_to_screen(fig: plt.Figure, max_screen_fraction: float = 0.85) -> None:
    manager = plt.get_current_fig_manager()

    try:
        window = manager.window
    except Exception:
        return

    screen_width = None
    screen_height = None

    for getter_x, getter_y in (
        ("winfo_screenwidth", "winfo_screenheight"),
        ("width", "height"),
    ):
        if hasattr(window, getter_x) and hasattr(window, getter_y):
            try:
                screen_width = int(getattr(window, getter_x)())
                screen_height = int(getattr(window, getter_y)())
            except Exception:
                screen_width = None
                screen_height = None
            if screen_width and screen_height:
                break

    if not screen_width or not screen_height:
        return

    target_px = min(screen_width, screen_height) * max_screen_fraction
    target_inches = target_px / fig.dpi
    fig.set_size_inches(target_inches, target_inches, forward=True)


def draw_chartwheel(output_path: Path) -> Path:
    max_diameter = max(PLANET_DIAMETERS.values())
    max_radius = max_diameter / 2

    fig, ax = plt.subplots(figsize=(max_diameter / 100, max_diameter / 100), dpi=100)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    for index, sign in enumerate(ZODIAC_SIGNS):
        theta1 = ARIES_THETA_START + (index * SLICE_SPAN_DEGREES)
        theta2 = theta1 + SLICE_SPAN_DEGREES
        slice_overlay = Wedge(
            center=(0, 0),
            r=max_radius,
            theta1=theta1,
            theta2=theta2,
            facecolor=SIGN_COLORS[sign],
            alpha=0.10,
            edgecolor="#202020",
            linewidth=0.8,
            zorder=ZODIAC_OVERLAY_ZORDER,
        )
        ax.add_patch(slice_overlay)

    for z_index, (planet, diameter) in enumerate(
        sorted(PLANET_DIAMETERS.items(), key=lambda entry: entry[1], reverse=True),
        start=1,
    ):
        circle = Circle(
            (0, 0),
            radius=diameter / 2,
            facecolor=PLANET_COLORS[planet],
            edgecolor="#111111",
            linewidth=1,
            zorder=z_index,
        )
        ax.add_patch(circle)

    ax.set_xlim(-max_radius, max_radius)
    ax.set_ylim(-max_radius, max_radius)
    ax.set_aspect("equal")
    ax.axis("off")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        output_path,
        dpi=100,
        bbox_inches="tight",
        pad_inches=0,
        transparent=True,
    )
    return output_path


def main() -> None:
    output_path = Path("chartwheel.png")
    saved_path = draw_chartwheel(output_path)
    print(f"Chart wheel saved to: {saved_path.resolve()}")
    _fit_window_to_screen(plt.gcf())
    plt.show()
    plt.close("all")
