"""Shared aspect display and comparison inclusion rules.

This module is the single source of truth for aspect rows/lines that should be
visible in chart-data ASPECTS output, chart-wheel drawings, and similarity
aspect comparisons. Raw chart calculation may still keep mathematically valid
aspects; callers use these helpers whenever they need the user-visible aspect
set.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from typing import Any

ASPECT_DISPLAY_ANGLE_BODIES: frozenset[str] = frozenset({"AS", "MC", "DS", "IC"})

STRUCTURAL_ASPECT_TAUTOLOGIES: Mapping[str, frozenset[frozenset[str]]] = {
    "opposition": frozenset(
        {
            frozenset({"AS", "DS"}),
            frozenset({"MC", "IC"}),
            frozenset({"Rahu", "Ketu"}),
        }
    ),
    "square": frozenset(
        {
            frozenset({"AS", "MC"}),
            frozenset({"AS", "IC"}),
            frozenset({"MC", "DS"}),
            frozenset({"DS", "IC"}),
        }
    ),
}


def normalize_aspect_body_for_display(body: Any) -> str:
    """Normalize body labels for display/comparison filtering."""

    return str(body or "").strip()


def normalize_aspect_type_for_display(aspect_type: Any) -> str:
    """Normalize aspect names to the snake-case keys used across the app."""

    return str(aspect_type or "").strip().replace(" ", "_").lower()


def aspect_endpoint_names(aspect: Mapping[str, Any]) -> tuple[str, str] | None:
    """Return normalized endpoint body names, or None when incomplete."""

    p1 = normalize_aspect_body_for_display(aspect.get("p1"))
    p2 = normalize_aspect_body_for_display(aspect.get("p2"))
    if not p1 or not p2:
        return None
    return p1, p2


def is_structural_aspect_tautology(aspect: Mapping[str, Any]) -> bool:
    """Return True for deterministic axis/node aspects hidden app-wide."""

    endpoints = aspect_endpoint_names(aspect)
    if endpoints is None:
        return False
    aspect_type = normalize_aspect_type_for_display(aspect.get("type"))
    if not aspect_type:
        return False
    return frozenset(endpoints) in STRUCTURAL_ASPECT_TAUTOLOGIES.get(aspect_type, frozenset())


def aspect_is_displayable(
    aspect: Mapping[str, Any],
    *,
    use_houses: bool,
    known_positions: Collection[str] | Mapping[str, Any] | None = None,
) -> bool:
    """Return whether an aspect belongs in user-visible aspect surfaces.

    Rules applied here:
    * endpoints and aspect type must be present;
    * when a positions collection is supplied, both endpoints must be present;
    * deterministic structural tautologies are hidden;
    * when house/time-specific data is unavailable, all angle-body aspects are
      hidden because AS/MC/DS/IC are not meaningful display endpoints.
    """

    endpoints = aspect_endpoint_names(aspect)
    if endpoints is None:
        return False
    p1, p2 = endpoints
    if not normalize_aspect_type_for_display(aspect.get("type")):
        return False
    if known_positions is not None and (p1 not in known_positions or p2 not in known_positions):
        return False
    if is_structural_aspect_tautology(aspect):
        return False
    if not use_houses and (p1 in ASPECT_DISPLAY_ANGLE_BODIES or p2 in ASPECT_DISPLAY_ANGLE_BODIES):
        return False
    return True


def display_aspect_key(
    aspect: Mapping[str, Any],
    *,
    use_houses: bool,
    known_positions: Collection[str] | Mapping[str, Any] | None = None,
) -> tuple[tuple[str, str], str] | None:
    """Return a canonical user-visible aspect key, or None when hidden."""

    if not aspect_is_displayable(aspect, use_houses=use_houses, known_positions=known_positions):
        return None
    p1, p2 = aspect_endpoint_names(aspect) or ("", "")
    left, right = sorted((p1, p2))
    return (left, right), normalize_aspect_type_for_display(aspect.get("type"))


def iter_displayable_aspects(
    aspects: Iterable[Mapping[str, Any]],
    *,
    use_houses: bool,
    known_positions: Collection[str] | Mapping[str, Any] | None = None,
) -> Iterable[Mapping[str, Any]]:
    """Yield aspects that pass the shared user-visible aspect rules."""

    for aspect in aspects:
        if aspect_is_displayable(aspect, use_houses=use_houses, known_positions=known_positions):
            yield aspect
