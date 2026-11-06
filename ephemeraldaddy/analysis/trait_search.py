"""Cached Trait membership for an explicit UID cohort, without scoring."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable
from ephemeraldaddy.analysis.trait_prediction_index import global_trait_prediction_index


@dataclass(frozen=True)
class TraitMembership:
    above: frozenset[str]
    below: frozenset[str]
    available: frozenset[str]


def membership_for_uids(chart_uids: Iterable[str], traits: list[dict[str, Any]]) -> dict[str, TraitMembership]:
    results = global_trait_prediction_index().results_for_uids(chart_uids, traits)
    return {uid: TraitMembership(
        frozenset(name.casefold() for name, delta in result.deviations.items() if delta >= 5),
        frozenset(name.casefold() for name, delta in result.deviations.items() if delta <= -5),
        frozenset(name.casefold() for name in result.deviations),
    ) for uid, result in results.items()}


def matches_membership(membership: TraitMembership | None, *, required_present: set[str], excluded_present: set[str], required_absent: set[str], excluded_absent: set[str]) -> bool:
    selected = {name.casefold() for group in (required_present, excluded_present, required_absent, excluded_absent) for name in group}
    # Missing scores or norms are unknown, never negative evidence.
    if membership is None or not selected <= membership.available:
        return False
    return (all(name.casefold() in membership.above for name in required_present)
            and all(name.casefold() not in membership.above for name in excluded_present)
            and all(name.casefold() in membership.below for name in required_absent)
            and all(name.casefold() not in membership.below for name in excluded_absent))
