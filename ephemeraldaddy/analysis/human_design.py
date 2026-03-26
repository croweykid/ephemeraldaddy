"""Human Design summary helpers for Chart View popouts."""

from __future__ import annotations

from typing import Any

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.human_design_system import (
    HumanDesignResult,
    calculate_human_design,
)
from ephemeraldaddy.analysis.human_design_reference import AWARENESS_STREAMS
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


def _build_hd_positions_lines(hd_result: HumanDesignResult) -> list[str]:
    """Build a Human Design-native POSITIONS block (no zodiac sign import)."""
    lines = [
        "POSITIONS",
        CHART_DATA_DIVIDER,
        f"{'Body':<12}  {'Stream':<12}  {'Longitude':<11}  {'Activation':<20}",
        CHART_DATA_DIVIDER,
    ]
    for activation in (*hd_result.personality_activations, *hd_result.design_activations):
        stream = "Personality" if activation.side == "personality" else "Design"
        activation_text = f"G{activation.gate}.{activation.line} C{activation.color} T{activation.tone} B{activation.base}"
        lines.append(
            f"{activation.body:<12}  {stream:<12}  {activation.longitude:>8.3f}°  {activation_text:<20}"
        )
    return lines


def _render_clickable_gates(active_gates: set[int]) -> tuple[str, list[dict[str, object]]]:
    if not active_gates:
        return "None", []
    parts: list[str] = []
    info_entries: list[dict[str, object]] = []
    cursor = 0
    for idx, gate in enumerate(sorted(active_gates)):
        token = f"{gate} ⓘ"
        parts.append(token)
        info_entries.append({"kind": "hd_gate_line", "gate": gate, "line": None, "icon_index": cursor + len(str(gate)) + 1})
        cursor += len(token)
        if idx < len(active_gates) - 1:
            parts.append(", ")
            cursor += 2
    return "".join(parts), info_entries


def _render_clickable_lines(active_lines: set[tuple[int, int]]) -> tuple[str, list[dict[str, object]]]:
    if not active_lines:
        return "None", []
    sorted_lines = sorted(active_lines, key=lambda item: (item[0], item[1]))
    parts: list[str] = []
    info_entries: list[dict[str, object]] = []
    cursor = 0
    for idx, (gate, line) in enumerate(sorted_lines):
        label = f"{gate}.{line}"
        token = f"{label} ⓘ"
        parts.append(token)
        info_entries.append({"kind": "hd_gate_line", "gate": gate, "line": line, "icon_index": cursor + len(label) + 1})
        cursor += len(token)
        if idx < len(sorted_lines) - 1:
            parts.append(", ")
            cursor += 2
    return "".join(parts), info_entries


def build_human_design_chart_data_output(
    chart: Chart,
    *,
    aspect_sort: str,
) -> tuple[str, dict[int, Any], dict[int, Any], dict[int, Any], int]:
    """Build Human Design-centric chart data text for popout output.

    Includes the standard Positions section, then Gates/Lines/Awareness Streams.
    Excludes Houses and Aspects from the rendered output.
    """

    _ = aspect_sort
    positions_start_index = 0
    position_info_map: dict[int, Any] = {}

    hd_result = calculate_human_design(chart)
    position_lines = _build_hd_positions_lines(hd_result)
    activations = (*hd_result.personality_activations, *hd_result.design_activations)
    active_gate_set = {activation.gate for activation in activations}
    active_line_set = {(activation.gate, activation.line) for activation in activations}

    gates_text, gates_info_entries = _render_clickable_gates(active_gate_set)
    lines_text, lines_info_entries = _render_clickable_lines(active_line_set)

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
    gates_line_index = rendered_lines.index(gates_text)
    lines_line_index = rendered_lines.index(lines_text)
    for entry in gates_info_entries:
        position_info_map.setdefault(positions_start_index + gates_line_index, []).append(entry)
    for entry in lines_info_entries:
        position_info_map.setdefault(positions_start_index + lines_line_index, []).append(entry)

    return (
        "\n".join(rendered_lines),
        position_info_map,
        {},
        {},
        positions_start_index,
    )
