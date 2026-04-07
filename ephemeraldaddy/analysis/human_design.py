"""Human Design summary helpers for Chart View popouts."""

from __future__ import annotations

from typing import Any

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.human_design_system import (
    HumanDesignResult,
    calculate_human_design,
)
from ephemeraldaddy.analysis.human_design_reference import AWARENESS_STREAMS, HD_CIRCUIT_GROUPS
from ephemeraldaddy.gui.style import CHART_DATA_DIVIDER

ZODIAC_NAMES = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)


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


def derive_human_design_profile(
    chart: Chart,
) -> tuple[list[int], list[int], list[str], str]:
    """Return canonical HD gates/lines/channels/type derived from chart positions.

    This helper is the shared, canonical profile derivation path for all UI
    surfaces that need Human Design filter/analytics values.
    """
    hd_result = calculate_human_design(chart)
    activations = (*hd_result.personality_activations, *hd_result.design_activations)
    gates = sorted(int(gate) for gate in hd_result.active_gates)
    lines = sorted({int(activation.line) for activation in activations})
    channels = sorted(
        f"{min(gate_a, gate_b)}-{max(gate_a, gate_b)}"
        for gate_a, gate_b, _center_a, _center_b in hd_result.defined_channels
    )
    hd_type = str(hd_result.hd_type or "").strip()
    return gates, lines, channels, hd_type


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


def build_circuit_group_completion(active_gate_set: set[int]) -> list[dict[str, Any]]:
    """Build per-circuit completion payload for Human Design visuals."""
    circuit_payload: list[dict[str, Any]] = []
    for group_name, group_meta in HD_CIRCUIT_GROUPS.items():
        required_gates = sorted({int(gate) for gate in group_meta.get("gates", ()) if isinstance(gate, int)})
        if not required_gates:
            circuit_payload.append(
                {
                    "type": "Circuit",
                    "name": str(group_name),
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
        circuit_payload.append(
            {
                "type": "Circuit",
                "name": str(group_name),
                "gates": required_gates,
                "present_gates": present_gates,
                "completion_pct": completion_pct,
                "missing_text": missing_text,
            }
        )
    return circuit_payload


def _build_hd_positions_lines(hd_result: HumanDesignResult) -> list[str]:
    """Build a Human Design-native POSITIONS block (no zodiac sign import)."""
    lines = [
        "POSITIONS",
        CHART_DATA_DIVIDER,
        f"{'Body':<18}  {'Sign':<11}  {'Longitude':<11}  {'G/L':<7}  {'C':<1}  {'T':<1}  {'B':<1}",
        CHART_DATA_DIVIDER,
    ]
    for activation in (*hd_result.personality_activations, *hd_result.design_activations):
        body_label = f"{'Personality' if activation.side == 'personality' else 'Design'} {activation.body}"
        sign_text = ZODIAC_NAMES[int((activation.longitude % 360.0) // 30) % 12]
        gl_text = f"{activation.gate}.{activation.line}"
        lines.append(
            f"{body_label:<18}  {sign_text:<11}  {activation.longitude:>8.3f}°  {gl_text:<7}  {activation.color:<1}  {activation.tone:<1}  {activation.base:<1}"
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


def _render_clickable_property(
    label: str,
    value: str,
    property_key: str,
    *,
    lookup_value: str | None = None,
) -> tuple[str, dict[str, object]]:
    line = f"{label}: {value} ⓘ"
    entry = {
        "kind": "hd_property",
        "property_key": property_key,
        "property_value": lookup_value if lookup_value is not None else value,
        "icon_index": len(f"{label}: {value} "),
    }
    return line, entry

def _format_split_definition(split_definition: str) -> str:
    suffix = " Definition"
    if split_definition.endswith(suffix):
        return split_definition[: -len(suffix)]
    return split_definition


def _render_channel_lines(
    defined_channels: tuple[tuple[int, int, str, str], ...],
) -> tuple[list[str], dict[int, list[dict[str, object]]]]:
    center_order = (
        "Head",
        "Ajna",
        "Throat",
        "G",
        "Ego",
        "Spleen",
        "Solar Plexus",
        "Sacral",
        "Root",
    )
    grouped: dict[str, list[tuple[int, int, str]]] = {center: [] for center in center_order}
    for gate_a, gate_b, center_a, center_b in defined_channels:
        lower_gate = min(gate_a, gate_b)
        upper_gate = max(gate_a, gate_b)
        label = f"{lower_gate}-{upper_gate}"
        grouped.setdefault(center_a, []).append((lower_gate, upper_gate, label))
        if center_b != center_a:
            grouped.setdefault(center_b, []).append((lower_gate, upper_gate, label))

    lines: list[str] = []
    info_map: dict[int, list[dict[str, object]]] = {}
    ordered_centers = [center for center in center_order if grouped.get(center)]
    ordered_centers.extend(
        sorted(center for center, entries in grouped.items() if entries and center not in center_order)
    )
    if not ordered_centers:
        return ["None"], {}
    for center in ordered_centers:
        lines.append(center)
        entries = sorted(set(grouped[center]), key=lambda item: (item[0], item[1]))
        parts: list[str] = []
        cursor = 0
        row_entries: list[dict[str, object]] = []
        for idx, (gate_a, gate_b, label) in enumerate(entries):
            token = f"{label} ⓘ"
            parts.append(token)
            row_entries.append(
                {
                    "kind": "hd_channel",
                    "gate_a": gate_a,
                    "gate_b": gate_b,
                    "center": center,
                    "icon_index": cursor + len(label) + 1,
                }
            )
            cursor += len(token)
            if idx < len(entries) - 1:
                parts.append(", ")
                cursor += 2
        lines.append("".join(parts))
        info_map[len(lines) - 1] = row_entries
    return lines, info_map


def _format_defined_centers(defined_centers: set[str]) -> str:
    if not defined_centers:
        return "None"
    center_order = (
        "Head",
        "Ajna",
        "Throat",
        "G",
        "Ego",
        "Spleen",
        "Solar Plexus",
        "Sacral",
        "Root",
    )
    ordered = [center for center in center_order if center in defined_centers]
    ordered.extend(sorted(center for center in defined_centers if center not in center_order))
    return ", ".join(ordered)


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
    type_line, type_info_entry = _render_clickable_property("Type", hd_result.hd_type, "type")
    authority_line, authority_info_entry = _render_clickable_property("Authority", hd_result.authority, "authority")
    profile_line, profile_info_entry = _render_clickable_property("Profile", hd_result.profile, "profile")
    definition_line, definition_info_entry = _render_clickable_property(
        "Definition",
        _format_split_definition(hd_result.split_definition),
        "definition",
        lookup_value=hd_result.split_definition,
    )
    strategy_line, strategy_info_entry = _render_clickable_property(
        "Strategy",
        hd_result.strategy,
        "strategy",
    )
    defined_centers_line = f"Defined Centers: {_format_defined_centers(set(hd_result.defined_centers))}"
    channel_lines, channel_info_map = _render_channel_lines(hd_result.defined_channels)

    awareness_lines: list[str] = []
    for stream_entry in build_awareness_stream_completion(active_gate_set):
        awareness_lines.append(
            f"{stream_entry['type']}: {stream_entry['name']} - {stream_entry['completion_pct']}%. {stream_entry['missing_text']}"
        )

#Chart Data Output panel output for Human Design Charts:
    rendered_lines = [
        CHART_DATA_DIVIDER,
        "CORE DESIGNATION",
        CHART_DATA_DIVIDER,
        type_line,
        authority_line,
        profile_line,
        definition_line,
        strategy_line,
        defined_centers_line,
        f"Incarnation Cross: {hd_result.incarnation_cross}",
        "",
        CHART_DATA_DIVIDER,
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
        "CHANNELS",
        CHART_DATA_DIVIDER,
        *channel_lines,
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
    for line_text, entry in (
        (type_line, type_info_entry),
        (authority_line, authority_info_entry),
        (profile_line, profile_info_entry),
        (definition_line, definition_info_entry),
        (strategy_line, strategy_info_entry),
    ):
        line_index = rendered_lines.index(line_text)
        position_info_map.setdefault(positions_start_index + line_index, []).append(entry)
    channels_header_index = rendered_lines.index("CHANNELS")
    channel_block_start = channels_header_index + 2
    for relative_line_index, entries in channel_info_map.items():
        absolute_line_index = positions_start_index + channel_block_start + relative_line_index
        position_info_map.setdefault(absolute_line_index, []).extend(entries)

    return (
        "\n".join(rendered_lines),
        position_info_map,
        {},
        {},
        positions_start_index,
    )
