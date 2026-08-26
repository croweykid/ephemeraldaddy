"""Pure helpers for Database View sign-dominance ranking behavior."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any


def complete_sign_weight_map(
    weights: object,
    zodiac_names: Sequence[str],
) -> dict[str, float] | None:
    """Return a complete numeric sign-weight map, or ``None`` when unusable.

    An empty or partial persisted cache is not evidence of zero dominance.  The
    Rankings panel must recalculate those rows instead of silently treating a
    missing sign as ``0.0``.
    """
    if not isinstance(weights, Mapping):
        return None

    normalized: dict[str, float] = {}
    for sign in zodiac_names:
        if sign not in weights:
            return None
        try:
            value = float(weights[sign])
        except (TypeError, ValueError):
            return None
        if value != value or value in (float("inf"), float("-inf")):
            return None
        normalized[str(sign)] = value

    if not any(abs(value) > 0.0 for value in normalized.values()):
        return None
    return normalized


def resolve_complete_sign_weights(
    stored_weights: object,
    chart_weights: object,
    zodiac_names: Sequence[str],
    recalculate: Callable[[], object],
) -> tuple[dict[str, float] | None, bool]:
    """Resolve trustworthy weights, recalculating when both caches are unusable."""
    for candidate in (stored_weights, chart_weights):
        normalized = complete_sign_weight_map(candidate, zodiac_names)
        if normalized is not None:
            return normalized, False

    recalculated = complete_sign_weight_map(recalculate(), zodiac_names)
    return recalculated, True


def least_house_priority(*, least: bool, uses_houses: object) -> int:
    """Put known-house charts ahead of unknown-house fallbacks in least mode."""
    if not least:
        return 0
    return 0 if bool(uses_houses) else 1
