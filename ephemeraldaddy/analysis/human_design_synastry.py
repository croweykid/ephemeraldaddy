"""UID-first Human Design synastry ranking.

The ranking deliberately measures only mechanics created by superimposing two
sets of gates.  It is not a general relationship compatibility model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ephemeraldaddy.core.human_design_system import (
    defined_centers_from_active_gates,
    defined_channels_from_active_gates,
)


@dataclass(frozen=True, slots=True)
class HumanDesignSynastryCandidate:
    chart_uid: str
    name: str
    alias: str | None
    gates: frozenset[int]
    uses_houses: bool = True


@dataclass(frozen=True, slots=True)
class HumanDesignSynastryMatch:
    chart_uid: str
    name: str
    alias: str | None
    completed_channels: int
    defined_centers: int
    uses_houses: bool = True


def normalize_gates(values: Iterable[object] | None) -> frozenset[int]:
    """Return valid Human Design gate numbers, ignoring malformed cache data."""
    gates: set[int] = set()
    for value in values or ():
        try:
            gate = int(value)
        except (TypeError, ValueError):
            continue
        if 1 <= gate <= 64:
            gates.add(gate)
    return frozenset(gates)


def rank_human_design_synastry(
    chart_uid: str,
    gates: Iterable[object] | None,
    candidates: Iterable[HumanDesignSynastryCandidate],
    *,
    limit: int = 10,
) -> list[HumanDesignSynastryMatch]:
    """Rank candidates by new union channels, then union-defined centers.

    Channel completion is the primary criterion.  Center definition is a
    lexicographic bonus rather than a separate database pass, so it cannot let
    a candidate with fewer completed channels outrank one with more.
    """
    normalized_uid = str(chart_uid or "").strip().upper()
    source_gates = normalize_gates(gates)
    source_channels = {
        tuple(sorted((gate_a, gate_b)))
        for gate_a, gate_b, _center_a, _center_b in defined_channels_from_active_gates(source_gates)
    }
    matches: list[HumanDesignSynastryMatch] = []
    for candidate in candidates:
        candidate_uid = str(candidate.chart_uid or "").strip().upper()
        if not candidate_uid or candidate_uid == normalized_uid:
            continue
        candidate_gates = normalize_gates(candidate.gates)
        candidate_channels = {
            tuple(sorted((gate_a, gate_b)))
            for gate_a, gate_b, _center_a, _center_b in defined_channels_from_active_gates(candidate_gates)
        }
        combined_gates = source_gates | candidate_gates
        combined_channels = defined_channels_from_active_gates(combined_gates)
        completed_channels = sum(
            tuple(sorted((gate_a, gate_b))) not in source_channels | candidate_channels
            for gate_a, gate_b, _center_a, _center_b in combined_channels
        )
        matches.append(
            HumanDesignSynastryMatch(
                chart_uid=candidate_uid,
                name=str(candidate.name or "Unnamed chart").strip() or "Unnamed chart",
                alias=str(candidate.alias).strip() if candidate.alias else None,
                completed_channels=completed_channels,
                defined_centers=len(defined_centers_from_active_gates(combined_gates)),
                uses_houses=bool(candidate.uses_houses),
            )
        )
    matches.sort(
        key=lambda match: (
            -match.completed_channels,
            -match.defined_centers,
            match.name.casefold(),
            match.chart_uid,
        )
    )
    return matches[: max(0, int(limit))]
