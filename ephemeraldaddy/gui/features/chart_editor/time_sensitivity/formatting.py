"""Rich-text formatting for Fine Tune Hourly Scan results."""

from __future__ import annotations

import re
from html import escape

from ephemeraldaddy.analysis.human_design_reference import GATE_COLORS
from ephemeraldaddy.core.interpretations import (
    ASPECT_COLORS,
    HOUSE_COLORS,
    NAKSHATRA_PLANET_COLOR,
    PLANET_COLORS,
    SIGN_COLORS,
)

from .hourly_scan import FineTuneHourlyScanResult, FineTuneTransition, TransitionSection


def _span(text: str, color: str) -> str:
    return f"<span style='color:{escape(color, quote=True)};'>{escape(text)}</span>"


def _subject_html(item: FineTuneTransition) -> str:
    if item.section is TransitionSection.ASPECT_CHANGES:
        words = item.subject.split()
        aspect_name = " ".join(words[1:-1]).replace(" ", "_") if len(words) > 2 else ""
        color = ASPECT_COLORS.get(aspect_name, "#d7d7d7")
        return _span(item.subject, color)
    if item.section is TransitionSection.HOUSE_CHANGES:
        match = re.search(r"H(\d+)", item.subject)
        color = HOUSE_COLORS.get(match.group(1), "#d7d7d7") if match else "#d7d7d7"
        return _span(item.subject, color)
    body = item.subject.removesuffix(" house").split()[-1]
    return _span(item.subject, PLANET_COLORS.get(body, "#d7d7d7"))


def _value_html(item: FineTuneTransition, value: str) -> str:
    if value in SIGN_COLORS:
        return _span(value, SIGN_COLORS[value])
    if item.section is TransitionSection.NAKSHATRA_CHANGES:
        color = NAKSHATRA_PLANET_COLOR.get(value, ("", "#d7d7d7"))[1]
        return _span(value, color)
    if item.section is TransitionSection.HD_GATE_LINE_CHANGES:
        match = re.search(r"Gate (\d+)", value)
        color = GATE_COLORS.get(int(match.group(1)), "#d7d7d7") if match else "#d7d7d7"
        return _span(value, color)
    if item.section is TransitionSection.ASPECT_CHANGES and "relevance" in value:
        return _span(value, "#f0a35b" if "out" in value else "#70c98b")
    return escape(value)


def format_fine_tune_hourly_scan_html(result: FineTuneHourlyScanResult) -> str:
    """Return sectioned, color-coded micro-ephemeris HTML."""
    end_hour = (result.start_hour + 1) % 24
    lines = [
        "<div style='white-space:normal;'>",
        (
            f"<div><b>Fine Tune Hourly Scan</b> &mdash; "
            f"{result.start_hour:02d}:00&ndash;{end_hour:02d}:00, "
            f"{result.resolution_minutes}-minute steps</div>"
        ),
    ]
    if not result.uses_houses:
        lines.append(
            "<div style='color:#aaa;'><i>House and angle changes are unavailable "
            "because this chart does not use houses.</i></div>"
        )
    if result.warnings:
        visible_warnings = result.warnings[:10]
        lines.append("<h4 style='margin:8px 0 3px 0;'>Warnings</h4>")
        lines.extend(
            f"<div style='color:#d9a066;'>{escape(warning)}</div>"
            for warning in visible_warnings
        )
        if len(result.warnings) > len(visible_warnings):
            lines.append(
                "<div style='color:#d9a066;'>"
                f"{len(result.warnings) - len(visible_warnings)} additional warnings omitted."
                "</div>"
            )
    by_section = {
        section: [item for item in result.transitions if item.section is section]
        for section in TransitionSection
    }
    for section in TransitionSection:
        lines.append(f"<h4 style='margin:8px 0 3px 0;'>{escape(section.value)}</h4>")
        items = by_section[section]
        if not items:
            lines.append("<div style='color:#888;'>No changes detected.</div>")
            continue
        for item in items:
            lines.append(
                "<div>"
                f"<b>{escape(item.time_label)}</b> &nbsp;|&nbsp; {_subject_html(item)}: "
                f"{_value_html(item, item.previous_value)} &rarr; "
                f"{_value_html(item, item.current_value)}"
                "</div>"
            )
    lines.append("</div>")
    return "\n".join(lines)
