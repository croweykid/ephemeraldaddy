from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from ..core.interpretations import PLANET_COLORS

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


def draw_chartwheel(output_path: Path) -> Path:
    max_diameter = max(PLANET_DIAMETERS.values())
    max_radius = max_diameter / 2

    fig, ax = plt.subplots(figsize=(max_diameter / 100, max_diameter / 100), dpi=100)

    for z_index, (planet, diameter) in enumerate(
        sorted(PLANET_DIAMETERS.items(), key=lambda entry: entry[1], reverse=True),
        start=1,
    ):
        circle = Circle(
            (0, 0),
            radius=diameter / 2,
            facecolor=PLANET_COLORS[planet],
            edgecolor="#000000",
            linewidth=1,
            zorder=z_index,
        )
        ax.add_patch(circle)

    ax.set_xlim(-max_radius, max_radius)
    ax.set_ylim(-max_radius, max_radius)
    ax.set_aspect("equal")
    ax.axis("off")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=100, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return output_path


def main() -> None:
    output_path = Path("chartwheel.png")
    saved_path = draw_chartwheel(output_path)
    print(f"Chart wheel saved to: {saved_path.resolve()}")
