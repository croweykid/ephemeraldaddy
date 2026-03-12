"""Human Design gate/line/channel lookup helpers."""

from __future__ import annotations

from typing import Iterable

TOTAL_DEGREES = 360.0
NUM_GATES = 64
GATE_SIZE = TOTAL_DEGREES / NUM_GATES  # 5.625 degrees per gate
LINES_PER_GATE = 6
LINE_SIZE = GATE_SIZE / LINES_PER_GATE  # 0.9375 degrees per line

# Canonical Human Design channels as gate pairs.
HD_CHANNELS: tuple[tuple[int, int], ...] = (
    (1, 8), (2, 14), (3, 60), (4, 63), (5, 15), (6, 59),
    (7, 31), (9, 52), (10, 20), (10, 34), (10, 57), (11, 56),
    (12, 22), (13, 33), (16, 48), (17, 62), (18, 58), (19, 49),
    (20, 34), (20, 57), (21, 45), (23, 43), (24, 61), (25, 51),
    (26, 44), (27, 50), (28, 38), (29, 46), (30, 41), (32, 54),
    (34, 57), (35, 36), (37, 40), (39, 55), (42, 53), (47, 64),
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
