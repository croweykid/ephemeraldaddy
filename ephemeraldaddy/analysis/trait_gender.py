"""Optional recorded-gender evidence overlay on shared astrological scores."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from ephemeraldaddy.analysis.traits import calculate_trait_scores, trait_possible_score
from ephemeraldaddy.core.chart import chart_uses_houses

def _trait_profile(trait: Mapping[str, Any]) -> Mapping[str, Any]:
    profile = trait.get("profile")
    return profile if isinstance(profile, Mapping) else trait

def _normalize_gender(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()

def _matching_key(mapping: Mapping[Any, Any], normalized_label: str) -> Any | None:
    for key in mapping:
        if _normalize_gender(key) == normalized_label:
            return key
    return None

def gender_evidence_points(profile: Mapping[str, Any], gender: Any) -> float | None:
    """Return significant sample-minus-database gender prevalence in percentage points."""
    normalized_gender = _normalize_gender(gender)
    if not normalized_gender:
        return None
    distribution = profile.get("genderDistribution")
    if not isinstance(distribution, Mapping) or not bool(distribution.get("statisticallySignificant", False)):
        return None
    percentages = distribution.get("percentages")
    database_percentages = distribution.get("databasePercentages")
    if not isinstance(percentages, Mapping) or not isinstance(database_percentages, Mapping):
        return None
    sample_key = _matching_key(percentages, normalized_gender)
    database_key = _matching_key(database_percentages, normalized_gender)
    if sample_key is None or database_key is None:
        return None

    category_significant = False
    significance = distribution.get("significance")
    if isinstance(significance, Mapping):
        significance_key = _matching_key(significance, normalized_gender)
        detail = significance.get(significance_key) if significance_key is not None else None
        if isinstance(detail, Mapping):
            category_significant = bool(detail.get("significant", False))
    if not category_significant:
        categories = distribution.get("significantCategories")
        if isinstance(categories, (list, tuple, set, frozenset)):
            category_significant = any(
                _normalize_gender(value) == normalized_gender for value in categories
            )
    if not category_significant:
        return None
    try:
        return float(percentages[sample_key]) - float(database_percentages[database_key])
    except (TypeError, ValueError):
        return None

def likelihood_from_evidence(
    raw_score: float,
    possible_score: float,
    *,
    gender_delta: float | None = None,
) -> float:
    """Normalize signed evidence, adding gender to numerator and denominator when present."""
    raw = float(raw_score)
    possible = max(float(possible_score), 1.0)
    if gender_delta is not None:
        delta = float(gender_delta)
        raw += delta
        possible += abs(delta)
    normalized = max(-1.0, min(1.0, raw / possible))
    return round(50.0 + (normalized * 50.0), 1)

def calculate_trait_likelihoods_with_gender(
    chart: Any,
    traits: list[dict[str, Any]],
) -> dict[str, float]:
    """Score Traits with statistically significant recorded-gender evidence."""
    active_traits = [trait for trait in traits if not bool(trait.get("archived", False))]
    if chart is None or not active_traits:
        return {}
    raw_scores = calculate_trait_scores(chart, active_traits)
    include_houses = chart_uses_houses(chart)
    chart_gender = getattr(chart, "gender", None)
    likelihoods: dict[str, float] = {}
    for trait in active_traits:
        name = str(trait.get("name", "") or "").strip()
        if not name:
            continue
        profile = _trait_profile(trait)
        likelihoods[name] = likelihood_from_evidence(
            float(raw_scores.get(name, 0.0)),
            trait_possible_score(profile, include_houses=include_houses),
            gender_delta=gender_evidence_points(profile, chart_gender),
        )
    return likelihoods

def _gender_traits_for_chart(chart: Any, traits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gender = getattr(chart, "gender", None)
    if not _normalize_gender(gender):
        return []
    return [
        trait
        for trait in traits
        if gender_evidence_points(_trait_profile(trait), gender) is not None
    ]
