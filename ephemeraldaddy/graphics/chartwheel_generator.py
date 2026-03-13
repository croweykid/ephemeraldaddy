"""Generate a concentric planetary color wheel chart.

Run examples:
- From repository root (preferred):
  `python -m ephemeraldaddy.graphics.chartwheel_generator`
- From this directory:
  `python -m chartwheel_generator`

Note: when using `-m`, do not include the `.py` suffix.
"""

Run examples:
- From repository root (preferred):
  `python -m ephemeraldaddy.graphics.chartwheel_generator`
- From this directory:
  `python -m chartwheel_generator`

Note: when using `-m`, do not include the `.py` suffix.
"""

import argparse
from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import Circle

if __package__ in {None, ""}:
    # Support running this file directly while preserving package imports.
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from ephemeraldaddy.core.interpretations import PLANET_COLORS
else:
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
    """Draw and save a chart wheel of concentric planetary circles."""
    max_diameter = max(PLANET_DIAMETERS.values())
    max_radius = max_diameter / 2

    fig, ax = plt.subplots(figsize=(max_diameter / 100, max_diameter / 100), dpi=100)

    # Draw from outermost to innermost so the innermost is on top.
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        default="chartwheel.png",
        help="Path to output image (default: chartwheel.png)",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    saved_path = draw_chartwheel(output_path)
    print(f"Chart wheel saved to: {saved_path.resolve()}")


if __name__ == "__main__":
    main()
