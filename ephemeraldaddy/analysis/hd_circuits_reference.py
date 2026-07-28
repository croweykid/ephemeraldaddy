"""
Human Design circuitry reference.

Compiled from public Human Design circuitry references. This module models the
3 main circuit groups and the 7 commonly named subcircuits / channel groups.

Notes:
- Human Design sources agree on 3 major circuit groups: Individual, Collective,
  and Tribal.
- They commonly break these into 7 named subcircuits:
  Integration, Knowing, Centering, Logic, Abstract, Ego, and Defense.
- Integration is sometimes described as a channel group rather than a full
  subcircuit. It is included here because many practitioners treat it that way
  in software and teaching materials.

Primary reference pages used when compiling:
- Jovian Archive: What is Circuitry in Human Design?
- HumDes Knowledge Base: Circuitry in Human Design
- Health Manifested: Human Design Circuitry

This file is intentionally practical rather than doctrinal.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


from ephemeraldaddy.analysis.human_design_circuits import HD_CIRCUIT_GROUPS


HD_ALL_CHANNELS: List[dict] = [
    {
        "group": group_name,
        "subcircuit": subcircuit_name,
        "channel": channel,
        "name": name,
        "gates": gates,
    }
    for group_name, group_data in HD_CIRCUIT_GROUPS.items()
    for subcircuit_name, subcircuit_data in group_data["subcircuits"].items()
    for channel, name, gates in subcircuit_data["channels"]
]

HD_ALL_GATES: Tuple[int, ...] = tuple(
    sorted({gate for channel in HD_ALL_CHANNELS for gate in channel["gates"]})
)

HD_SUBCIRCUIT_INDEX: Dict[str, dict] = {
    sub_name: sub_data
    for group_data in HD_CIRCUIT_GROUPS.values()
    for sub_name, sub_data in group_data["subcircuits"].items()
}

HD_CHANNEL_TO_CIRCUIT: Dict[str, dict] = {
    item["channel"]: item
    for item in HD_ALL_CHANNELS
}


def get_group(name: str) -> Optional[dict]:
    """Return a main circuit group by exact name."""
    return HD_CIRCUIT_GROUPS.get(name)


def get_subcircuit(name: str) -> Optional[dict]:
    """Return a subcircuit by exact canonical name."""
    return HD_SUBCIRCUIT_INDEX.get(name)


def get_channel(channel: str) -> Optional[dict]:
    """
    Return metadata for a channel key like '34-57' or '57-34'.
    """
    if channel in HD_CHANNEL_TO_CIRCUIT:
        return HD_CHANNEL_TO_CIRCUIT[channel]
    a, b = channel.split("-")
    flipped = f"{b}-{a}"
    return HD_CHANNEL_TO_CIRCUIT.get(flipped)


def find_subcircuits_for_gate(gate: int) -> List[str]:
    """Return canonical subcircuit names containing a gate."""
    return [
        sub_name
        for sub_name, sub_data in HD_SUBCIRCUIT_INDEX.items()
        if gate in sub_data["gates"]
    ]


def find_groups_for_gate(gate: int) -> List[str]:
    """Return main circuit groups containing a gate."""
    return [
        group_name
        for group_name, group_data in HD_CIRCUIT_GROUPS.items()
        if gate in group_data["gates"]
    ]


if __name__ == "__main__":
    print("Main circuit groups:", list(HD_CIRCUIT_GROUPS))
    print("Total channels:", len(HD_ALL_CHANNELS))
    print("Total gates covered:", len(HD_ALL_GATES))
