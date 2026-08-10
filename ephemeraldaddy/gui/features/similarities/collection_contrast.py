"""Pure aggregate-norm analysis for collection comparisons."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from ephemeraldaddy.core.aspect_display import ASPECT_DISPLAY_ANGLE_BODIES
from ephemeraldaddy.core.chart import chart_uses_houses

_SIGNS = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)


def _sign_for_longitude(longitude: object) -> str:
    return _SIGNS[int(float(longitude) % 360 // 30)]


@dataclass(frozen=True, slots=True, order=True)
class CollectionNorm:
    category: str
    label: str


@dataclass(frozen=True, slots=True)
class CollectionContrast:
    only_a: tuple[CollectionNorm, ...]
    overlap: tuple[CollectionNorm, ...]
    only_b: tuple[CollectionNorm, ...]


def _chart_norms(chart: object) -> set[CollectionNorm]:
    norms: set[CollectionNorm] = set()
    positions = getattr(chart, "positions", {}) or {}
    timed = chart_uses_houses(chart)
    uncertain_bodies = {
        str(body).strip().casefold()
        for body in (getattr(chart, "unknown_signs", ()) or ())
        if str(body).strip()
    }
    for body, longitude in positions.items():
        if (
            longitude is None
            or str(body).strip().casefold() in uncertain_bodies
            or (not timed and body in ASPECT_DISPLAY_ANGLE_BODIES)
        ):
            continue
        norms.add(
            CollectionNorm("Placements", f"{body} in {_sign_for_longitude(longitude)}")
        )
    for gate in getattr(chart, "human_design_gates", ()) or ():
        if gate_text := str(gate).strip():
            norms.add(CollectionNorm("Human Design Gates", f"Gate {gate_text}"))
    for channel in getattr(chart, "human_design_channels", ()) or ():
        if channel_text := str(channel).strip():
            norms.add(CollectionNorm("Human Design Channels", channel_text))
    if timed:
        houses = list(getattr(chart, "houses", ()) or ())
        for house_number, longitude in enumerate(houses[:12], 1):
            norms.add(
                CollectionNorm(
                    "House Signs",
                    f"House {house_number}: {_sign_for_longitude(longitude)}",
                )
            )
    return norms


def aggregate_collection_norms(
    charts: Iterable[object], *, minimum_occurrences: int = 2
) -> set[CollectionNorm]:
    """Find factual features recurring across usable charts.

    Similarities Analysis treats a feature as shared once it occurs in at
    least two selected charts.  Collection comparison intentionally uses the
    same rule instead of requiring a feature to appear in half of an entire
    collection: the latter silently becomes much stricter as collections grow
    and hides patterns that the existing analysis panel reports.
    """
    usable = [chart for chart in charts if getattr(chart, "positions", None)]
    if not usable:
        return set()
    required = min(len(usable), max(1, int(minimum_occurrences)))
    counts: Counter[CollectionNorm] = Counter()
    for chart in usable:
        counts.update(_chart_norms(chart))
    return {norm for norm, count in counts.items() if count >= required}


def collection_norm_counts(
    charts: Iterable[object],
) -> tuple[Counter[CollectionNorm], int]:
    """Return per-feature chart counts and the usable collection population."""
    usable = [chart for chart in charts if getattr(chart, "positions", None)]
    counts: Counter[CollectionNorm] = Counter()
    for chart in usable:
        counts.update(_chart_norms(chart))
    return counts, len(usable)


def contrast_collection_norms(
    charts_a: Iterable[object], charts_b: Iterable[object]
) -> CollectionContrast:
    norms_a = aggregate_collection_norms(charts_a)
    norms_b = aggregate_collection_norms(charts_b)
    return CollectionContrast(
        only_a=tuple(sorted(norms_a - norms_b)),
        overlap=tuple(sorted(norms_a & norms_b)),
        only_b=tuple(sorted(norms_b - norms_a)),
    )
