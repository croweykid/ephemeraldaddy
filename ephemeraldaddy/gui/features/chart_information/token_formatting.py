"""Pure labels used by Human Design and house Chart Information tokens."""

from __future__ import annotations

from ephemeraldaddy.analysis.human_design_reference import HD_CIRCUIT_GROUPS
from ephemeraldaddy.core.human_design_system import (
    MANDALA_GATE_ORDER,
    MANDALA_START_DEGREE,
)
from ephemeraldaddy.core.interpretations import ZODIAC_NAMES
from ephemeraldaddy.semantics_formatting import format_ordinal


def ordinal_house_header(house_number: int) -> str:
    """Return the canonical heading for a numbered astrological house."""
    return f"{format_ordinal(house_number)} House"


def format_human_design_zodiac_degree(longitude: float) -> str:
    """Format an ecliptic longitude as a rounded zodiac degree and minute."""
    normalized = float(longitude) % 360.0
    sign_index = int(normalized // 30) % 12
    degree_in_sign = normalized - (sign_index * 30)
    whole_degrees = int(degree_in_sign)
    minutes = int(round((degree_in_sign - whole_degrees) * 60))
    if minutes == 60:
        whole_degrees += 1
        minutes = 0
    if whole_degrees == 30:
        whole_degrees = 0
        sign_index = (sign_index + 1) % 12
    return f"{whole_degrees}°{minutes:02d}' {ZODIAC_NAMES[sign_index]}"


def human_design_gate_degree_range_text(gate_number: int) -> str:
    """Return the zodiac span occupied by a Human Design gate."""
    try:
        gate_index = MANDALA_GATE_ORDER.index(int(gate_number))
    except ValueError:
        return "degree range unknown"
    gate_width = 360.0 / 64.0
    start_longitude = (MANDALA_START_DEGREE + (gate_index * gate_width)) % 360.0
    end_longitude = (start_longitude + gate_width) % 360.0
    return (
        f"{format_human_design_zodiac_degree(start_longitude)}–"
        f"{format_human_design_zodiac_degree(end_longitude)}"
    )


def human_design_gate_circuit_group(gate_number: int) -> str:
    """Return the normalized circuit-group label containing a gate."""
    for group_name, group_data in HD_CIRCUIT_GROUPS.items():
        gates = group_data.get("gates", ()) if isinstance(group_data, dict) else ()
        try:
            if int(gate_number) in {int(gate) for gate in gates}:
                return str(group_name).strip().lower()
        except (TypeError, ValueError):
            continue
    return "circuit unknown"


def human_design_gate_header_suffix(gate_number: int) -> str:
    """Combine a gate's circuit group and zodiac span for Chart Information."""
    return (
        f"{human_design_gate_circuit_group(gate_number)}, "
        f"{human_design_gate_degree_range_text(gate_number)}"
    )
