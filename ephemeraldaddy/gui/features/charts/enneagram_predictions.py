"""Enneagram prediction chart rendering and popout info helpers."""

from __future__ import annotations

import html
import random
from typing import Any, Callable


def calculate_enneagram_type_weights(
    chart: Any,
    *,
    enneagram: dict[int, dict[str, Any]],
    calculate_sign_weights: Callable[[Any], dict[str, float]],
    calculate_body_weights: Callable[[Any], dict[str, float]],
    calculate_house_weights: Callable[[Any], dict[int, float]],
    chart_uses_houses: Callable[[Any], bool],
) -> dict[int, float]:
    """Compute Enneagram type scores from chart-level dominant weights."""
    scores = {enneagram_type: 0.0 for enneagram_type in range(1, 10)}
    sign_weights = getattr(chart, "dominant_sign_weights", None) or calculate_sign_weights(chart)
    body_weights = getattr(chart, "dominant_planet_weights", None) or calculate_body_weights(chart)
    use_houses = chart_uses_houses(chart)
    house_weights = calculate_house_weights(chart) if use_houses else {}

    for enneagram_type, factors in enneagram.items():
        signs = {str(sign).strip() for sign in factors.get("signs", set()) if str(sign).strip()}
        bodies = {str(body).strip() for body in factors.get("bodies", set()) if str(body).strip()}
        houses = {
            int(house_num)
            for house_num in factors.get("houses", set())
            if isinstance(house_num, int) and 1 <= int(house_num) <= 12
        }

        scores[enneagram_type] += sum(float(sign_weights.get(sign, 0.0)) for sign in signs)
        scores[enneagram_type] += sum(float(body_weights.get(body, 0.0)) for body in bodies)
        if use_houses:
            scores[enneagram_type] += sum(float(house_weights.get(house_num, 0.0)) for house_num in houses)

    return scores


def draw_enneagram_predictions(
    ax: Any,
    *,
    chart: Any,
    enneagram: dict[int, dict[str, Any]],
    calculate_type_weights: Callable[[Any], dict[int, float]],
    chart_theme_colors: dict[str, str],
    apply_standard_bar_axes: Callable[[Any, list[str]], None],
    standard_chart_layout: dict[str, float],
) -> None:
    """Draw the Enneagram prediction bar chart on the provided Matplotlib axis."""
    type_labels = [str(num) for num in range(1, 10)]
    type_scores = calculate_type_weights(chart)
    values = [float(type_scores.get(num, 0.0)) for num in range(1, 10)]
    max_value = max(values) if values else 0.0

    enneagram_colors = [
        str(enneagram.get(num, {}).get("color", chart_theme_colors["highlight"]))
        for num in range(1, 10)
    ]
    bars = ax.bar(type_labels, values, color=enneagram_colors)
    apply_standard_bar_axes(ax, type_labels)
    ax.set_ylim(0, max(1.0, max_value + 1.0))
    ax.set_anchor("W")
    label_offset = max(0.15, (max_value * 0.02) if max_value else 0.15)
    for bar, type_label in zip(bars, type_labels, strict=True):
        bar.set_gid(f"enneagram:{type_label}")
        bar.set_picker(True)
        score = bar.get_height()
        ax.text(
            bar.get_x() + (bar.get_width() / 2.0),
            max(score, 0.0) + label_offset,
            f"{score:.0f}",
            ha="center",
            va="bottom",
            color=chart_theme_colors["text"],
            fontsize=7.5,
        )
    for spine in ax.spines.values():
        spine.set_color(chart_theme_colors["spine"])
    ax.figure.tight_layout()
    ax.figure.subplots_adjust(
        left=standard_chart_layout["left"],
        bottom=standard_chart_layout["bottom"],
        top=standard_chart_layout["top"],
        right=standard_chart_layout["right"],
    )


def build_enneagram_popout_info_html(
    enneagram_type: int,
    *,
    enneagram: dict[int, dict[str, Any]],
    chart_theme_colors: dict[str, str],
    highlight_color: str,
) -> str:
    """Build HTML for the Enneagram popout info panel selection."""
    type_data = enneagram.get(int(enneagram_type), {})
    type_color = str(type_data.get("color") or chart_theme_colors["text"]).strip() or chart_theme_colors["text"]
    motivation = str(type_data.get("motivation", "No motivation data available.")).strip()
    description = str(type_data.get("description", "No description data available.")).strip()
    quotes = type_data.get("quotes", [])
    quote_list = [str(quote).strip() for quote in quotes if str(quote).strip()]
    selected_quote = random.choice(quote_list) if quote_list else "No quote available."

    return (
        f"<div style='font-size:18px;font-weight:700;color:{html.escape(type_color)};'>"
        f"Enneagram Type {enneagram_type}"
        "</div>"
        f"<div style='margin-top:8px;'><span style='font-weight:700;color:{highlight_color};'>"
        "Motivation:"
        f"</span> {html.escape(motivation)}</div>"
        f"<div style='margin-top:8px;font-size:12px;color:{chart_theme_colors['text']};font-style:italic;'>"
        f"{html.escape(selected_quote)}"
        "</div>"
        f"<div style='margin-top:8px;color:{chart_theme_colors['text']};'>"
        f"{html.escape(description)}"
        "</div>"
    )


def tritype_text_for_scores(type_scores: dict[int, float]) -> str:
    """Return the top-ranked tritype string from Enneagram scores."""
    ranked_types = sorted(
        range(1, 10),
        key=lambda type_num: (float(type_scores.get(type_num, 0.0)), -type_num),
        reverse=True,
    )[:3]
    return "-".join(str(type_num) for type_num in ranked_types)


def connect_enneagram_popout_pick_handler(
    popout_canvas: Any,
    info_panel: Any,
    *,
    build_info_html: Callable[[int], str],
) -> None:
    """Attach standard Enneagram bar click behavior to the popout chart canvas."""

    def _on_pick(event) -> None:
        artist = getattr(event, "artist", None)
        artist_gid = artist.get_gid() if artist is not None else None
        if not isinstance(artist_gid, str) or ":" not in artist_gid:
            return
        chart_key, raw_value = artist_gid.split(":", 1)
        if chart_key != "enneagram":
            return
        try:
            enneagram_type = int(raw_value)
        except ValueError:
            return
        info_panel.setHtml(build_info_html(enneagram_type))

    popout_canvas.mpl_connect("pick_event", _on_pick)
