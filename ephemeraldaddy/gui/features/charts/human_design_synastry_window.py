from __future__ import annotations

from collections import defaultdict
from typing import Any

from ephemeraldaddy.analysis.human_design import build_human_design_result
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.human_design_system import (
    CHANNELS,
    HDActivation,
    HumanDesignResult,
    _resolve_authority,
    _resolve_strategy,
    _resolve_type,
    _split_definition,
)
from ephemeraldaddy.gui.style import CHART_DATA_DIVIDER

SYNASTRY_PRIMARY_COLOR = "#ff9f1c"
SYNASTRY_SECONDARY_COLOR = "#4ea5ff"


def _style_for_gate(gate: int, first_gate_set: set[int], second_gate_set: set[int]) -> str:
    if gate in first_gate_set and gate in second_gate_set:
        return "combined"
    return "black" if gate in first_gate_set else "red"


def _format_split_definition(split_definition: str) -> str:
    suffix = " Definition"
    if split_definition.endswith(suffix):
        return split_definition[: -len(suffix)]
    return split_definition


def build_combined_human_design_result(
    chart_a: Chart,
    chart_b: Chart,
) -> tuple[HumanDesignResult, set[int], set[int], tuple[str, ...]]:
    hd_a = build_human_design_result(chart_a)
    hd_b = build_human_design_result(chart_b)

    first_gate_set = {activation.gate for activation in (*hd_a.personality_activations, *hd_a.design_activations)}
    second_gate_set = {activation.gate for activation in (*hd_b.personality_activations, *hd_b.design_activations)}
    combined_gate_set = first_gate_set | second_gate_set

    def _clone_activation(activation: HDActivation) -> HDActivation:
        return HDActivation(
            body=activation.body,
            side=activation.side,
            longitude=activation.longitude,
            gate=activation.gate,
            line=activation.line,
            color=activation.color,
            tone=activation.tone,
            base=activation.base,
            style=_style_for_gate(activation.gate, first_gate_set, second_gate_set),
        )

    combined_activations = tuple(
        _clone_activation(activation)
        for activation in (*hd_a.personality_activations, *hd_a.design_activations)
    ) + tuple(
        _clone_activation(activation)
        for activation in (*hd_b.personality_activations, *hd_b.design_activations)
    )

    unique_channels: dict[tuple[int, int], tuple[int, int, str, str]] = {}
    for channel in CHANNELS:
        gate_a, gate_b, _center_a, _center_b = channel
        if gate_a not in combined_gate_set or gate_b not in combined_gate_set:
            continue
        channel_key = tuple(sorted((gate_a, gate_b)))
        unique_channels.setdefault(channel_key, channel)
    defined_channels = tuple(unique_channels.values())
    defined_centers = frozenset({center for _g1, _g2, center_a, center_b in defined_channels for center in (center_a, center_b)})
    hd_type = _resolve_type(set(defined_centers), defined_channels)
    authority = _resolve_authority(hd_type, set(defined_centers), defined_channels)
    strategy = _resolve_strategy(hd_type)
    split_definition = _split_definition(defined_channels)

    combined_result = HumanDesignResult(
        birth_utc=hd_a.birth_utc,
        design_utc=hd_a.design_utc,
        personality_activations=combined_activations,
        design_activations=tuple(),
        active_gates=frozenset(combined_gate_set),
        defined_channels=defined_channels,
        defined_centers=defined_centers,
        hd_type=hd_type,
        authority=authority,
        profile="-",
        strategy=strategy,
        split_definition=split_definition,
        incarnation_cross="",
    )
    combined_crosses = tuple(sorted({hd_a.incarnation_cross, hd_b.incarnation_cross}))
    return combined_result, first_gate_set, second_gate_set, combined_crosses


def build_synastry_chart_data_output(
    combined_result: HumanDesignResult,
    first_gate_set: set[int],
    second_gate_set: set[int],
    combined_crosses: tuple[str, ...],
) -> tuple[str, dict[int, Any], int]:
    info_map: dict[int, list[dict[str, object]]] = {}

    active_line_set = {(activation.gate, activation.line) for activation in combined_result.personality_activations}
    grouped_lines: dict[int, list[int]] = defaultdict(list)
    for gate, line in sorted(active_line_set, key=lambda item: (item[0], item[1])):
        grouped_lines[gate].append(line)

    lines: list[str] = [
        CHART_DATA_DIVIDER,
        "CORE DESIGNATION",
        CHART_DATA_DIVIDER,
    ]

    core_rows = [
        ("Combined Type", combined_result.hd_type, "type", combined_result.hd_type),
        ("Combined Authority", combined_result.authority, "authority", combined_result.authority),
        (
            "Combined Definition",
            _format_split_definition(combined_result.split_definition),
            "definition",
            combined_result.split_definition,
        ),
        ("Combined Strategy", combined_result.strategy, "strategy", combined_result.strategy),
    ]
    for label, value, property_key, lookup in core_rows:
        row = f"{label}: {value} ⓘ"
        lines.append(row)
        info_map[len(lines) - 1] = [
            {
                "kind": "hd_property",
                "property_key": property_key,
                "property_value": lookup,
                "icon_index": len(f"{label}: {value} "),
            }
        ]

    center_order = ("Head", "Ajna", "Throat", "G", "Ego", "Spleen", "Solar Plexus", "Sacral", "Root")
    ordered_centers = [center for center in center_order if center in combined_result.defined_centers]
    lines.append(f"Combined Defined Centers: {', '.join(ordered_centers) if ordered_centers else 'None'}")
    lines.append(
        "Combined Incarnation Cross(es): "
        + (" | ".join(combined_crosses) if combined_crosses else "N/A for combined charts")
    )
    lines.extend(["", CHART_DATA_DIVIDER, "GATES & LINES", CHART_DATA_DIVIDER])

    if not grouped_lines:
        lines.append("None")
    else:
        for gate in sorted(grouped_lines):
            line_numbers = grouped_lines[gate]
            marker = "🟧🟦" if gate in first_gate_set and gate in second_gate_set else "🟧" if gate in first_gate_set else "🟦"
            row_entries: list[dict[str, object]] = []
            parts: list[str] = []
            cursor = 0
            for idx, line_no in enumerate(line_numbers):
                token = f"{marker} {gate}.{line_no}"
                parts.append(token)
                gate_start = cursor + len(marker) + 1
                row_entries.append(
                    {
                        "kind": "hd_gate_line",
                        "gate": gate,
                        "line": line_no,
                        "span_start": gate_start,
                        "span_end": gate_start + len(f"{gate}.{line_no}"),
                    }
                )
                cursor += len(token)
                if idx < len(line_numbers) - 1:
                    parts.append(", ")
                    cursor += 2
            lines.append("".join(parts))
            info_map[len(lines) - 1] = row_entries

    lines.extend(["", CHART_DATA_DIVIDER, "CHANNELS", CHART_DATA_DIVIDER])
    channel_groups: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for gate_a, gate_b, center_a, center_b in combined_result.defined_channels:
        channel = (min(gate_a, gate_b), max(gate_a, gate_b))
        channel_groups[center_a].append(channel)
        if center_b != center_a:
            channel_groups[center_b].append(channel)

    if not channel_groups:
        lines.append("None")
    else:
        ordered_channel_centers = [center for center in center_order if center in channel_groups]
        for center in ordered_channel_centers:
            lines.append(center)
            entries = sorted(set(channel_groups[center]))
            row_entries: list[dict[str, object]] = []
            cursor = 0
            parts: list[str] = []
            for idx, (gate_a, gate_b) in enumerate(entries):
                first_has_channel = gate_a in first_gate_set and gate_b in first_gate_set
                second_has_channel = gate_a in second_gate_set and gate_b in second_gate_set
                marker = "🟧🟦" if (first_has_channel and second_has_channel) or (not first_has_channel and not second_has_channel) else "🟧" if first_has_channel else "🟦"
                label = f"{gate_a}-{gate_b}"
                token = f"{marker} {label} ⓘ"
                parts.append(token)
                row_entries.append(
                    {
                        "kind": "hd_channel",
                        "gate_a": gate_a,
                        "gate_b": gate_b,
                        "center": center,
                        "icon_index": cursor + len(marker) + 1 + len(label) + 1,
                    }
                )
                cursor += len(token)
                if idx < len(entries) - 1:
                    parts.append(", ")
                    cursor += 2
            lines.append("".join(parts))
            info_map[len(lines) - 1] = row_entries

    return "\n".join(lines), info_map, 0
