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

# Antipodal endpoints describe one axis. When both halves aspect the same third
# endpoint, the two rows are the same geometric event expressed from opposite
# ends of that axis. Keep only one user-visible representative.
_AXIS_ID_BY_BODY: Mapping[str, str] = {
    "AS": "AS-DS",
    "DS": "AS-DS",
    "MC": "MC-IC",
    "IC": "MC-IC",
    "Rahu": "Rahu-Ketu",
    "Ketu": "Rahu-Ketu",
}

_AXIS_DISPLAY_LABEL_BY_ID: Mapping[str, str] = {
    "AS-DS": "AS–DS axis",
    "MC-IC": "MC–IC axis",
    "Rahu-Ketu": "Rahu–Ketu axis",
}

# Aspect types related by a 180-degree endpoint flip. Harmonics whose
# complements are not represented by the app (for example quintile -> 108°)
# deliberately remain independent.
_AXIS_COMPLEMENT_FAMILY: Mapping[str, str] = {
    "conjunction": "conjunction-opposition",
    "opposition": "conjunction-opposition",
    "square": "square",
    "sextile": "sextile-trine",
    "trine": "sextile-trine",
    "semisextile": "semisextile-quincunx",
    "quincunx": "semisextile-quincunx",
    "semisquare": "semisquare-sesquiquadrate",
    "sesquiquadrate": "semisquare-sesquiquadrate",
}


def normalize_aspect_body_for_display(body: Any) -> str:
    """Normalize body labels for display/comparison filtering."""

    return str(body or "").strip()


def normalize_aspect_type_for_display(aspect_type: Any) -> str:
    """Normalize aspect names to the snake-case keys used across the app."""

    return str(aspect_type or "").strip().replace(" ", "_").lower()


def aspect_axis_display_label(body: Any) -> str | None:
    """Return the user-facing axis label for an antipodal endpoint, if any.

    This is presentation metadata only. Callers must keep the canonical raw
    endpoint (AS/DS, MC/IC, Rahu/Ketu) for geometry, scoring, lookup, and click
    metadata.
    """

    normalized = normalize_aspect_body_for_display(body)
    axis_id = _AXIS_ID_BY_BODY.get(normalized)
    if axis_id is None:
        return None
    return _AXIS_DISPLAY_LABEL_BY_ID[axis_id]


def aspect_endpoint_names(aspect: Mapping[str, Any]) -> tuple[str, str] | None:
    """Return normalized endpoint body names, or None when incomplete."""

    p1 = normalize_aspect_body_for_display(aspect.get("p1"))
    p2 = normalize_aspect_body_for_display(aspect.get("p2"))
    if not p1 or not p2:
        return None
    return p1, p2


def _axis_endpoint_key(body: str) -> tuple[str, str]:
    axis_id = _AXIS_ID_BY_BODY.get(body)
    if axis_id is not None:
        return "axis", axis_id
    return "body", body


def axis_aspect_redundancy_key(
    body1: Any,
    body2: Any,
    aspect_type: Any,
    *,
    directed: bool = False,
    layer1: Any = None,
    layer2: Any = None,
) -> tuple[Any, ...] | None:
    """Return a key shared by redundant complementary axis-aspect halves.

    ``directed=False`` is appropriate for natal/chart aspect mappings, whose
    endpoints are symmetric. Transit-to-natal hits use ``directed=True`` and
    preserve layer identity so a transiting axis aspect is never confused with
    a transiting planet aspect to a natal axis.
    """

    p1 = normalize_aspect_body_for_display(body1)
    p2 = normalize_aspect_body_for_display(body2)
    family = _AXIS_COMPLEMENT_FAMILY.get(normalize_aspect_type_for_display(aspect_type))
    if not p1 or not p2 or family is None:
        return None
    if p1 not in _AXIS_ID_BY_BODY and p2 not in _AXIS_ID_BY_BODY:
        return None

    endpoint1 = _axis_endpoint_key(p1)
    endpoint2 = _axis_endpoint_key(p2)
    if directed:
        return (
            endpoint1,
            endpoint2,
            family,
            str(layer1 or ""),
            str(layer2 or ""),
        )

    left, right = sorted((endpoint1, endpoint2))
    return left, right, family


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
    """Yield the canonical user-visible aspect set without redundant axis halves."""

    seen_axis_events: set[tuple[Any, ...]] = set()
    for aspect in aspects:
        if not aspect_is_displayable(aspect, use_houses=use_houses, known_positions=known_positions):
            continue
        endpoints = aspect_endpoint_names(aspect)
        if endpoints is not None:
            axis_key = axis_aspect_redundancy_key(
                endpoints[0],
                endpoints[1],
                aspect.get("type"),
            )
            if axis_key is not None:
                if axis_key in seen_axis_events:
                    continue
                seen_axis_events.add(axis_key)
        yield aspect
