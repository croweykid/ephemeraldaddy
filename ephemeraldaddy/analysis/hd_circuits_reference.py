"""Compatibility exports for Human Design circuitry helpers.

Canonical Human Design reference data and lookups live in
:mod:`ephemeraldaddy.analysis.human_design_reference`.
"""

from ephemeraldaddy.analysis.human_design_reference import (
    HD_ALL_CHANNELS,
    HD_ALL_GATES,
    HD_CHANNEL_TO_CIRCUIT,
    HD_CIRCUIT_GROUPS,
    HD_SUBCIRCUIT_INDEX,
    find_groups_for_gate,
    find_subcircuits_for_gate,
    get_channel,
    get_group,
    get_subcircuit,
)

__all__ = [
    "HD_ALL_CHANNELS",
    "HD_ALL_GATES",
    "HD_CHANNEL_TO_CIRCUIT",
    "HD_CIRCUIT_GROUPS",
    "HD_SUBCIRCUIT_INDEX",
    "find_groups_for_gate",
    "find_subcircuits_for_gate",
    "get_channel",
    "get_group",
    "get_subcircuit",
]
