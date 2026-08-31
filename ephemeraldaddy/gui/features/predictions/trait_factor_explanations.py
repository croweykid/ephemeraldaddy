"""Build Chart Info evidence for custom Trait predictions.

This module owns presentation-oriented factor grouping for the Predictions
workflow.  It intentionally does not change weighted predictor scoring: it
uses the scorer's existing normalizers, eligibility rules, and matched-factor
result to explain which configured positive opportunities did not contribute
to the current chart.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ephemeraldaddy.analysis.weighted_chart_predictor import (
    aspect_spec_uses_houses,
    coerce_weighted_entries,
    matched_weighted_criteria,
    parse_position_spec,
    position_spec_uses_houses,
    weighted_bazi_sign_entries,
    weighted_channel_entries,
    weighted_gate_entries,
    weighted_hd_authority_entries,
    weighted_hd_center_entries,
    weighted_hd_profile_entries,
    weighted_hd_type_entries,
    weighted_house_entries,
    weighted_position_entries,
    weighted_string_entries,
)
from ephemeraldaddy.core.chart import chart_uses_houses


@dataclass(frozen=True)
class TraitFactorEvidence:
    """Ordered Chart Info evidence for one trait/profile pair."""

    supporting: tuple[str, ...]
    counter_factors: tuple[str, ...]
    missing: tuple[str, ...]


@dataclass(frozen=True)
class _PositiveCandidate:
    category: str
    label: str
    dominance: bool = False
    position_bucket: tuple[str, str] | None = None
    position_subject: str = ""
    position_destination: str = ""


def _weighted_text_entries(values: Any) -> tuple[str, ...]:
    """Match weighted_chart_predictor's aspect-entry normalization and order."""
    return tuple(
        token
        for raw_value in coerce_weighted_entries(values)
        if (token := str(raw_value).strip())
    )


def _position_candidate(spec: str) -> _PositiveCandidate:
    parsed = parse_position_spec(spec)
    if parsed is None:
        return _PositiveCandidate("positions", spec)
    category, container, subject = parsed
    if category == "body_in_sign" and isinstance(container, str):
        return _PositiveCandidate(
            "positions",
            spec,
            position_bucket=(category, str(subject)),
            position_subject=str(subject),
            position_destination=container,
        )
    if category == "body_in_house" and isinstance(container, int):
        return _PositiveCandidate(
            "positions",
            spec,
            position_bucket=(category, str(subject)),
            position_subject=str(subject),
            position_destination=f"House {container}",
        )
    if category == "sign_in_house" and isinstance(container, int):
        return _PositiveCandidate(
            "positions",
            spec,
            position_bucket=(category, str(container)),
            position_subject=f"House {container}",
            position_destination=str(subject),
        )
    return _PositiveCandidate("positions", spec)


def _eligible_positive_candidates(chart: Any, factors: Mapping[str, Any]) -> list[_PositiveCandidate]:
    """Return positive criteria in the same category order as Supporting evidence."""
    use_houses = bool(chart_uses_houses(chart))
    candidates: list[_PositiveCandidate] = []

    def add_strings(category: str, values: Any, *, dominance: bool = False) -> None:
        candidates.extend(
            _PositiveCandidate(category, label, dominance=dominance)
            for label in weighted_string_entries(values)
        )

    add_strings("signs", factors.get("signs", set()), dominance=True)
    add_strings("bodies", factors.get("bodies", set()), dominance=True)
    add_strings("nakshatras", factors.get("nakshatras", set()), dominance=True)

    if use_houses:
        candidates.extend(
            _PositiveCandidate("houses", f"House {house}", dominance=True)
            for house in weighted_house_entries(factors.get("houses", set()))
        )

    candidates.extend(
        _PositiveCandidate("gates", f"Gate {gate}")
        for gate in weighted_gate_entries(factors.get("gates", set()))
    )
    candidates.extend(
        _PositiveCandidate("channels", f"Channel {left}–{right}")
        for left, right in weighted_channel_entries(factors.get("channels", set()))
    )
    candidates.extend(
        _PositiveCandidate("hdtypes", str(value).replace("_", " ").title())
        for value in weighted_hd_type_entries(factors.get("hdtypes", set()))
    )
    candidates.extend(
        _PositiveCandidate("centers", f"{value} Center")
        for value in weighted_hd_center_entries(factors.get("centers", set()))
    )
    candidates.extend(
        _PositiveCandidate("profiles", f"Profile {value}")
        for value in weighted_hd_profile_entries(factors.get("profiles", set()))
    )
    candidates.extend(
        _PositiveCandidate("authorities", f"{value} Authority")
        for value in weighted_hd_authority_entries(factors.get("authorities", set()))
    )
    candidates.extend(
        _PositiveCandidate("bazisigns", f"BaZi {value}")
        for value in weighted_bazi_sign_entries(factors.get("bazisigns", set()))
    )

    for spec in weighted_position_entries(factors.get("positions", set())):
        if use_houses or not position_spec_uses_houses(spec):
            candidates.append(_position_candidate(spec))

    for spec in _weighted_text_entries(factors.get("aspects", set())):
        if use_houses or not aspect_spec_uses_houses(spec):
            candidates.append(_PositiveCandidate("aspects", spec))

    return candidates


def _join_values(values: list[str], *, conjunction: str) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} {conjunction} {values[1]}"
    return f"{', '.join(values[:-1])} {conjunction} {values[-1]}"


def _format_missing_gates(gate_labels: list[str]) -> str:
    gates = [label.removeprefix("Gate ") for label in gate_labels]
    if len(gates) == 1:
        return f"Missing Gate {gates[0]}"
    return f"Missing Gates {_join_values(gates, conjunction='&')}"


def _format_missing_position_group(candidates: list[_PositiveCandidate]) -> str:
    first = candidates[0]
    destinations = [candidate.position_destination for candidate in candidates if candidate.position_destination]
    if not first.position_subject or not destinations:
        return first.label
    return f"{first.position_subject} not in {_join_values(destinations, conjunction='or')}"


def build_trait_factor_evidence(
    chart: Any,
    factors: Mapping[str, Any] | None,
    *,
    matches: Mapping[str, list[str]] | None = None,
) -> TraitFactorEvidence:
    """Return Supporting, Counter-factors, and compact Missing explanations.

    ``Missing`` is the complement of *eligible positive* criteria only.  Anti
    criteria remain Counter-factors and are never presented as missing
    positives.  Mutually exclusive position alternatives share the same
    category/body bucket used by the scorer: once one alternative matches, the
    other alternatives in that bucket are suppressed rather than described as
    failures.
    """
    profile = factors if isinstance(factors, Mapping) else {}
    resolved_matches = matches if isinstance(matches, Mapping) else matched_weighted_criteria(chart, profile)
    supporting = tuple(str(value) for value in resolved_matches.get("positive", []) if str(value))
    counter_factors = tuple(str(value) for value in resolved_matches.get("negative", []) if str(value))
    matched_positive = set(supporting)
    candidates = _eligible_positive_candidates(chart, profile)

    position_groups: dict[tuple[str, str], list[_PositiveCandidate]] = {}
    matched_position_buckets: set[tuple[str, str]] = set()
    for candidate in candidates:
        if candidate.category != "positions" or candidate.position_bucket is None:
            continue
        position_groups.setdefault(candidate.position_bucket, []).append(candidate)
        if candidate.label in matched_positive:
            matched_position_buckets.add(candidate.position_bucket)

    unmatched_gates = [
        candidate.label
        for candidate in candidates
        if candidate.category == "gates" and candidate.label not in matched_positive
    ]
    emitted_gate_group = False
    emitted_position_groups: set[tuple[str, str]] = set()
    missing: list[str] = []

    for candidate in candidates:
        if candidate.label in matched_positive:
            continue
        if candidate.category == "gates":
            if not emitted_gate_group and unmatched_gates:
                missing.append(_format_missing_gates(unmatched_gates))
                emitted_gate_group = True
            continue
        if candidate.category == "positions" and candidate.position_bucket is not None:
            bucket = candidate.position_bucket
            if bucket in matched_position_buckets:
                continue
            if bucket in emitted_position_groups:
                continue
            group = [item for item in position_groups.get(bucket, []) if item.label not in matched_positive]
            if group:
                missing.append(_format_missing_position_group(group))
            emitted_position_groups.add(bucket)
            continue
        if candidate.dominance:
            missing.append(f"{candidate.label} not above baseline in chart")
        else:
            missing.append(candidate.label)

    return TraitFactorEvidence(
        supporting=supporting,
        counter_factors=counter_factors,
        missing=tuple(missing),
    )
