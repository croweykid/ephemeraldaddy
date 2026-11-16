"""Canonical, GUI-free identities for Trait calculation inputs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


DISPLAY_FIELDS = frozenset({
    "name", "color", "description", "motivation", "quotes", "archived",
    "samples", "sample_uids", "antisample_uids", "chartUIDs", "exported_at",
    "chart_accuracy_rankings", "perceived_accuracy", "astro_analysis",
})


def analytical_mapping_signature(value: Mapping[str, Any] | None, *, strip_uids: bool = False) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    excluded = DISPLAY_FIELDS | ({"uid", "trait_uid"} if strip_uids else set())
    return {str(key): item for key, item in value.items() if str(key) not in excluded}


def stable_hash(value: Any) -> str:
    try:
        text = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    except TypeError:
        text = repr(value)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def trait_definition_signature(trait: Mapping[str, Any]) -> str:
    return stable_hash(analytical_mapping_signature(trait.get("profile", {}), strip_uids=True))


def chart_prediction_signature(chart: Any) -> str:
    from ephemeraldaddy.core.chart_data_fields import astro_data_recalculation_token
    from ephemeraldaddy.core.chart import chart_uses_houses

    return stable_hash(astro_data_recalculation_token(chart, chart_uses_houses_value=bool(chart_uses_houses(chart))))
