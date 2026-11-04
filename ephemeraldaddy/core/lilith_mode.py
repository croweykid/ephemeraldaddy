"""Which calculated lunar apogee is eligible for user-facing astrology scoring.

All three canonical coordinates remain stored. This module selects the one
used for dominance, prevalence and presentation without modifying chart data.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ephemeraldaddy.core.body_identity import (
    CANONICAL_LILITH_BODIES,
    MEAN_LILITH,
    NATURAL_LILITH,
    OSCULATING_LILITH,
    canonicalize_semantic_body_name,
)

LILITH_MODES = (OSCULATING_LILITH, MEAN_LILITH, NATURAL_LILITH)
DEFAULT_LILITH_MODE = OSCULATING_LILITH


def normalize_lilith_mode(value: object) -> str:
    """Use Osculating on missing/invalid preferences (including old installs)."""
    mode = str(value or "").strip()
    return mode if mode in LILITH_MODES else DEFAULT_LILITH_MODE


def lilith_is_eligible(body: object, mode: str) -> bool:
    """A selected Lilith counts once; all unrelated celestial bodies survive."""
    canonical = canonicalize_semantic_body_name(body)
    return canonical not in CANONICAL_LILITH_BODIES or canonical == normalize_lilith_mode(mode)


def visible_lilith_positions(positions: Mapping[str, Any], mode: str) -> dict[str, Any]:
    return {
        body: value for body, value in positions.items()
        if lilith_is_eligible(body, mode)
    }


def filter_lilith_aspects(aspects: Any, mode: str) -> list[dict]:
    """Keep aspects involving the selected Lilith; reject other Lilith endpoints."""
    return [
        aspect for aspect in (aspects or [])
        if isinstance(aspect, dict)
        and lilith_is_eligible(aspect.get("p1", ""), mode)
        and lilith_is_eligible(aspect.get("p2", ""), mode)
    ]


def filtered_chart_export_payload(payload: Any, mode: str) -> Any:
    """Remove inactive Lilith coordinates and aspect rows without losing null data."""
    excluded = object()

    def visit(value: Any) -> Any:
        if isinstance(value, dict):
            if ("p1" in value or "p2" in value) and not (
                lilith_is_eligible(value.get("p1", ""), mode)
                and lilith_is_eligible(value.get("p2", ""), mode)
            ):
                return excluded
            result = {}
            for key, item in value.items():
                if not lilith_is_eligible(key, mode):
                    continue
                filtered = visit(item)
                if filtered is not excluded:
                    result[key] = filtered
            return result
        if isinstance(value, (list, tuple)):
            result = []
            for item in value:
                filtered = visit(item)
                if filtered is not excluded:
                    result.append(filtered)
            return result
        return value

    return visit(payload)
