"""Pure classification of cached Trait scores against static reference values."""
from __future__ import annotations
from typing import Any
TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD = 5.0

def metadata_from_vectors(
    *,
    likelihoods: dict[str, float],
    database_averages: dict[str, float],
    stale_chart_vector: bool = False,
    stale_trait_definition: bool = False,
    stale_db_baseline: bool = False,
    updated_at: str = "",
    stale_trait_names: set[str] | None = None,
    full_staleness_reasons: list[str] | None = None,
) -> dict[str, Any]:
    deviations = {
        name: float(pct) - float(database_averages[name])
        for name, pct in likelihoods.items()
        if name in database_averages
    }
    above = {name for name, deviation in deviations.items() if deviation >= TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD}
    below = {name for name, deviation in deviations.items() if deviation <= -TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD}
    stale = bool(stale_chart_vector or stale_trait_definition or stale_db_baseline or stale_trait_names)
    stale_trait_names = set(stale_trait_names or set())
    full_staleness_reasons = list(full_staleness_reasons or [])
    if stale_chart_vector and "astro_data" not in full_staleness_reasons:
        full_staleness_reasons.append("astro_data")
    if stale_db_baseline and "database_norms" not in full_staleness_reasons:
        full_staleness_reasons.append("database_norms")
    if stale_trait_definition and not stale_trait_names and "all_traits" not in full_staleness_reasons:
        full_staleness_reasons.append("all_traits")
    staleness_kind = "fresh"
    if stale:
        staleness_kind = "full" if full_staleness_reasons else "partial"
    metadata: dict[str, Any] = {
        "above": above,
        "below": below,
        "deviations": deviations,
        "likelihoods": likelihoods,
        "database_averages": database_averages,
        "stale_chart_vector": bool(stale_chart_vector),
        "stale_trait_definition": bool(stale_trait_definition),
        "stale_db_baseline": bool(stale_db_baseline),
        "staleness_kind": staleness_kind,
        "stale_trait_names": sorted(stale_trait_names),
        "full_staleness_reasons": full_staleness_reasons,
    }
    if stale:
        metadata["stale"] = True
    if updated_at:
        metadata["updated_at"] = updated_at
    return metadata
