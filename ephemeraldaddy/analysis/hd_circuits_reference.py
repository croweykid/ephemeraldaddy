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


from ephemeraldaddy.analysis.human_design_reference import HD_CIRCUIT_GROUPS


HD_ALL_CHANNELS: List[dict] = [{'group': 'Individual', 'subcircuit': 'Integration', 'channel': '10-20', 'name': 'Awakening', 'gates': (10, 20)}, {'group': 'Individual', 'subcircuit': 'Integration', 'channel': '20-34', 'name': 'Charisma', 'gates': (20, 34)}, {'group': 'Individual', 'subcircuit': 'Integration', 'channel': '10-57', 'name': 'Perfected Form', 'gates': (10, 57)}, {'group': 'Individual', 'subcircuit': 'Integration', 'channel': '34-57', 'name': 'Power', 'gates': (34, 57)}, {'group': 'Individual', 'subcircuit': 'Knowing', 'channel': '1-8', 'name': 'Inspiration', 'gates': (1, 8)}, {'group': 'Individual', 'subcircuit': 'Knowing', 'channel': '2-14', 'name': 'The Beat', 'gates': (2, 14)}, {'group': 'Individual', 'subcircuit': 'Knowing', 'channel': '3-60', 'name': 'Mutation', 'gates': (3, 60)}, {'group': 'Individual', 'subcircuit': 'Knowing', 'channel': '28-38', 'name': 'Struggle', 'gates': (28, 38)}, {'group': 'Individual', 'subcircuit': 'Knowing', 'channel': '20-57', 'name': 'Brainwave', 'gates': (20, 57)}, {'group': 'Individual', 'subcircuit': 'Knowing', 'channel': '39-55', 'name': 'Emoting', 'gates': (39, 55)}, {'group': 'Individual', 'subcircuit': 'Knowing', 'channel': '12-22', 'name': 'Openness', 'gates': (12, 22)}, {'group': 'Individual', 'subcircuit': 'Knowing', 'channel': '43-23', 'name': 'Structuring', 'gates': (43, 23)}, {'group': 'Individual', 'subcircuit': 'Knowing', 'channel': '61-24', 'name': 'Awareness', 'gates': (61, 24)}, {'group': 'Individual', 'subcircuit': 'Centering', 'channel': '25-51', 'name': 'Initiation', 'gates': (25, 51)}, {'group': 'Individual', 'subcircuit': 'Centering', 'channel': '10-34', 'name': 'Exploration', 'gates': (10, 34)}, {'group': 'Collective', 'subcircuit': 'Logic', 'channel': '63-4', 'name': 'Logic', 'gates': (63, 4)}, {'group': 'Collective', 'subcircuit': 'Logic', 'channel': '17-62', 'name': 'Acceptance', 'gates': (17, 62)}, {'group': 'Collective', 'subcircuit': 'Logic', 'channel': '16-48', 'name': 'Talent', 'gates': (16, 48)}, {'group': 'Collective', 'subcircuit': 'Logic', 'channel': '18-58', 'name': 'Judgment', 'gates': (18, 58)}, {'group': 'Collective', 'subcircuit': 'Logic', 'channel': '52-9', 'name': 'Concentration', 'gates': (52, 9)}, {'group': 'Collective', 'subcircuit': 'Logic', 'channel': '15-5', 'name': 'Rhythm', 'gates': (15, 5)}, {'group': 'Collective', 'subcircuit': 'Logic', 'channel': '31-7', 'name': 'The Alpha', 'gates': (31, 7)}, {'group': 'Collective', 'subcircuit': 'Abstract', 'channel': '64-47', 'name': 'Abstraction', 'gates': (64, 47)}, {'group': 'Collective', 'subcircuit': 'Abstract', 'channel': '11-56', 'name': 'Curiosity', 'gates': (11, 56)}, {'group': 'Collective', 'subcircuit': 'Abstract', 'channel': '35-36', 'name': 'Transitoriness', 'gates': (35, 36)}, {'group': 'Collective', 'subcircuit': 'Abstract', 'channel': '41-30', 'name': 'Recognition', 'gates': (41, 30)}, {'group': 'Collective', 'subcircuit': 'Abstract', 'channel': '42-53', 'name': 'Maturation', 'gates': (42, 53)}, {'group': 'Collective', 'subcircuit': 'Abstract', 'channel': '46-29', 'name': 'Discovery', 'gates': (46, 29)}, {'group': 'Collective', 'subcircuit': 'Abstract', 'channel': '33-13', 'name': 'The Prodigal', 'gates': (33, 13)}, {'group': 'Tribal', 'subcircuit': 'Ego', 'channel': '32-54', 'name': 'Transformation', 'gates': (32, 54)}, {'group': 'Tribal', 'subcircuit': 'Ego', 'channel': '44-26', 'name': 'Surrender', 'gates': (44, 26)}, {'group': 'Tribal', 'subcircuit': 'Ego', 'channel': '19-49', 'name': 'Synthesis', 'gates': (19, 49)}, {'group': 'Tribal', 'subcircuit': 'Ego', 'channel': '40-37', 'name': 'Community', 'gates': (40, 37)}, {'group': 'Tribal', 'subcircuit': 'Ego', 'channel': '21-45', 'name': 'Money', 'gates': (21, 45)}, {'group': 'Tribal', 'subcircuit': 'Defense', 'channel': '50-27', 'name': 'Preservation', 'gates': (50, 27)}, {'group': 'Tribal', 'subcircuit': 'Defense', 'channel': '59-6', 'name': 'Mating', 'gates': (59, 6)}]

HD_ALL_GATES: Tuple[int, ...] = tuple(sorted({1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64}))

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
