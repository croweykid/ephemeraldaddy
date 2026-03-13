# ephemeraldaddy/graphics/wheel_plot.py
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from ephemeraldaddy.gui.style import DARK_THEME


from ephemeraldaddy.core.interpretations import (
    ASPECT_COLORS,
    aspect_score,
    ELEMENT_COLORS,
    NAKSHATRA_PLANET_COLOR,
    PLANET_COLORS,
    #PLANET_COLORS_EARTH, #this isn't used anywhere, as far as I can tell
    PLANET_GLYPHS,
    SIGN_COLORS,
    ZODIAC_NAMES,
    ZODIAC_SIGNS,
)



TRANSIT_INNER_WHEEL_SLICES = ("#80b3ff", "#4d94ff") #blue inner wheel (personal chart or person 1)
TRANSIT_INNER_GLYPH_COLOR = "#0000ff" #blue inner glyphs (personal chart or person 1)
TRANSIT_OUTER_WHEEL_SLICES = ("#ff8080", "#ff4d4d") #red outer wheel (event transit or person 2)
TRANSIT_OUTER_GLYPH_COLOR = "#ff0000" #red outer glyphs (event transit or person 2)

def _angular_diff(a, b):
    diff = abs(a - b) % (2 * np.pi)
    return min(diff, 2 * np.pi - diff)


def _relative_luminance(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _lighten_color(hex_color, amount):
    rgb = np.array(mcolors.to_rgb(hex_color))
    return mcolors.to_hex(rgb + (1.0 - rgb) * amount)


def _monochrome_sign_slice_color(base_color, sign_index):
    """Use the requested blue palette for alternating zodiac slices."""
    return TRANSIT_INNER_WHEEL_SLICES[sign_index % len(TRANSIT_INNER_WHEEL_SLICES)]


def _overlay_sign_slice_color(base_color, sign_index):
    """Use matching alternating red tones for the transit overlay ring."""
    return TRANSIT_OUTER_WHEEL_SLICES[sign_index % len(TRANSIT_OUTER_WHEEL_SLICES)]

def _glyph_color_for_sign(sign_name):
    base = SIGN_COLORS.get(sign_name, DARK_THEME["foreground"])
    luminance = _relative_luminance(mcolors.to_rgb(base))
    lighten_amount = 0.25 if luminance > 0.7 else 0.45
    return _lighten_color(base, lighten_amount)

def _format_degree_minutes(value):
    magnitude = abs(float(value))
    deg = int(magnitude)
    minutes = int(round((magnitude - deg) * 60))
    if minutes == 60:
        deg += 1
        minutes = 0
    return f"{deg:02d}°{minutes:02d}'"

def _chart_uses_houses(chart) -> bool:
    return not getattr(chart, "birthtime_unknown", False) or getattr(
        chart, "retcon_time_used", False
    )

def _draw_chart_wheel(
    fig,
    chart,
    *,
    canvas=None,
    overlay_positions=None,
    overlay_aspects=None,
    overlay_aspects_only=False,
    overlay_color="#6f8f6f",
    base_monochrome_color=None,
    overlay_sign_color=None,
    wheel_padding=0.0,
    show_title=True,
    symbol_scale=1.0,
    wheel_scale=1.0,
):
    ax_bg = fig.add_subplot(111, polar=True)
    ax = fig.add_axes(ax_bg.get_position(), polar=True, frameon=False)
    ax_cart = fig.add_axes(ax_bg.get_position(), frameon=False)

    if wheel_padding > 0:
        base_position = ax_bg.get_position()
        bounded_padding = min(max(float(wheel_padding), 0.0), 0.45)
        inset_x = base_position.width * bounded_padding
        inset_y = base_position.height * bounded_padding
        wheel_position = [
            base_position.x0 + inset_x,
            base_position.y0 + inset_y,
            max(0.01, base_position.width - (2.0 * inset_x)),
            max(0.01, base_position.height - (2.0 * inset_y)),
        ]
        ax_bg.set_position(wheel_position)
        ax.set_position(wheel_position)
        ax_cart.set_position(wheel_position)

    if wheel_scale != 1.0:
        bounded_scale = min(max(float(wheel_scale), 0.5), 1.8)
        current_position = ax_bg.get_position()
        center_x = current_position.x0 + (current_position.width / 2.0)
        center_y = current_position.y0 + (current_position.height / 2.0)
        scaled_width = min(1.0, current_position.width * bounded_scale)
        scaled_height = min(1.0, current_position.height * bounded_scale)
        scaled_position = [
            max(0.0, center_x - (scaled_width / 2.0)),
            max(0.0, center_y - (scaled_height / 2.0)),
            scaled_width,
            scaled_height,
        ]
        if scaled_position[0] + scaled_position[2] > 1.0:
            scaled_position[0] = 1.0 - scaled_position[2]
        if scaled_position[1] + scaled_position[3] > 1.0:
            scaled_position[1] = 1.0 - scaled_position[3]
        ax_bg.set_position(scaled_position)
        ax.set_position(scaled_position)
        ax_cart.set_position(scaled_position)

    fig.patch.set_facecolor(DARK_THEME["background"])
    ax_bg.set_facecolor(DARK_THEME["background"])
    ax.set_facecolor("none")
    ax_cart.patch.set_alpha(0)

    ax_bg.set_zorder(0)
    ax_cart.set_zorder(1)
    ax.set_zorder(2)

    for axis in (ax_bg, ax):
        axis.set_theta_zero_location("E")
        axis.set_theta_direction(-1)
        axis.grid(False)
        axis.set_xticks([])
        axis.set_yticks([])

    theta = np.linspace(0, 2 * np.pi, 360)
    ax.plot(theta, [1.0] * 360,
            linewidth=2.2,
            color=DARK_THEME["wheel_circle"])

    use_houses = _chart_uses_houses(chart)

    # Sign sectors + glyphs
    sign_inner_radius = 0.18
    sign_outer_radius = 1.0
    sign_height = sign_outer_radius - sign_inner_radius
    for i in range(12):
        start_angle = np.deg2rad(i * 30)
        mid_angle = start_angle + np.deg2rad(15)
        sign_name = ZODIAC_NAMES[i]
        if base_monochrome_color:
            sign_color = _monochrome_sign_slice_color(base_monochrome_color, i)
        else:
            sign_color = SIGN_COLORS.get(sign_name, DARK_THEME["background"])

        ax_bg.bar(
            start_angle,
            sign_height,
            width=np.deg2rad(30),
            bottom=sign_inner_radius,
            color=sign_color,
            align="edge",
            edgecolor="none",
            #zorder=0,
        )

        ax.plot(
            [start_angle, start_angle],
            [0.18, 1.0],
            linewidth=1.0,
            color=DARK_THEME["house_line"],
        )

        ax.text(
            mid_angle,
            1.06,
            ZODIAC_SIGNS[i],
            color=DARK_THEME["foreground"],
            ha="center",
            va="center",
            fontsize=16 * symbol_scale,
        )

        # Houses: draw from chart.houses if available; else fall back to equal
    if use_houses:
        cusps = getattr(chart, "houses", None)
        if isinstance(cusps, (list, tuple)) and len(cusps) >= 12:
            # Normalize to floats, 0–360
            cusps = [float(c) % 360.0 for c in cusps[:12]]

            # Draw each house cusp line
            for h_deg in cusps:
                theta_h = np.deg2rad(h_deg)
                ax.plot(
                    [theta_h, theta_h],
                    [0.18, 1.0],
                    linewidth=1.0,
                    color=DARK_THEME["house_line"],
                )

            # Label house numbers at the midpoint between consecutive cusps
            for i in range(12):
                start = cusps[i]
                end = cusps[(i + 1) % 12]
                if end <= start:
                    end += 360.0
                mid = (start + end) / 2.0
                theta_mid = np.deg2rad(mid % 360.0)

                ax.text(
                    theta_mid,
                    0.55,
                    str(i + 1),
                    color=DARK_THEME["foreground"],
                    ha="center",
                    va="center",
                    fontsize=10 * symbol_scale,
                )
        else:
            # Fallback: equal houses (old behaviour)
            for i in range(12):
                house_angle = np.deg2rad(i * 30)
                ax.plot(
                    [house_angle, house_angle],
                    [0.18, 1.0],
                    linewidth=1.0,
                    color=DARK_THEME["house_line"],
                )

            for i in range(12):
                house_mid = np.deg2rad(i * 30 + 15)
                ax.text(
                    house_mid,
                    0.55,
                    str(i + 1),
                    color=DARK_THEME["foreground"],
                    ha="center",
                    va="center",
                    fontsize=10 * symbol_scale,
                )


    # Planets with simple overlap handling
    inner_base_r_planet = 0.80
    inner_base_r_label = 0.88
    outer_base_r_planet = 1.12
    outer_base_r_label = 1.20
    plotted_angles = {"inner": [], "outer": []}
    hover_targets = []

    outer_bodies = {
        "Chiron",
        "Ceres",
        "Pallas",
        "Juno",
        "Vesta",
        "Rahu",
        "Ketu",
        "Lilith",
        "Part of Fortune",
    }

    angular_bodies = {"AS", "MC", "DS", "IC"}
    for body, lon_deg in sorted(chart.positions.items(), key=lambda kv: kv[1]):
        if not use_houses and body in angular_bodies:
            continue
        theta_p = np.radians(lon_deg)
        ring = "outer" if body in outer_bodies else "inner"

        close_count = sum(
            1 for ang in plotted_angles[ring]
            if _angular_diff(theta_p, ang) < np.deg2rad(6)
        )

        if ring == "outer":
            r_planet = outer_base_r_planet + 0.03 * close_count
            r_label = outer_base_r_label + 0.03 * close_count
        else:
            r_planet = inner_base_r_planet - 0.035 * close_count
            r_label = inner_base_r_label - 0.035 * close_count

        plotted_angles[ring].append(theta_p)

        #glyph = PLANET_GLYPHS.get(body, "•")

        sign_index = int(lon_deg // 30) % 12
        sign_name = ZODIAC_NAMES[sign_index]
        if base_monochrome_color:
            glyph_color = TRANSIT_INNER_GLYPH_COLOR
        else:
            glyph_color = _glyph_color_for_sign(sign_name)
        glyph = PLANET_GLYPHS.get(body, ZODIAC_SIGNS[sign_index])

        sign_text = ax.text(
            theta_p,
            r_planet,
            ZODIAC_SIGNS[sign_index],
            color=glyph_color,
            ha="center",
            va="center",
            fontsize=14 * symbol_scale,
        )
        planet_text = ax.text(
            theta_p,
            r_label,
            glyph,
            color=glyph_color,
            ha="center",
            va="center",
            fontsize=16 * symbol_scale,
        )
        hover_targets.append(
            {
                "texts": (sign_text, planet_text),
                "body": body,
                "lon_deg": lon_deg,
                "sign_name": sign_name,
                "anchor_text": sign_text,
            }
        )

    if overlay_positions:
        overlay_sign_tone = TRANSIT_OUTER_GLYPH_COLOR

        overlay_ring_inner_radius = 1.0
        overlay_ring_outer_radius = 1.085
        overlay_ring_height = overlay_ring_outer_radius - overlay_ring_inner_radius
        for i in range(12):
            start_angle = np.deg2rad(i * 30)
            overlay_slice_color = _overlay_sign_slice_color(overlay_color, i)
            ax_bg.bar(
                start_angle,
                overlay_ring_height,
                width=np.deg2rad(30),
                bottom=overlay_ring_inner_radius,
                color=overlay_slice_color,
                align="edge",
                edgecolor="none",
            )
            ax.plot(
                [start_angle, start_angle],
                [overlay_ring_inner_radius, overlay_ring_outer_radius],
                linewidth=0.8,
                color=DARK_THEME["house_line"],
            )

        overlay_angles: list[float] = []
        overlay_base_r_planet = 1.14
        overlay_base_r_label = 1.24
        for body, lon_deg in sorted(overlay_positions.items(), key=lambda kv: kv[1]):
            theta_p = np.radians(lon_deg)
            close_count = sum(
                1 for ang in overlay_angles if _angular_diff(theta_p, ang) < np.deg2rad(6)
            )
            r_planet = overlay_base_r_planet + 0.035 * close_count
            r_label = overlay_base_r_label + 0.035 * close_count
            overlay_angles.append(theta_p)

            sign_index = int(lon_deg // 30) % 12
            sign_name = ZODIAC_NAMES[sign_index]
            glyph = PLANET_GLYPHS.get(body, ZODIAC_SIGNS[sign_index])

            sign_text = ax.text(
                theta_p,
                r_planet,
                ZODIAC_SIGNS[sign_index],
                color=overlay_sign_tone,
                ha="center",
                va="center",
                fontsize=13 * symbol_scale,
            )
            planet_text = ax.text(
                theta_p,
                r_label,
                glyph,
                color=TRANSIT_OUTER_GLYPH_COLOR,
                ha="center",
                va="center",
                fontsize=15 * symbol_scale,
            )
            hover_targets.append(
                {
                    "texts": (sign_text, planet_text),
                    "body": body,
                    "lon_deg": lon_deg,
                    "sign_name": sign_name,
                    "anchor_text": sign_text,
                }
            )

    # === NEW: aspect lines (drawn as chords on a cartesian overlay) ===
    # Use a second axes in cartesian coordinates, between the background and labels.
    ax_cart.set_xlim(-1.05, 1.05)
    ax_cart.set_ylim(-1.05, 1.05)
    ax_cart.set_aspect("equal", adjustable="box")
    ax_cart.axis("off")

    r_aspect = 0.65  # radius at which aspect lines attach to the wheel
    aspect_clip_circle = Circle((0.0, 0.0), r_aspect, transform=ax_cart.transData)
    min_opacity = 0.20
    max_opacity = 1.0
    gamma = 0.8

    aspect_entries: list[tuple[dict, float]] = []
    angular_bodies = {"AS", "MC", "DS", "IC"}
    if not overlay_aspects_only:
        for asp in getattr(chart, "aspects", []):
            p1 = asp["p1"]
            p2 = asp["p2"]

            if p1 not in chart.positions or p2 not in chart.positions:
                continue
            if not use_houses and (p1 in angular_bodies or p2 in angular_bodies):
                continue
            aspect_entries.append((asp, aspect_score(asp)))

    for overlay_asp in overlay_aspects or []:
        lon1 = overlay_asp.get("lon1_deg")
        lon2 = overlay_asp.get("lon2_deg")
        aspect_type = overlay_asp.get("type")
        if lon1 is None or lon2 is None or not aspect_type:
            continue
        aspect_entries.append(
            (
                {
                    "type": str(aspect_type),
                    "lon1_deg": float(lon1) % 360.0,
                    "lon2_deg": float(lon2) % 360.0,
                },
                float(overlay_asp.get("score", 1.0)),
            )
        )

    for overlay_asp in overlay_aspects or []:
        lon1 = overlay_asp.get("lon1_deg")
        lon2 = overlay_asp.get("lon2_deg")
        aspect_type = overlay_asp.get("type")
        if lon1 is None or lon2 is None or not aspect_type:
            continue
        aspect_entries.append(
            (
                {
                    "type": str(aspect_type),
                    "lon1_deg": float(lon1) % 360.0,
                    "lon2_deg": float(lon2) % 360.0,
                },
                float(overlay_asp.get("score", 1.0)),
            )
        )

    scores = [score for _asp, score in aspect_entries]
    min_score = min(scores) if scores else 0.0
    max_score = max(scores) if scores else 0.0
    score_span = max_score - min_score

    for asp, score in aspect_entries:
        asp_type = asp["type"]
        if "lon1_deg" in asp and "lon2_deg" in asp:
            theta1 = np.radians(float(asp["lon1_deg"]))
            theta2 = np.radians(float(asp["lon2_deg"]))
        else:
            p1 = asp["p1"]
            p2 = asp["p2"]
            theta1 = np.radians(chart.positions[p1])
            theta2 = np.radians(chart.positions[p2])

        x1 = r_aspect * np.cos(theta1)
        y1 = r_aspect * np.sin(theta1)
        x2 = r_aspect * np.cos(theta2)
        y2 = r_aspect * np.sin(theta2)

        if score_span <= 0:
            norm = 1.0
        else:
            norm = (score - min_score) / score_span

        opacity = min_opacity + (max_opacity - min_opacity) * (norm ** gamma)
        color = ASPECT_COLORS.get(asp_type, DARK_THEME["foreground"])

        ax_cart.plot(
            [x1, x2],
            [y1, y2],
            linewidth=0.8,
            alpha=opacity,
            color=color,
            clip_on=True,
            clip_path=aspect_clip_circle,
        )

    if show_title:
        ax.set_title(
            chart.name,
            color=DARK_THEME["foreground"],
            fontsize=16 * symbol_scale,
            pad=24,
        )

    hover_note = ax.annotate(
        "",
        xy=(0, 0),
        xycoords="data",
        textcoords="offset points",
        xytext=(8, 8),
        ha="left",
        va="bottom",
        fontsize=10 * symbol_scale,
        color=DARK_THEME["foreground"],
        bbox=dict(
            boxstyle="round,pad=0.3",
            fc=DARK_THEME["background"],
            ec=DARK_THEME["foreground"],
            lw=0.8,
        ),
        annotation_clip=False,
    )
    hover_note.set_clip_on(False)
    hover_note.set_visible(False)

    def _on_move(event):
        if event.x is None or event.y is None:
            return
        if fig.canvas is None:
            return

        renderer = fig.canvas.get_renderer()

        for item in hover_targets:
            hit = False
            for text in item["texts"]:
                # During dialog/window teardown, hover events can fire while text artists
                # are detached from any figure; probing extents in that state raises.
                if getattr(text, "figure", None) is None:
                    continue

                try:
                    contains, _ = text.contains(event)
                except Exception:
                    continue
                if contains:
                    hit = True
                    break

                try:
                    bbox = text.get_window_extent(renderer=renderer).expanded(1.35, 1.35)
                    if bbox.contains(event.x, event.y):
                        hit = True
                        break
                except Exception:
                    continue

            if hit:
                degree_in_sign = item["lon_deg"] % 30.0
                hover_note.xy = item["anchor_text"].get_position()
                hover_note.set_text(
                    f"{item['body']}: {item['sign_name']} {_format_degree_minutes(degree_in_sign)}"
                )
                hover_note.set_visible(True)
                fig.canvas.draw_idle()
                return

        if hover_note.get_visible():
            hover_note.set_visible(False)
            fig.canvas.draw_idle()

    target_canvas = canvas or fig.canvas
    if target_canvas is not None:
        target_canvas.mpl_connect("motion_notify_event", _on_move)

    return fig


def draw_chart_wheel(
    fig,
    chart,
    *,
    canvas=None,
    overlay_positions=None,
    overlay_aspects=None,
    overlay_aspects_only=False,
    overlay_color="#6f8f6f",
    base_monochrome_color=None,
    overlay_sign_color=None,
    wheel_padding=0.0,
    show_title=True,
    symbol_scale=1.0,
    wheel_scale=1.0,
):
    return _draw_chart_wheel(
        fig,
        chart,
        canvas=canvas,
        overlay_positions=overlay_positions,
        overlay_aspects=overlay_aspects,
        overlay_aspects_only=overlay_aspects_only,
        overlay_color=overlay_color,
        base_monochrome_color=base_monochrome_color,
        overlay_sign_color=overlay_sign_color,
        wheel_padding=wheel_padding,
        show_title=show_title,
        symbol_scale=symbol_scale,
        wheel_scale=wheel_scale,
    )


def build_chart_wheel_figure(chart, *, figsize=(6, 6)):
    fig = Figure(figsize=figsize)
    return draw_chart_wheel(fig, chart)


def plot_chart_wheel(chart):
    fig = plt.figure(figsize=(8, 8))
    _draw_chart_wheel(fig, chart, show_title=True)
    plt.show()
    return fig
