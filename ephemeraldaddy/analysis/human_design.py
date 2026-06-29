"""Human Design summary helpers for Chart View popouts."""

from __future__ import annotations

import copy
import re
from datetime import datetime
from typing import Any

from ephemeraldaddy.core.chart import Chart, chart_uses_houses
from ephemeraldaddy.core.human_design_system import (
    CHANNELS,
    HDActivation,
    INCARNATION_CROSS_LOOKUP,
    HumanDesignResult,
    defined_centers_from_active_gates,
    defined_channels_from_active_gates,
    _resolve_authority,
    _resolve_strategy,
    _resolve_type,
    _split_definition,
    calculate_human_design,
)
from ephemeraldaddy.analysis.human_design_reference import AWARENESS_STREAMS, HD_CIRCUIT_GROUPS, HD_COLORS, HD_TONES, HD_PERSPECTIVE_NAMES, HD_DIGESTION_NAMES, HD_ENVIRONMENT_COLORS
from ephemeraldaddy.gui.style import CHART_DATA_DIVIDER
from ephemeraldaddy.analysis.hd_line_fixings import get_hd_line_fixing
from ephemeraldaddy.core.interpretations import BODY_RELATIONAL_GLYPHS

CHART_DATA_COLUMN_SEPARATOR = " … "

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


def _chart_with_hypothetical_local_time(chart: Chart, hour: int, minute: int) -> Chart:
    """Return a lightweight chart copy pinned to a hypothetical local time."""
    chart_copy = copy.copy(chart)
    source_dt = getattr(chart, "dt", None)
    if not isinstance(source_dt, datetime):
        return chart_copy
    chart_copy.dt = source_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return chart_copy


def _time_variant_human_design_results(chart: Chart) -> tuple[HumanDesignResult, HumanDesignResult, HumanDesignResult]:
    return (
        calculate_human_design(_chart_with_hypothetical_local_time(chart, 0, 0)),
        calculate_human_design(_chart_with_hypothetical_local_time(chart, 12, 0)),
        calculate_human_design(_chart_with_hypothetical_local_time(chart, 23, 59)),
    )


def hd_line_fixing_for_activation(activation: HDActivation) -> str | None:
    """Return the HD line fixing for an activation, if its body fixes the line."""
    try:
        return get_hd_line_fixing(int(activation.gate), int(activation.line), str(activation.body))
    except (KeyError, TypeError, ValueError):
        return None


def _hd_line_fixing_label(fixing: str | None) -> str:
    return "exalted" if fixing == "exaltation" else "detriment" if fixing == "detriment" else ""


def _activation_key(activation) -> tuple[str, str]:
    return str(activation.side), str(activation.body)


def _activation_variant_lookup(
    variant_results: tuple[HumanDesignResult, HumanDesignResult, HumanDesignResult] | None,
) -> dict[tuple[str, str], tuple[object, object, object]]:
    if variant_results is None:
        return {}
    lookup: dict[tuple[str, str], list[object]] = {}
    for result in variant_results:
        for activation in (*result.personality_activations, *result.design_activations):
            lookup.setdefault(_activation_key(activation), []).append(activation)
    return {key: tuple(value) for key, value in lookup.items() if len(value) == 3}


def _collapsed_time_variant_tokens(tokens: tuple[str, str, str]) -> list[str]:
    if tokens[0] == tokens[1] == tokens[2]:
        return [tokens[1]]
    rendered: list[str] = []
    for token in tokens:
        if not rendered or rendered[-1] != token:
            rendered.append(token)
    return rendered


def _format_time_variant_field(tokens: tuple[str, str, str]) -> str:
    return "->".join(_collapsed_time_variant_tokens(tokens))


def _time_variant_change_count(tokens: tuple[str, str, str]) -> int:
    return sum(
        1
        for previous_token, current_token in zip(tokens, tokens[1:])
        if previous_token != current_token
    )


def _format_single_change_or_unknown_time_variant_field(tokens: tuple[str, str, str]) -> str:
    if _time_variant_change_count(tokens) > 1:
        return "?"
    return _format_time_variant_field(tokens)


def _activation_display_values(activation, variants: tuple[object, object, object] | None) -> tuple[str, str, str, str]:
    if variants is None:
        return (
            f"{activation.gate}.{activation.line}",
            str(int(activation.color)),
            str(int(activation.tone)),
            str(int(activation.base)),
        )
    gate_line_tokens = tuple(f"{item.gate}.{item.line}" for item in variants)
    color_tokens = tuple(str(int(item.color)) for item in variants)
    tone_tokens = tuple(str(int(item.tone)) for item in variants)
    base_tokens = tuple(str(int(item.base)) for item in variants)
    return (
        _format_time_variant_field(gate_line_tokens),
        _format_single_change_or_unknown_time_variant_field(color_tokens),
        _format_single_change_or_unknown_time_variant_field(tone_tokens),
        _format_single_change_or_unknown_time_variant_field(base_tokens),
    )


def _sign_name_for_longitude(longitude: float) -> str:
    return ZODIAC_NAMES[int((float(longitude) % 360.0) // 30) % 12]


def _activation_sign_display_value(activation, variants: tuple[object, object, object] | None) -> str:
    if variants is None:
        return _sign_name_for_longitude(activation.longitude)
    sign_tokens = tuple(_sign_name_for_longitude(item.longitude) for item in variants)
    return _format_time_variant_field(sign_tokens)


def _hd_activation_consciousness_label(side: str) -> str:
    return "Conscious" if str(side).strip().lower() == "personality" else "Subconscious"


_HD_ACTIVATION_SIDE_DISPLAY_ALIASES = {
    "personality": "P.",
    "design": "D.",
}


def _hd_activation_body_display_label(activation: HDActivation) -> str:
    """Return the compact Chart Data Output label for an HD activation.

    This is intentionally a display alias only; activation.side remains the
    canonical placement side used by calculations and lookups.
    """
    side_alias = _HD_ACTIVATION_SIDE_DISPLAY_ALIASES.get(activation.side, activation.side.title())
    fixing = hd_line_fixing_for_activation(activation)
    body_name = f"{BODY_RELATIONAL_GLYPHS.get('Detriment', '')} {activation.body}" if fixing == "detriment" else str(activation.body)
    return f"{side_alias} {body_name}"


def _build_hd_positions_lines(
    hd_result: HumanDesignResult,
    *,
    time_variant_results: tuple[HumanDesignResult, HumanDesignResult, HumanDesignResult] | None = None,
) -> tuple[list[str], dict[int, list[dict[str, object]]]]:
    """Build a Human Design-native POSITIONS block (no zodiac sign import)."""
    variant_lookup = _activation_variant_lookup(time_variant_results)
    activation_rows = []
    for activation in (*hd_result.personality_activations, *hd_result.design_activations):
        display_values = _activation_display_values(
            activation,
            variant_lookup.get(_activation_key(activation)),
        )
        sign_text = _activation_sign_display_value(
            activation,
            variant_lookup.get(_activation_key(activation)),
        )
        activation_rows.append((activation, _hd_activation_body_display_label(activation), sign_text, display_values))
    body_width = max(
        len("Body"),
        *(len(body_label) for _activation, body_label, _sign_text, _display_values in activation_rows),
    )
    sign_width = max(11, *(len(sign_text) for _activation, _body_label, sign_text, _display_values in activation_rows))
    gl_width = max(
        7,
        *(
            len((BODY_RELATIONAL_GLYPHS.get("Exaltation", "") if hd_line_fixing_for_activation(_activation) == "exaltation" else "") + display_values[0])
            for _activation, _body_label, _sign_text, display_values in activation_rows
        ),
    )
    c_width = max(1, *(len(display_values[1]) for _activation, _body_label, _sign_text, display_values in activation_rows))
    t_width = max(1, *(len(display_values[2]) for _activation, _body_label, _sign_text, display_values in activation_rows))
    b_width = max(1, *(len(display_values[3]) for _activation, _body_label, _sign_text, display_values in activation_rows))
    header_line = CHART_DATA_COLUMN_SEPARATOR.join([
        f"{'Body':<{body_width}}",
        f"{'Sign':<{sign_width}}",
        f"{'Degree':<11}",
        f"{'G/L':<{gl_width}}",
        f"{'C':<{c_width}}",
        f"{'T':<{t_width}}",
        f"{'B':<{b_width}}",
    ])
    lines = [
        "POSITIONS",
        CHART_DATA_DIVIDER,
        header_line,
        CHART_DATA_DIVIDER,
    ]
    info_map: dict[int, list[dict[str, object]]] = {}
    for activation, body_label, sign_text, (gl_text, color_text, tone_text, base_text) in activation_rows:
        displayed_gl_text = BODY_RELATIONAL_GLYPHS.get("Exaltation", "") + gl_text if hd_line_fixing_for_activation(activation) == "exaltation" else gl_text
        line_text = (
            CHART_DATA_COLUMN_SEPARATOR.join([
                f"{body_label:<{body_width}}",
                f"{sign_text:<{sign_width}}",
                f"{activation.longitude:>8.3f}°",
                f"{(displayed_gl_text):<{gl_width}}",
                f"{color_text:<{c_width}}",
                f"{tone_text:<{t_width}}",
                f"{base_text:<{b_width}}",
            ])
            + " ⓘ"
        )
        lines.append(line_text)
        body_start = line_text.find(body_label)
        sign_start = line_text.find(sign_text, body_start + len(body_label)) if body_start != -1 else line_text.find(sign_text)
        gl_start = line_text.find(displayed_gl_text)
        color_start = line_text.find(color_text, gl_start + len(gl_text))
        tone_start = line_text.find(tone_text, color_start + len(color_text)) if color_start != -1 else -1
        base_start = line_text.find(base_text, tone_start + len(tone_text)) if tone_start != -1 else -1
        line_entries: list[dict[str, object]] = []
        display_body_label = f"{activation.body} ({_hd_activation_consciousness_label(activation.side)})"
        if body_start != -1:
            line_entries.append(
                {
                    "kind": "hd_position_body",
                    "body": str(activation.body),
                    "side": str(activation.side),
                    "sign": _sign_name_for_longitude(activation.longitude),
                    "display_body": display_body_label,
                    "span_start": body_start,
                    "span_end": body_start + len(body_label),
                }
            )
        if sign_start != -1:
            for sign_match in re.finditer("|".join(re.escape(name) for name in ZODIAC_NAMES), sign_text):
                sign_name = sign_match.group(0)
                line_entries.append(
                    {
                        "kind": "sign_keyword",
                        "sign": sign_name,
                        "body": str(activation.body),
                        "display_body": display_body_label,
                        "span_start": sign_start + sign_match.start(),
                        "span_end": sign_start + sign_match.end(),
                    }
                )
        if gl_start != -1:
            first_gate_line_entry: dict[str, object] | None = None
            for gl_match in re.finditer(rf"(?<![\d.])({_GATE_NUMBER_PATTERN})\.([1-6])(?![\d.])", gl_text):
                gate_line_entry = {
                    "kind": "hd_gate_line",
                    "gate": int(gl_match.group(1)),
                    "line": int(gl_match.group(2)),
                    "span_start": gl_start + gl_match.start(),
                    "span_end": gl_start + gl_match.end(),
                }
                if first_gate_line_entry is None:
                    first_gate_line_entry = gate_line_entry
                line_entries.append(gate_line_entry)
            icon_index = line_text.rfind("ⓘ")
            if first_gate_line_entry is not None and icon_index != -1:
                line_entries.append(
                    {
                        **first_gate_line_entry,
                        "span_start": icon_index,
                        "span_end": icon_index + len("ⓘ"),
                        "icon_index": icon_index,
                    }
                )
        if color_start != -1:
            for color_match in re.finditer(r"(?<!\d)([1-6])(?!\d)", color_text):
                line_entries.append(
                    {
                        "kind": "hd_color",
                        "color": int(color_match.group(1)),
                        "span_start": color_start + color_match.start(1),
                        "span_end": color_start + color_match.end(1),
                    }
                )
        if tone_start != -1:
            for tone_match in re.finditer(r"(?<!\d)([1-6])(?!\d)", tone_text):
                line_entries.append(
                    {
                        "kind": "hd_tone",
                        "tone": int(tone_match.group(1)),
                        "span_start": tone_start + tone_match.start(1),
                        "span_end": tone_start + tone_match.end(1),
                    }
                )
        if base_start != -1:
            for base_match in re.finditer(r"(?<!\d)([1-5])(?!\d)", base_text):
                line_entries.append(
                    {
                        "kind": "hd_base",
                        "base": int(base_match.group(1)),
                        "span_start": base_start + base_match.start(1),
                        "span_end": base_start + base_match.end(1),
                    }
                )
        if line_entries:
            info_map[len(lines) - 1] = line_entries
    return lines, info_map


def _render_clickable_gates(active_gates: set[int]) -> tuple[str, list[dict[str, object]]]:
    if not active_gates:
        return "None", []
    parts: list[str] = []
    info_entries: list[dict[str, object]] = []
    cursor = 0
    for idx, gate in enumerate(sorted(active_gates)):
        token = f"{gate}"
        parts.append(token)
        span_start = cursor
        span_end = cursor + len(token)
        info_entries.append(
            {
                "kind": "hd_gate_line",
                "gate": gate,
                "line": None,
                "span_start": span_start,
                "span_end": span_end,
            }
        )
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
        token = label
        parts.append(token)
        span_start = cursor
        span_end = cursor + len(token)
        info_entries.append(
            {
                "kind": "hd_gate_line",
                "gate": gate,
                "line": line,
                "span_start": span_start,
                "span_end": span_end,
            }
        )
        cursor += len(token)
        if idx < len(sorted_lines) - 1:
            parts.append(", ")
            cursor += 2
    return "".join(parts), info_entries


def _render_clickable_gate_line_summary(
    active_lines: set[tuple[int, int]],
    activations: tuple[HDActivation, ...] = (),
) -> tuple[list[str], dict[int, list[dict[str, object]]]]:
    if not active_lines:
        return ["None"], {}
    fixing_by_line: dict[tuple[int, int], str] = {}
    for activation in activations:
        fixing = hd_line_fixing_for_activation(activation)
        if fixing and (int(activation.gate), int(activation.line)) not in fixing_by_line:
            fixing_by_line[(int(activation.gate), int(activation.line))] = fixing
    grouped_lines: dict[int, list[int]] = {}
    for gate, line in sorted(active_lines, key=lambda item: (item[0], item[1])):
        grouped_lines.setdefault(gate, []).append(line)
    rendered_rows: list[str] = []
    row_info_map: dict[int, list[dict[str, object]]] = {}
    for gate in sorted(grouped_lines):
        line_numbers = grouped_lines[gate]
        parts: list[str] = []
        row_entries: list[dict[str, object]] = []
        cursor = 0
        for idx, line in enumerate(line_numbers):
            label = f"{gate}.{line}"
            prefix = BODY_RELATIONAL_GLYPHS.get("Exaltation", "") if fixing_by_line.get((gate, line)) == "exaltation" else ""
            token = f"{prefix}{label}"
            parts.append(token)
            span_start = cursor + len(prefix)
            span_end = span_start + len(label)
            row_entries.append(
                {
                    "kind": "hd_gate_line",
                    "gate": gate,
                    "line": line,
                    "span_start": span_start,
                    "span_end": span_end,
                }
            )
            cursor += len(token)
            if idx < len(line_numbers) - 1:
                separator = ", "
                parts.append(separator)
                cursor += len(separator)
        row_index = len(rendered_rows)
        rendered_rows.append("".join(parts))
        row_info_map[row_index] = row_entries
    return rendered_rows, row_info_map


def describe_gate_line_placements(
    chart: Chart,
    gate: int,
    line: int | None = None,
) -> list[str]:
    """Return formatted placement lines for a gate or gate/line in a chart."""
    gate_number = int(gate)
    line_number = int(line) if isinstance(line, int) else None
    hd_result = calculate_human_design(chart)
    matches: list[str] = []
    for activation in (*hd_result.personality_activations, *hd_result.design_activations):
        if int(activation.gate) != gate_number:
            continue
        if line_number is not None and int(activation.line) != line_number:
            continue
        side_label = "Personality" if activation.side == "personality" else "Design"
        sign_name = ZODIAC_NAMES[int((float(activation.longitude) % 360.0) // 30) % 12]
        fixing_label = _hd_line_fixing_label(hd_line_fixing_for_activation(activation))
        line_label = f"{int(activation.gate)}.{int(activation.line)}" + (f" ({fixing_label})" if fixing_label else "")
        matches.append(
            f"• {side_label} {activation.body}: {line_label} in {sign_name}"
        )
    return matches


def describe_synastry_gate_line_placements(
    chart_contexts: list[tuple[str, Chart]],
    gate: int,
    line: int | None = None,
) -> list[str]:
    """Return placement lines for a gate or gate/line across a synastry pair."""
    matches: list[str] = []
    for fallback_index, (chart_label, chart) in enumerate(chart_contexts, start=1):
        label = str(chart_label or f"Chart {fallback_index}").strip() or f"Chart {fallback_index}"
        for placement_line in describe_gate_line_placements(chart, gate, line):
            placement_text = placement_line[2:] if placement_line.startswith("• ") else placement_line
            matches.append(f"• {label}'s {placement_text}")
    return matches


def gate_lines_for_gate(hd_result: HumanDesignResult, gate: int) -> list[int]:
    """Return unique sorted active lines for a gate from an HD result."""
    gate_number = int(gate)
    lines = {
        int(activation.line)
        for activation in (*hd_result.personality_activations, *hd_result.design_activations)
        if int(activation.gate) == gate_number
    }
    return sorted(lines)


def _render_clickable_property(
    label: str,
    value: str,
    property_key: str,
    *,
    lookup_value: str | None = None,
) -> tuple[str, dict[str, object]]:
    value_text = str(value or "").strip() or "Unknown"
    line = f"{label}: {value_text} ⓘ"
    value_start = len(f"{label}: ")
    icon_index = len(f"{label}: {value_text} ")
    entry = {
        "kind": "hd_property",
        "property_key": property_key,
        "property_value": lookup_value if lookup_value is not None else value_text,
        "span_start": value_start,
        "span_end": icon_index + 1,
        "icon_index": icon_index,
    }
    return line, entry


def _render_clickable_incarnation_cross_line(
    label: str,
    cross_names: list[str],
) -> tuple[str, list[dict[str, object]]]:
    value_text = ", ".join(cross_names) if cross_names else "Unknown"
    line = f"{label}: {value_text} ⓘ"
    if not cross_names:
        return line, []
    entries: list[dict[str, object]] = []
    value_start = len(f"{label}: ")
    search_start = value_start
    for cross_name in cross_names:
        span_start = line.find(cross_name, search_start)
        if span_start == -1:
            continue
        span_end = span_start + len(cross_name)
        entries.append(
            {
                "kind": "hd_property",
                "property_key": "incarnation_cross",
                "property_value": cross_name,
                "span_start": span_start,
                "span_end": span_end,
                "icon_index": len(line) - 1,
            }
        )
        search_start = span_end
    return line, entries

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
                    "span_start": cursor,
                    "span_end": cursor + len(token),
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


def _hd_meta_entry_by_value(entries: object, value: int) -> dict[str, object]:
    """Return Human Design reference metadata for a numeric color/tone value."""
    try:
        target_value = int(value)
    except (TypeError, ValueError):
        return {}
    if isinstance(entries, dict):
        raw_entry = entries.get(target_value)
        return raw_entry if isinstance(raw_entry, dict) else {}
    if isinstance(entries, (list, tuple)):
        for raw_entry in entries:
            if not isinstance(raw_entry, dict):
                continue
            try:
                entry_value = int(raw_entry.get("value", -1))
            except (TypeError, ValueError):
                continue
            if entry_value == target_value:
                return raw_entry
    return {}


def _hd_activation_by_body(hd_result: HumanDesignResult, *, side: str, body: str) -> HDActivation | None:
    """Return a Human Design activation by side and body name."""
    activations = (
        hd_result.design_activations
        if str(side).strip().lower() == "design"
        else hd_result.personality_activations
    )
    body_key = str(body).strip().lower()
    return next(
        (
            activation
            for activation in activations
            if str(activation.body).strip().lower() == body_key
        ),
        None,
    )


def _design_rahu_activation(hd_result: HumanDesignResult) -> HDActivation | None:
    """Return the Design-side Rahu activation that defines HD environment metadata."""
    return _hd_activation_by_body(hd_result, side="design", body="Rahu")


def _color_name_for_activation(activation: HDActivation | None) -> str:
    """Return the Human Design Color name for an activation."""
    if activation is None:
        return "Unknown"
    color_entry = _hd_meta_entry_by_value(HD_COLORS, int(activation.color))
    return str(color_entry.get("name", "Unknown")).strip().title() or "Unknown"


def _motivation_name_for_activation(activation: HDActivation | None) -> str:
    """Return the Human Design Motivation name for an activation's Color."""
    if activation is None:
        return "Unknown"
    color_entry = _hd_meta_entry_by_value(HD_COLORS, int(activation.color))
    return str(color_entry.get("motivation", "Unknown")).strip().title() or "Unknown"


def digestion_orientation_from_tone(tone: int) -> str:
    """Return the digestion subvariant orientation encoded by Tone."""
    tone_value = int(tone)
    if tone_value in (1, 2, 3):
        return "left"
    if tone_value in (4, 5, 6):
        return "right"
    raise ValueError("tone must be 1-6")


def _tone_orientation_for_activation(activation: HDActivation | None) -> str:
    """Return the left/right Tone orientation for an activation."""
    if activation is None:
        return ""
    try:
        return digestion_orientation_from_tone(int(activation.tone))
    except ValueError:
        tone_entry = _hd_meta_entry_by_value(HD_TONES, int(activation.tone))
        return str(tone_entry.get("orientation", "")).strip().lower()


def _perspective_name_for_activation(activation: HDActivation | None) -> str:
    """Return the Human Design Perspective/View label for an activation's Color."""
    if activation is None:
        return "Unknown"
    perspective_entry = HD_PERSPECTIVE_NAMES.get(int(activation.color))
    if isinstance(perspective_entry, dict):
        return str(perspective_entry.get("name", "Unknown")).strip() or "Unknown"
    return str(perspective_entry or "Unknown").strip() or "Unknown"


def _digestion_variant_label(raw_variant: object) -> str:
    """Return the short digestion variant label before any explanatory colon."""
    variant_text = str(raw_variant or "").strip()
    if not variant_text:
        return "Unknown"
    return variant_text.split(":", 1)[0].strip() or variant_text


def _digestion_details_for_activation(activation: HDActivation | None) -> dict[str, str]:
    """Return digestion determination, Tone, and subvariant details for an activation."""
    if activation is None:
        return {
            "display": "Unknown",
            "determination": "Unknown",
            "tone": "",
            "orientation": "",
            "variant": "Unknown",
            "variant_text": "",
            "description": "",
        }
    digestion_entry = HD_DIGESTION_NAMES.get(int(activation.color))
    if not isinstance(digestion_entry, dict):
        return {
            "display": "Unknown",
            "determination": "Unknown",
            "tone": str(int(activation.tone)),
            "orientation": _tone_orientation_for_activation(activation),
            "variant": "Unknown",
            "variant_text": "",
            "description": "",
        }

    digestion_name = str(digestion_entry.get("name", "Unknown")).strip() or "Unknown"
    tone_value = str(int(activation.tone))
    orientation = _tone_orientation_for_activation(activation)
    variant_text = str(digestion_entry.get(orientation, "") or "").strip()
    variant_label = _digestion_variant_label(variant_text)
    description = variant_text.split(":", 1)[1].strip() if ":" in variant_text else ""
    display = f"{digestion_name}  — {variant_label}" if variant_label != "Unknown" else digestion_name
    info_value = f"{display} (Tone {tone_value})" if variant_label != "Unknown" else digestion_name
    return {
        "display": display,
        "info_value": info_value,
        "determination": digestion_name,
        "tone": tone_value,
        "orientation": orientation,
        "variant": variant_label,
        "variant_text": variant_text,
        "description": description,
    }


def _digestion_name_for_activation(activation: HDActivation | None) -> str:
    """Return the Human Design Digestion/Determination label for an activation."""
    return _digestion_details_for_activation(activation).get("display", "Unknown") or "Unknown"


def _environment_details_for_activation(activation: HDActivation | None) -> dict[str, str]:
    """Return environment macro-name, Tone, and left/right subvariant details."""
    if activation is None:
        return {
            "display": "Unknown",
            "environment": "Unknown",
            "tone": "",
            "orientation": "",
            "variant": "Unknown",
        }
    environment_entry = HD_ENVIRONMENT_COLORS.get(int(activation.color))
    if not isinstance(environment_entry, dict):
        color_name = _color_name_for_activation(activation)
        return {
            "display": color_name,
            "environment": color_name,
            "tone": str(int(activation.tone)),
            "orientation": _tone_orientation_for_activation(activation),
            "variant": "Unknown",
        }

    environment_name = str(environment_entry.get("name", "Unknown")).strip().title() or "Unknown"
    tone_value = str(int(activation.tone))
    orientation = _tone_orientation_for_activation(activation)
    variant = str(environment_entry.get(orientation, "Unknown")).strip().title() or "Unknown"
    display = f"{environment_name}  — {variant}" if variant != "Unknown" else environment_name
    info_value = f"{display} (Tone {tone_value})" if variant != "Unknown" else environment_name
    return {
        "display": display,
        "info_value": info_value,
        "environment": environment_name,
        "tone": tone_value,
        "orientation": orientation,
        "variant": variant,
    }


def _environment_name_for_activation(activation: HDActivation | None) -> str:
    """Build the display environment label from an activation's Color and Tone."""
    return _environment_details_for_activation(activation).get("display", "Unknown") or "Unknown"


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
    time_variant_results = None if chart_uses_houses(chart) else _time_variant_human_design_results(chart)
    position_lines, positions_info_map = _build_hd_positions_lines(
        hd_result,
        time_variant_results=time_variant_results,
    )
    activations = (*hd_result.personality_activations, *hd_result.design_activations)
    active_gate_set = {activation.gate for activation in activations}
    active_line_set = {(activation.gate, activation.line) for activation in activations}

    gate_line_lines, gate_line_info_map = _render_clickable_gate_line_summary(active_line_set, activations)
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
    environment_details = _environment_details_for_activation(_design_rahu_activation(hd_result))
    environment_line, environment_info_entry = _render_clickable_property(
        "Environment",
        environment_details.get("display", "Unknown"),
        "environment",
        lookup_value=environment_details.get("info_value"),
    )
    perspective_name = _perspective_name_for_activation(
        _hd_activation_by_body(hd_result, side="personality", body="Rahu")
    )
    perspective_line, perspective_info_entry = _render_clickable_property(
        "Perspective",
        perspective_name,
        "perspective",
    )
    motivation_name = _motivation_name_for_activation(
        _hd_activation_by_body(hd_result, side="personality", body="Sun")
    )
    motivation_line, motivation_info_entry = _render_clickable_property(
        "Motivation",
        motivation_name,
        "motivation",
    )
    digestion_details = _digestion_details_for_activation(_hd_activation_by_body(hd_result, side="design", body="Sun"))
    digestion_line, digestion_info_entry = _render_clickable_property(
        "Digestion",
        digestion_details.get("display", "Unknown"),
        "digestion",
        lookup_value=digestion_details.get("info_value"),
    )
    incarnation_cross_line, incarnation_cross_entries = _render_clickable_incarnation_cross_line(
        "Incarnation Cross",
        [hd_result.incarnation_cross] if str(hd_result.incarnation_cross or "").strip() else [],
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
        incarnation_cross_line,
        environment_line,
        perspective_line,
        motivation_line,
        digestion_line,
        "",
        CHART_DATA_DIVIDER,
        *position_lines,
        "",
        CHART_DATA_DIVIDER,
        "GATES & LINES",
        CHART_DATA_DIVIDER,
        *gate_line_lines,
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
    gates_lines_header_index = rendered_lines.index("GATES & LINES")
    gates_lines_block_start = gates_lines_header_index + 2
    for relative_line_index, entries in gate_line_info_map.items():
        absolute_line_index = positions_start_index + gates_lines_block_start + relative_line_index
        position_info_map.setdefault(absolute_line_index, []).extend(entries)
    positions_header_index = rendered_lines.index("POSITIONS")
    for relative_line_index, entries in positions_info_map.items():
        absolute_line_index = positions_start_index + positions_header_index + relative_line_index
        position_info_map.setdefault(absolute_line_index, []).extend(entries)
    for line_text, entry in (
        (type_line, type_info_entry),
        (authority_line, authority_info_entry),
        (profile_line, profile_info_entry),
        (definition_line, definition_info_entry),
        (strategy_line, strategy_info_entry),
        (incarnation_cross_line, incarnation_cross_entries[0] if incarnation_cross_entries else None),
        (environment_line, environment_info_entry),
        (perspective_line, perspective_info_entry),
        (motivation_line, motivation_info_entry),
        (digestion_line, digestion_info_entry),
    ):
        line_index = rendered_lines.index(line_text)
        if entry is not None:
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


_GATE_NUMBER_PATTERN = r"[1-9]|[1-5][0-9]|6[0-4]"
_GATE_LINE_TOKEN_RE = re.compile(
    rf"(?<![\d.])(?P<gate>{_GATE_NUMBER_PATTERN})(?:\.(?P<line>[1-6]))?(?![\d.%])"
)
_CHANNEL_TOKEN_RE = re.compile(
    rf"(?<![\d.])(?P<gate_a>{_GATE_NUMBER_PATTERN})-(?P<gate_b>{_GATE_NUMBER_PATTERN})(?![\d.])"
)


def _qt_text_offset(text: str, index: int) -> int:
    """Return the QTextCursor-compatible UTF-16 code-unit offset for a Python index."""
    return len(text[:index].encode("utf-16-le")) // 2


def _qt_text_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Return a QTextCursor-compatible span for Python regex match indices."""
    return _qt_text_offset(text, start), _qt_text_offset(text, end)


def _qt_click_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Return a forgiving QTextCursor-compatible click span for token hit testing.

    QTextCursor positions represent insertion points between glyphs, so clicking the
    right side of the final glyph in a token can produce the position immediately
    after that token. Include that trailing insertion point and the preceding
    whitespace separator so short gate/channel tokens are easy to click without
    overlapping the next token's span.
    """
    expanded_start = start
    if expanded_start > 0 and text[expanded_start - 1] in {" ", "\t"}:
        expanded_start -= 1
    span_start, span_end = _qt_text_span(text, expanded_start, end)
    return span_start, span_end + 1


def _find_channel_tokens(line_text: str) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for match in _CHANNEL_TOKEN_RE.finditer(line_text):
        try:
            gate_a = int(match.group("gate_a"))
            gate_b = int(match.group("gate_b"))
        except (TypeError, ValueError):
            continue
        span_start, span_end = _qt_click_span(line_text, match.start(), match.end())
        entries.append(
            {
                "kind": "hd_channel",
                "gate_a": min(gate_a, gate_b),
                "gate_b": max(gate_a, gate_b),
                "center": "",
                "span_start": span_start,
                "span_end": span_end,
            }
        )
    return entries


def _find_gate_line_tokens(line_text: str) -> list[dict[str, object]]:
    """Return clickable gate/gate-line entries for HD synastry free-text rows."""
    entries: list[dict[str, object]] = []
    for match in _GATE_LINE_TOKEN_RE.finditer(line_text):
        gate_text = match.group("gate")
        line_text_value = match.group("line")
        try:
            gate_number = int(gate_text)
            line_number = int(line_text_value) if line_text_value is not None else None
        except (TypeError, ValueError):
            continue
        span_start, span_end = _qt_click_span(line_text, match.start(), match.end())
        entries.append(
            {
                "kind": "hd_gate_line",
                "gate": gate_number,
                "line": line_number,
                "span_start": span_start,
                "span_end": span_end,
            }
        )
    return entries


def _add_synastry_gate_token_entries(
    rendered_lines: list[str],
    position_info_map: dict[int, Any],
    *,
    excluded_line_indices: set[int] | None = None,
) -> None:
    """Make otherwise-unmapped gate numbers in synastry output clickable."""
    excluded = excluded_line_indices or set()
    for line_index, line_text in enumerate(rendered_lines):
        if line_index in excluded:
            continue
        existing_entries = position_info_map.setdefault(line_index, [])
        existing_spans = [
            (int(entry["span_start"]), int(entry["span_end"]))
            for entry in existing_entries
            if isinstance(entry.get("span_start"), int) and isinstance(entry.get("span_end"), int)
        ]
        for entry in _find_channel_tokens(line_text):
            span_start = int(entry["span_start"])
            span_end = int(entry["span_end"])
            if any(
                span_start < existing_end and span_end > existing_start
                for existing_start, existing_end in existing_spans
            ):
                continue
            existing_entries.append(entry)
            existing_spans.append((span_start, span_end))
        for entry in _find_gate_line_tokens(line_text):
            span_start = int(entry["span_start"])
            span_end = int(entry["span_end"])
            if any(
                span_start < existing_end and span_end > existing_start
                for existing_start, existing_end in existing_spans
            ):
                continue
            existing_entries.append(entry)
        if not existing_entries:
            position_info_map.pop(line_index, None)


def build_human_design_synastry_data_output(
    hd_a: HumanDesignResult,
    hd_b: HumanDesignResult,
    *,
    chart_a_name: str = "Chart A",
    chart_b_name: str = "Chart B",
) -> tuple[str, dict[int, Any], int]:
    """Build synastry HD output treating two charts as one aggregate chart."""
    active_lines = {
        (activation.gate, activation.line)
        for activation in (
            *hd_a.personality_activations,
            *hd_a.design_activations,
            *hd_b.personality_activations,
            *hd_b.design_activations,
        )
    }
    active_gates = {gate for gate, _line in active_lines}
    chart_a_active_gates = {
        activation.gate for activation in (*hd_a.personality_activations, *hd_a.design_activations)
    }
    chart_b_active_gates = {
        activation.gate for activation in (*hd_b.personality_activations, *hd_b.design_activations)
    }
    chart_a_channels = sorted(
        {
            f"{min(gate_a, gate_b)}-{max(gate_a, gate_b)}"
            for gate_a, gate_b, _center_a, _center_b in CHANNELS
            if gate_a in chart_a_active_gates and gate_b in chart_a_active_gates
        }
    )
    chart_b_channels = sorted(
        {
            f"{min(gate_a, gate_b)}-{max(gate_a, gate_b)}"
            for gate_a, gate_b, _center_a, _center_b in CHANNELS
            if gate_a in chart_b_active_gates and gate_b in chart_b_active_gates
        }
    )
    defined_channels = defined_channels_from_active_gates(active_gates)
    defined_centers = set(defined_centers_from_active_gates(active_gates))
    combined_type = _resolve_type(defined_centers, defined_channels)
    combined_authority = _resolve_authority(combined_type, defined_centers, defined_channels)
    combined_definition = _split_definition(defined_channels)
    combined_strategy = _resolve_strategy(combined_type)

    combined_crosses: list[str] = []
    for hd_result in (hd_a, hd_b):
        sun_personality = next((a for a in hd_result.personality_activations if a.body == "Sun"), None)
        earth_personality = next((a for a in hd_result.personality_activations if a.body == "Earth"), None)
        sun_design = next((a for a in hd_result.design_activations if a.body == "Sun"), None)
        earth_design = next((a for a in hd_result.design_activations if a.body == "Earth"), None)
        if not all((sun_personality, earth_personality, sun_design, earth_design)):
            continue
        cross_key = (
            int(sun_personality.gate),
            int(earth_personality.gate),
            int(sun_design.gate),
            int(earth_design.gate),
        )
        cross_name = INCARNATION_CROSS_LOOKUP.get(cross_key)
        if cross_name and cross_name not in combined_crosses:
            combined_crosses.append(cross_name)

    type_line, type_entry = _render_clickable_property("Combined Type", combined_type, "type")
    auth_line, auth_entry = _render_clickable_property("Combined Authority", combined_authority, "authority")
    definition_line, definition_entry = _render_clickable_property(
        "Combined Definition",
        _format_split_definition(combined_definition),
        "definition",
        lookup_value=combined_definition,
    )
    strategy_line, strategy_entry = _render_clickable_property(
        "Combined Strategy",
        combined_strategy,
        "strategy",
    )
    incarnation_cross_line, incarnation_cross_entries = _render_clickable_incarnation_cross_line(
        "Combined Incarnation Cross(es)",
        combined_crosses,
    )

    channel_lines, channel_info_map = _render_channel_lines(defined_channels)
    all_activations = (*hd_a.personality_activations, *hd_a.design_activations, *hd_b.personality_activations, *hd_b.design_activations)
    gate_line_lines, gate_line_info_map = _render_clickable_gate_line_summary(active_lines, all_activations)
    awareness_lines = [
        f"{stream_entry['type']}: {stream_entry['name']} - {stream_entry['completion_pct']}%. {stream_entry['missing_text']}"
        for stream_entry in build_awareness_stream_completion(active_gates)
    ]
    chart_a_label = str(chart_a_name or "Chart A").strip() or "Chart A"
    chart_b_label = str(chart_b_name or "Chart B").strip() or "Chart B"
    chart_a_gates_text = ", ".join(str(gate) for gate in sorted(chart_a_active_gates)) if chart_a_active_gates else "None"
    chart_b_gates_text = ", ".join(str(gate) for gate in sorted(chart_b_active_gates)) if chart_b_active_gates else "None"
    chart_a_channels_text = ", ".join(chart_a_channels) if chart_a_channels else "None"
    chart_b_channels_text = ", ".join(chart_b_channels) if chart_b_channels else "None"

    rendered_lines = [
        CHART_DATA_DIVIDER,
        "CORE DESIGNATION",
        CHART_DATA_DIVIDER,
        type_line,
        auth_line,
        definition_line,
        strategy_line,
        f"Combined Defined Centers: {_format_defined_centers(defined_centers)}",
        incarnation_cross_line,
        "",
        f"{chart_a_label}'s active gates: {chart_a_gates_text}",
        f"{chart_b_label}'s active gates: {chart_b_gates_text}",
        f"{chart_a_label}'s active channel(s): {chart_a_channels_text}",
        f"{chart_b_label}'s active channel(s): {chart_b_channels_text}",
        "",
        CHART_DATA_DIVIDER,
        "GATES & LINES",
        CHART_DATA_DIVIDER,
        *gate_line_lines,
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

    position_info_map: dict[int, Any] = {}
    for line_text, entry in (
        (type_line, type_entry),
        (auth_line, auth_entry),
        (definition_line, definition_entry),
        (strategy_line, strategy_entry),
    ):
        position_info_map.setdefault(rendered_lines.index(line_text), []).append(entry)

    incarnation_cross_line_index = rendered_lines.index(incarnation_cross_line)
    if incarnation_cross_entries:
        position_info_map.setdefault(incarnation_cross_line_index, []).extend(incarnation_cross_entries)

    gates_header_index = rendered_lines.index("GATES & LINES")
    for relative_line_index, entries in gate_line_info_map.items():
        position_info_map.setdefault(gates_header_index + 2 + relative_line_index, []).extend(entries)

    channels_header_index = rendered_lines.index("CHANNELS")
    channel_line_indices: set[int] = set()
    for relative_line_index, entries in channel_info_map.items():
        absolute_line_index = channels_header_index + 2 + relative_line_index
        position_info_map.setdefault(absolute_line_index, []).extend(entries)
        channel_line_indices.add(absolute_line_index)

    _add_synastry_gate_token_entries(
        rendered_lines,
        position_info_map,
        excluded_line_indices=channel_line_indices,
    )

    return "\n".join(rendered_lines), position_info_map, 0
