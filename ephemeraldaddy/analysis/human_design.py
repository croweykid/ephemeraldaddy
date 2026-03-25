"""Human Design summary helpers for Chart View popouts."""

from __future__ import annotations

import re
from typing import Any

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.human_design_system import (
    HumanDesignResult,
    calculate_human_design,
)
from ephemeraldaddy.core.interpretations import AWARENESS_STREAMS
from ephemeraldaddy.gui.features.charts.text_summary import format_chart_text
from ephemeraldaddy.gui.style import CHART_DATA_DIVIDER


def get_active_human_design_gates_and_lines(chart: Chart) -> tuple[set[int], set[tuple[int, int]]]:
    """Return active Human Design gates and (gate, line) tuples for a chart."""
    hd_result = calculate_human_design(chart)
    activations = (*hd_result.personality_activations, *hd_result.design_activations)
    active_gate_set = {activation.gate for activation in activations}
    active_line_set = {(activation.gate, activation.line) for activation in activations}
    return active_gate_set, active_line_set


def build_human_design_result(chart: Chart) -> HumanDesignResult:
    """Expose full HD computation for UI renderers."""
    return calculate_human_design(chart)


def build_awareness_stream_completion(active_gate_set: set[int]) -> list[dict[str, Any]]:
    """Build per-stream completion payload used by Human Design text + visuals."""
    awareness_payload: list[dict[str, Any]] = []
    for stream in AWARENESS_STREAMS:
        stream_name = str(stream.get("name", "")).strip().title() or "Unknown"
        stream_type = str(stream.get("type", "")).strip().title() or "Unknown"
        required_gates = [int(gate) for gate in stream.get("gates", []) if isinstance(gate, int)]
        if not required_gates:
            awareness_payload.append(
                {
                    "type": stream_type,
                    "name": stream_name,
                    "gates": [],
                    "present_gates": [],
                    "completion_pct": 0,
                    "missing_text": "Missing all gates",
                }
            )
            continue
        present_gates = [gate for gate in required_gates if gate in active_gate_set]
        completion_pct = int(round((len(present_gates) / len(required_gates)) * 100))
        missing = [str(gate) for gate in required_gates if gate not in active_gate_set]
        missing_text = f"Missing {', '.join(missing)}" if missing else "Complete"
        awareness_payload.append(
            {
                "type": stream_type,
                "name": stream_name,
                "gates": required_gates,
                "present_gates": present_gates,
                "completion_pct": completion_pct,
                "missing_text": missing_text,
            }
        )
    return awareness_payload


def _strip_nakshatra_column(position_lines: list[str]) -> list[str]:
    """Remove the Nakshatra column from POSITIONS block while preserving alignment."""
    result_lines: list[str] = []
    for line in position_lines:
        stripped = line.strip()
        if not stripped:
            result_lines.append(line)
            continue
        if stripped.startswith("Body") and "Nakshatra" in stripped:
            updated = re.sub(r"\s{2,}Nakshatra\s{2,}", "  ", line, count=1)
            result_lines.append(updated)
            continue
        if stripped.startswith(CHART_DATA_DIVIDER):
            result_lines.append(line)
            continue
        columns = re.split(r"\s{2,}", stripped)
        if len(columns) >= 5:
            if columns[-1].startswith("H") and len(columns) >= 6:
                body, sign, degree, _nakshatra, gl, house = columns[:6]
                result_lines.append(f"{body:<10}  {sign:<11}  {degree:<12}  {gl:<30}  {house:<5}")
            else:
                body, sign, degree, _nakshatra, gl = columns[:5]
                result_lines.append(f"{body:<10}  {sign:<11}  {degree:<12}  {gl:<30}")
            continue
        result_lines.append(line)
    return result_lines


def build_human_design_chart_data_output(
    chart: Chart,
    *,
    aspect_sort: str,
) -> tuple[str, dict[int, Any], dict[int, Any], dict[int, Any], int]:
    """Build Human Design-centric chart data text for popout output.

    Includes the standard Positions section, then Gates/Lines/Awareness Streams.
    Excludes Houses and Aspects from the rendered output.
    """

    chart_summary_text, position_info_map, aspect_info_map, species_info_map = format_chart_text(
        chart,
        aspect_sort=aspect_sort,
    )
    summary_lines = chart_summary_text.splitlines()
    positions_start_index = next(
        (idx for idx, line in enumerate(summary_lines) if line.strip() == "POSITIONS"),
        0,
    )
    houses_header_index = next(
        (
            idx
            for idx, line in enumerate(summary_lines[positions_start_index + 1 :], start=positions_start_index + 1)
            if line.strip() == "HOUSES"
        ),
        len(summary_lines),
    )
    position_lines = summary_lines[positions_start_index:houses_header_index]

    position_lines = _strip_nakshatra_column(position_lines)
    active_gate_set, active_line_set = get_active_human_design_gates_and_lines(chart)

    gates_text = ", ".join(str(gate) for gate in sorted(active_gate_set)) or "None"
    lines_text = (
        ", ".join(f"{gate}.{line}" for gate, line in sorted(active_line_set, key=lambda item: (item[0], item[1])))
        or "None"
    )

    awareness_lines: list[str] = []
    for stream_entry in build_awareness_stream_completion(active_gate_set):
        awareness_lines.append(
            f"{stream_entry['type']}: {stream_entry['name']} - {stream_entry['completion_pct']}%. {stream_entry['missing_text']}"
        )

    rendered_lines = [
        *position_lines,
        "",
        CHART_DATA_DIVIDER,
        "GATES",
        CHART_DATA_DIVIDER,
        gates_text,
        "",
        CHART_DATA_DIVIDER,
        "LINES",
        CHART_DATA_DIVIDER,
        lines_text,
        "",
        CHART_DATA_DIVIDER,
        "AWARENESS STREAMS",
        CHART_DATA_DIVIDER,
        *awareness_lines,
    ]
    return (
        "\n".join(rendered_lines),
        position_info_map,
        aspect_info_map,
        species_info_map,
        positions_start_index,
    )
