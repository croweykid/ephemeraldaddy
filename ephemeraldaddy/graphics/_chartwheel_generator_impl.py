from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Wedge

from ..core import interpretations
from ..core.interpretations import SIGN_COLORS

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


DEFAULT_WINDOW_SIZE_PX = 600
DEFAULT_OUTPUT_SIZE_PX = 600

SIGN_WHEEL_CANVAS_SIZE_PX = 2033
SIGN_WHEEL_DISC_DIAMETER_PX = 1632

SIGN_WHEELS = getattr(interpretations, "SIGN_WHEELS", {})
SIGN_WHEEL_IMAGE_CACHE: dict[str, object | None] = {}


def _resolve_sign_wheel_path(sign: str) -> Path | None:
    raw_path = SIGN_WHEELS.get(sign)
    if not raw_path:
        return None

    candidate = Path(raw_path)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    repo_root = Path(__file__).resolve().parents[2]
    repo_relative = repo_root / candidate
    if repo_relative.exists():
        return repo_relative

    package_root = Path(__file__).resolve().parents[1]
    package_relative = package_root / candidate
    if package_relative.exists():
        return package_relative

    return None


def _sign_wheel_image(sign: str):
    if sign in SIGN_WHEEL_IMAGE_CACHE:
        return SIGN_WHEEL_IMAGE_CACHE[sign]

    wheel_path = _resolve_sign_wheel_path(sign)
    if wheel_path is None:
        SIGN_WHEEL_IMAGE_CACHE[sign] = None
        return None

    try:
        SIGN_WHEEL_IMAGE_CACHE[sign] = mpimg.imread(wheel_path)
    except Exception:
        SIGN_WHEEL_IMAGE_CACHE[sign] = None

    return SIGN_WHEEL_IMAGE_CACHE[sign]




def _image_extent_radius_for_disc(max_radius: float) -> float:
    if SIGN_WHEEL_DISC_DIAMETER_PX <= 0:
        return max_radius
    return max_radius * (SIGN_WHEEL_CANVAS_SIZE_PX / SIGN_WHEEL_DISC_DIAMETER_PX)

def _ring_inner_radius(sorted_diameters: list[tuple[str, int]], index: int) -> float:
    if index + 1 >= len(sorted_diameters):
        return 0.0
    return sorted_diameters[index + 1][1] / 2

SAMPLE_CHART_POSITIONS = {
    "Sun": {"sign": "Pisces", "lon": 335.30, "house": 4},
    "Moon": {"sign": "Capricorn", "lon": 287.47, "house": 1},
    "Mercury": {"sign": "Aquarius", "lon": 318.45, "house": 3},
    "Venus": {"sign": "Aquarius", "lon": 305.62, "house": 3},
    "Mars": {"sign": "Aries", "lon": 6.00, "house": 2},
    "Jupiter": {"sign": "Virgo", "lon": 150.80, "house": 8},
    "Saturn": {"sign": "Aries", "lon": 10.89, "house": 2},
    "Uranus": {"sign": "Virgo", "lon": 178.56, "house": 9},
    "Neptune": {"sign": "Scorpio", "lon": 236.97, "house": 10},
    "Pluto": {"sign": "Virgo", "lon": 172.43, "house": 9},
}


def _sign_for_planet(planet: str) -> str:
    placement = SAMPLE_CHART_POSITIONS.get(planet, {})
    sign = placement.get("sign")
    if sign in SIGN_COLORS:
        return sign

    lon = placement.get("lon")
    if lon is None:
        return "Aries"

    sign_index = int(float(lon) % 360 // 30)
    return ZODIAC_SIGNS[sign_index]


def _fit_window_to_screen(fig: plt.Figure, max_screen_fraction: float = 0.95) -> None:
    manager = getattr(fig.canvas, "manager", None)
    if manager is None:
        return

    try:
        window = manager.window
    except Exception:
        return

    screen_width = None
    screen_height = None

    if hasattr(window, "winfo_screenwidth") and hasattr(window, "winfo_screenheight"):
        try:
            screen_width = int(window.winfo_screenwidth())
            screen_height = int(window.winfo_screenheight())
        except Exception:
            screen_width = None
            screen_height = None

    if (not screen_width or not screen_height) and hasattr(window, "screen"):
        try:
            geometry = window.screen().availableGeometry()
            screen_width = int(geometry.width())
            screen_height = int(geometry.height())
        except Exception:
            screen_width = None
            screen_height = None

    if not screen_width or not screen_height:
        return

    max_window_height_px = max(1, int(screen_height * max_screen_fraction))
    max_window_width_px = max(1, int(screen_width * max_screen_fraction))
    window_size_px = min(DEFAULT_WINDOW_SIZE_PX, max_window_height_px, max_window_width_px)

    if hasattr(manager, "resize"):
        try:
            manager.resize(window_size_px, window_size_px)
            if hasattr(fig.canvas, "draw_idle"):
                fig.canvas.draw_idle()
            return
        except Exception:
            pass

    # Fallback for backends without working manager.resize().
    # Reserve space for title bar / toolbar so overall window height stays within screen bounds.
    non_canvas_vertical_px = 140
    non_canvas_horizontal_px = 40
    target_canvas_px = min(
        max_window_height_px - non_canvas_vertical_px,
        max_window_width_px - non_canvas_horizontal_px,
    )
    target_canvas_px = max(1, target_canvas_px)
    target_inches = target_canvas_px / fig.dpi
    fig.set_size_inches(target_inches, target_inches, forward=True)


def draw_chartwheel(output_path: Path) -> Path:
    max_diameter = max(PLANET_DIAMETERS.values())
    max_radius = max_diameter / 2

    output_size_inches = DEFAULT_OUTPUT_SIZE_PX / 100
    fig, ax = plt.subplots(figsize=(output_size_inches, output_size_inches), dpi=100)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    sorted_diameters = sorted(PLANET_DIAMETERS.items(), key=lambda entry: entry[1], reverse=True)
    image_extent_radius = _image_extent_radius_for_disc(max_radius)

    for z_index, (planet, diameter) in enumerate(sorted_diameters, start=1):
        outer_radius = diameter / 2
        inner_radius = _ring_inner_radius(sorted_diameters, z_index - 1)
        sign = _sign_for_planet(planet)
        wheel_image = _sign_wheel_image(sign)

        if wheel_image is not None:
            ring_image = ax.imshow(
                wheel_image,
                extent=(
                    -image_extent_radius,
                    image_extent_radius,
                    -image_extent_radius,
                    image_extent_radius,
                ),
                zorder=z_index,
            )
            ring_clip = Wedge(
                center=(0, 0),
                r=outer_radius,
                theta1=0,
                theta2=360,
                width=max(outer_radius - inner_radius, 0),
                transform=ax.transData,
            )
            ring_image.set_clip_path(ring_clip)
        else:
            circle = Circle(
                (0, 0),
                radius=outer_radius,
                facecolor=SIGN_COLORS[sign],
                edgecolor="#111111",
                linewidth=1,
                zorder=z_index,
            )
            ax.add_patch(circle)

        ring_outline = Circle(
            (0, 0),
            radius=outer_radius,
            fill=False,
            edgecolor="#111111",
            linewidth=1,
            zorder=z_index + 0.2,
        )
        ax.add_patch(ring_outline)

    ax.set_xlim(-max_radius, max_radius)
    ax.set_ylim(-max_radius, max_radius)
    ax.set_aspect("equal")
    ax.axis("off")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        output_path,
        dpi=100,
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
