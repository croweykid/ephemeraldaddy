"""Database-independent helpers for generating static prediction norm sections.

The caller owns chart loading, placeholder exclusion, persistence, and source
selection. This module only turns a supplied reference population into compact,
versioned norm rows.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from ephemeraldaddy.analysis.prediction_norms_catalog import build_trait_norm_row
from ephemeraldaddy.analysis.traits import trait_possible_score, trait_uid_for_profile
from ephemeraldaddy.analysis.weighted_chart_predictor import calculate_weighted_criteria_scores
from ephemeraldaddy.core.chart import chart_uses_houses


def _trait_identity(trait: Mapping[str, Any]) -> tuple[str, str, str]:
    name = str(trait.get("name", "") or "").strip()
    profile = trait.get("profile", {})
    if not isinstance(profile, Mapping):
        profile = {}
    uid = str(trait.get("uid", "") or trait.get("trait_uid", "") or "").strip()
    if not uid:
        try:
            uid = str(trait_uid_for_profile(name, profile) or "").strip()
        except Exception:
            uid = ""
    key = f"uid:{uid}" if uid else f"name:{name.casefold()}"
    return key, uid, name


def trait_likelihood_for_norm_mode(
    chart: Any,
    trait: Mapping[str, Any],
    *,
    include_houses: bool,
) -> float:
    """Score one Trait with an explicit house policy for norm generation.

    Runtime Trait scoring normally derives house availability from the chart.
    Norm generation also needs to rescore house-capable charts with all
    house-dependent evidence disabled, so it uses the weighted predictor's
    injectable ``uses_houses`` policy rather than mutating or cloning charts.
    """
    name = str(trait.get("name", "") or "").strip()
    profile = trait.get("profile", {})
    if not name or not isinstance(profile, Mapping):
        raise ValueError("Trait norm scoring requires a named mapping profile.")

    raw_scores = calculate_weighted_criteria_scores(
        chart,
        predictors={name: profile},
        uses_houses=lambda _chart: bool(include_houses),
    )
    possible = max(
        float(trait_possible_score(profile, include_houses=bool(include_houses))),
        1.0,
    )
    normalized = max(-1.0, min(1.0, float(raw_scores.get(name, 0.0)) / possible))
    return round(50.0 + (normalized * 50.0), 1)


def trait_population_scores(
    charts: Iterable[Any],
    trait: Mapping[str, Any],
) -> tuple[list[float], list[float]]:
    """Return ``(with_houses, without_houses)`` reference score vectors.

    ``with_houses`` contains only charts whose house data is usable and scores
    them with house-dependent evidence enabled.

    ``without_houses`` contains the entire supplied reference population but
    rescored with house-dependent evidence disabled. This keeps the population
    constant when calibrating the no-house scoring mode instead of conflating
    missing birth times with a different demographic sample.
    """
    with_houses: list[float] = []
    without_houses: list[float] = []
    for chart in charts:
        without_houses.append(
            trait_likelihood_for_norm_mode(chart, trait, include_houses=False)
        )
        try:
            houses_available = bool(chart_uses_houses(chart))
        except Exception:
            houses_available = False
        if houses_available:
            with_houses.append(
                trait_likelihood_for_norm_mode(chart, trait, include_houses=True)
            )
    return with_houses, without_houses


def build_trait_norm_row_from_charts(
    trait: Mapping[str, Any],
    charts: Sequence[Any],
    *,
    source: str,
    profile_hash: str,
    model_kind: str = "",
) -> dict[str, Any]:
    """Generate one v2 Trait norm row from a supplied static population."""
    key, uid, name = _trait_identity(trait)
    if not name:
        raise ValueError("Trait norm generation requires a trait name.")
    with_houses, without_houses = trait_population_scores(charts, trait)
    return build_trait_norm_row(
        key=key,
        uid=uid,
        name=name,
        profile_hash=str(profile_hash),
        source=str(source),
        with_houses_scores=with_houses,
        without_houses_scores=without_houses,
        model_kind=str(model_kind),
        sample_sizes={
            "reference_population": len(charts),
            "with_houses": len(with_houses),
            "without_houses": len(without_houses),
        },
    )
