"""Human Design gate/line/channel lookup helpers."""

from __future__ import annotations

from typing import Iterable

from ephemeraldaddy.analysis.human_design_reference import HD_CHANNELS as HD_CHANNEL_REFERENCE

TOTAL_DEGREES = 360.0
NUM_GATES = 64
GATE_SIZE = TOTAL_DEGREES / NUM_GATES  # 5.625 degrees per gate
LINES_PER_GATE = 6
LINE_SIZE = GATE_SIZE / LINES_PER_GATE  # 0.9375 degrees per line

# Compact topology is derived from the metadata-rich canonical reference.
HD_CHANNELS: tuple[tuple[int, int], ...] = tuple(
    sorted(
        {
            tuple(sorted(channel["gates"]))
            for channel in HD_CHANNEL_REFERENCE.values()
        }
    )
)


def get_gate(degree: float) -> int:
    """Input degree (0 <= degree < 360); output gate number (1-64)."""
    degree = degree % TOTAL_DEGREES
    return int(degree // GATE_SIZE) + 1


def get_line(degree: float) -> tuple[int, int]:
    """Input degree (0 <= degree < 360); output (gate_number, line_number)."""
    degree = degree % TOTAL_DEGREES
    gate_num = get_gate(degree)
    gate_start_deg = (gate_num - 1) * GATE_SIZE
    deg_in_gate = degree - gate_start_deg
    line_num = int(deg_in_gate // LINE_SIZE) + 1
    return gate_num, line_num


def get_active_channels(degrees: Iterable[float]) -> set[tuple[int, int]]:
    """Return channels activated by the provided longitudes."""
    active_gates = {get_gate(degree) for degree in degrees}
    return {
        tuple(sorted((a, b)))
        for a, b in HD_CHANNELS
        if a in active_gates and b in active_gates
    }


def get_channels_for_gate(
    gate: int,
    active_channels: set[tuple[int, int]],
) -> list[str]:
    """Return active channels touching a gate, formatted as 'A-B'."""
    labels = [
        f"{a}-{b}"
        for a, b in sorted(active_channels)
        if a == gate or b == gate
    ]
    return labels
