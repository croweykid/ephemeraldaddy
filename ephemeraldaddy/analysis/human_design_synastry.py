"""UID-first Human Design synastry ranking.

The ranking deliberately measures only mechanics created by superimposing two
sets of gates.  It is not a general relationship compatibility model.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from statistics import median
from typing import Iterable

from ephemeraldaddy.analysis.get_astro_twin import normalize_astro_twin_gender_category
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
    gender: str | None = None
    astro_data_signature: str | None = None


@dataclass(frozen=True, slots=True)
class HumanDesignSynastryMatch:
    chart_uid: str
    name: str
    alias: str | None
    completed_channels: int
    defined_centers: int
    score: int
    population_median: float
    percentile: float
    uses_houses: bool = True


HD_SYNASTRY_GENDER_FILTERS = frozenset({"all", "male", "female"})
HD_SYNASTRY_GENDER_METHOD_SEX = "sex"
HD_SYNASTRY_GENDER_METHOD_IDENTITY = "gender"
# With 26 unique gates available to each chart, at most 28 channels can be
# completed *between* the charts (24 isolated pairs plus four integration
# channels).  A combined bodygraph can define all nine centers.
HD_ELECTROCHEMISTRY_MAX_CROSS_CHANNELS = 28
HD_ELECTROCHEMISTRY_MAX_DEFINED_CENTERS = 9
HD_ELECTROCHEMISTRY_MAX_SCORE = (
    HD_ELECTROCHEMISTRY_MAX_CROSS_CHANNELS + HD_ELECTROCHEMISTRY_MAX_DEFINED_CENTERS
)


def normalize_hd_synastry_gender_filter(value: object) -> str:
    """Return a supported candidate-gender filter, defaulting to all."""
    normalized = str(value or "").strip().casefold()
    return normalized if normalized in HD_SYNASTRY_GENDER_FILTERS else "all"


def filter_hd_synastry_candidates(
    candidates: Iterable[HumanDesignSynastryCandidate],
    gender_filter: object,
    gender_method: object = HD_SYNASTRY_GENDER_METHOD_SEX,
) -> list[HumanDesignSynastryCandidate]:
    """Filter candidates by either assigned-at-birth sex or gender identity."""
    candidate_list = list(candidates)
    normalized_filter = normalize_hd_synastry_gender_filter(gender_filter)
    if normalized_filter == "all":
        return candidate_list
    normalized_method = str(gender_method or "").strip().casefold()
    if normalized_method == HD_SYNASTRY_GENDER_METHOD_IDENTITY:
        accepted_categories = {
            "male": frozenset({"male", "afab-m"}),
            "female": frozenset({"female", "amab-f"}),
        }
    else:
        accepted_categories = {
            "male": frozenset({"male", "amab-f", "amab-nb"}),
            "female": frozenset({"female", "afab-m", "afab-nb"}),
        }
    return [
        candidate
        for candidate in candidate_list
        if normalize_astro_twin_gender_category(candidate.gender)
        in accepted_categories[normalized_filter]
    ]


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


def human_design_electrochemistry_score(
    gates_a: Iterable[object] | None,
    gates_b: Iterable[object] | None,
) -> tuple[int, int]:
    """Return cross-chart channel completions plus combined defined centers."""
    completed_channels, defined_centers = human_design_electrochemistry_components(gates_a, gates_b)
    return completed_channels + defined_centers, HD_ELECTROCHEMISTRY_MAX_SCORE


def human_design_electrochemistry_components(
    gates_a: Iterable[object] | None,
    gates_b: Iterable[object] | None,
) -> tuple[int, int]:
    """Return new cross-chart channels and centers defined by the union."""
    normalized_a = normalize_gates(gates_a)
    normalized_b = normalize_gates(gates_b)
    channels_a = {
        tuple(sorted((gate_a, gate_b)))
        for gate_a, gate_b, _center_a, _center_b in defined_channels_from_active_gates(normalized_a)
    }
    channels_b = {
        tuple(sorted((gate_a, gate_b)))
        for gate_a, gate_b, _center_a, _center_b in defined_channels_from_active_gates(normalized_b)
    }
    combined_channels = {
        tuple(sorted((gate_a, gate_b)))
        for gate_a, gate_b, _center_a, _center_b in defined_channels_from_active_gates(
            normalized_a | normalized_b
        )
    }
    return (
        len(combined_channels - channels_a - channels_b),
        len(defined_centers_from_active_gates(normalized_a | normalized_b)),
    )


def rank_human_design_synastry(
    chart_uid: str,
    gates: Iterable[object] | None,
    candidates: Iterable[HumanDesignSynastryCandidate],
    *,
    limit: int = 10,
) -> list[HumanDesignSynastryMatch]:
    """Rank candidates by summed electrochemistry score for this population."""
    normalized_uid = str(chart_uid or "").strip().upper()
    source_gates = normalize_gates(gates)
    matches: list[HumanDesignSynastryMatch] = []
    for candidate in candidates:
        candidate_uid = str(candidate.chart_uid or "").strip().upper()
        if not candidate_uid or candidate_uid == normalized_uid:
            continue
        candidate_gates = normalize_gates(candidate.gates)
        completed_channels, defined_centers = human_design_electrochemistry_components(
            source_gates, candidate_gates
        )
        matches.append(
            HumanDesignSynastryMatch(
                chart_uid=candidate_uid,
                name=str(candidate.name or "Unnamed chart").strip() or "Unnamed chart",
                alias=str(candidate.alias).strip() if candidate.alias else None,
                completed_channels=completed_channels,
                defined_centers=defined_centers,
                score=completed_channels + defined_centers,
                population_median=0.0,
                percentile=0.0,
                uses_houses=bool(candidate.uses_houses),
            )
        )
    if matches:
        scores = [match.score for match in matches]
        population_median = float(median(scores))
        population_size = len(scores)
        score_counts = Counter(scores)
        cumulative_count = 0
        percentile_by_score: dict[int, float] = {}
        for score in sorted(score_counts):
            cumulative_count += score_counts[score]
            percentile_by_score[score] = 100.0 * cumulative_count / population_size
        matches = [
            HumanDesignSynastryMatch(
                chart_uid=match.chart_uid,
                name=match.name,
                alias=match.alias,
                completed_channels=match.completed_channels,
                defined_centers=match.defined_centers,
                score=match.score,
                population_median=population_median,
                percentile=percentile_by_score[match.score],
                uses_houses=match.uses_houses,
            )
            for match in matches
        ]
    matches.sort(
        key=lambda match: (
            -match.score,
            -match.completed_channels,
            match.name.casefold(),
            match.chart_uid,
        )
    )
    return matches[: max(0, int(limit))]
