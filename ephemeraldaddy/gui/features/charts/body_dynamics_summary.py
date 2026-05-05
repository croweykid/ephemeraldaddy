"""Body Dynamics summary rendering helpers for Chart Analytics panels."""

from __future__ import annotations

import html

from ephemeraldaddy.core.interpretations import INNER_PLANETS, OUTER_PLANETS, PLANET_COLORS, PLANET_ORDER
from ephemeraldaddy.gui.features.charts.text_summary import _display_body_name


def build_body_dynamics_summary_html(
    scores: dict[str, dict[str, float]],
    *,
    fallback_text_color: str,
) -> str:
    tracked_bodies = [body for body in PLANET_ORDER if body in (INNER_PLANETS | OUTER_PLANETS)]
    sections = [
        ("Enabling influences:", "enabling", "#6be39d"),
        ("Antagonizing influences:", "antagonizing", "#ff6b6b"),
        ("Escalating influences:", "escalating", "#ffbd59"),
    ]

    def _render_list(metric_key: str) -> str:
        entries: list[tuple[str, float]] = []
        for body in tracked_bodies:
            body_scores = scores.get(body) or {}
            enabling = float(body_scores.get("enabling", 0.0))
            antagonizing = float(body_scores.get("antagonizing", 0.0))
            escalating = float(body_scores.get("escalating", 0.0))
            total = enabling + antagonizing + escalating
            if total <= 0.0:
                continue
            dominance = (float(body_scores.get(metric_key, 0.0)) / total) * 100.0
            if metric_key == "enabling" and enabling > antagonizing:
                entries.append((body, dominance))
            elif metric_key == "antagonizing" and antagonizing > enabling:
                entries.append((body, dominance))
            elif metric_key == "escalating" and escalating > enabling and escalating > antagonizing:
                entries.append((body, dominance))
        entries.sort(key=lambda item: item[1], reverse=True)
        if not entries:
            return "<span style='color:#8d8d8d;'>none</span>"
        rendered = []
        for body, pct in entries:
            body_color = PLANET_COLORS.get(body, fallback_text_color)
            rendered.append(
                f"<span style='color:{body_color};'>{html.escape(_display_body_name(body))}</span> ({pct:.1f}%)"
            )
        return ", ".join(rendered)

    section_lines = []
    for label, metric_key, header_color in sections:
        section_lines.append(
            f"<span style='font-weight:700;color:{header_color};'>{html.escape(label)}</span> {_render_list(metric_key)}"
        )
    return "<br>".join(section_lines)
