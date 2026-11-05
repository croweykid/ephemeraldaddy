"""Chart-local presentation metadata for accepted Trait calculations."""
from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from ephemeraldaddy.analysis.trait_signatures import (
    chart_prediction_signature, stable_hash, trait_definition_signature,
)
from ephemeraldaddy.core import db
from ephemeraldaddy.core.prediction_norms import prediction_norms_reference, trait_norm_signature


def trait_metadata_cache_key(
    chart: Any, traits: list[dict[str, Any]], *, chart_signature: str | None = None,
) -> str:
    """Identify one chart's model and static-reference inputs, including drafts."""
    reference = prediction_norms_reference()
    return stable_hash({
        "version": 1,
        "database": str(db.DB_PATH),
        "chart_uid": str(getattr(chart, "chart_uid", "") or "").strip().upper(),
        "astro_data": chart_signature or chart_prediction_signature(chart),
        "traits": [
            (trait.get("uid") or trait.get("trait_uid"), trait.get("name"),
             trait_definition_signature(trait), trait_norm_signature(trait, reference))
            for trait in traits
        ],
    })


def cached_trait_prediction_metadata(
    chart: Any, traits: list[dict[str, Any]], *, chart_signature: str | None = None,
) -> dict[str, Any] | None:
    """Read a matching view without scoring, explanations, or SQLite lookups."""
    cached = getattr(chart, "_trait_prediction_metadata_cache", None)
    if not isinstance(cached, dict) or cached.get("signature") != trait_metadata_cache_key(
        chart, traits, chart_signature=chart_signature,
    ):
        return None
    metadata = cached.get("metadata")
    return copy.deepcopy(metadata) if isinstance(metadata, dict) else None


def retain_trait_prediction_metadata(
    chart: Any, traits: list[dict[str, Any]], metadata: Mapping[str, Any], *,
    expected_signature: str,
) -> bool:
    """Keep an accepted base result on its live chart, independently of saving."""
    if (metadata.get("stale") or metadata.get("gender_criterion_traits")
            or trait_metadata_cache_key(chart, traits) != expected_signature):
        return False
    chart._trait_prediction_metadata_cache = {
        "signature": expected_signature, "metadata": copy.deepcopy(dict(metadata)),
    }
    return True
