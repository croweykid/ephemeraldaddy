"""Pure aggregate-norm analysis for collection comparisons."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from ephemeraldaddy.core.aspect_display import ASPECT_DISPLAY_ANGLE_BODIES
from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.gui.features.charts.provenance import chart_is_non_aggregable

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

_TRAIT_EXPORT_SECTION_BY_CATEGORY = {
    "Placements": "Signs in positions in common",
    "House Signs": "Signs in houses in common",
    "Human Design Gates": "Gates in common",
    "Human Design Channels": "Channels in common",
}


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


def collection_norm_subgroup_label(norm: CollectionNorm) -> str | None:
    """Return the nested display group for aspect and position norm labels."""
    if "Aspect" in norm.category:
        return norm.label.split(" ", 1)[0]
    if norm.category == "Houses in positions in common":
        _body, separator, house = norm.label.partition(": ")
        return house if separator else None
    if norm.category in {"Placements", "Signs in positions in common"}:
        _body, separator, position = norm.label.partition(" in ")
        return position if separator else None
    return None


def collection_trait_export_sections(
    norms: tuple[CollectionNorm, ...],
    counts: Counter[CollectionNorm],
    known_totals: Counter[CollectionNorm],
    database_counts: Counter[CollectionNorm],
    database_known_totals: Counter[CollectionNorm],
    *,
    cohort_size: int | None = None,
) -> tuple[tuple[str, tuple[tuple[object, ...], ...]], ...]:
    """Adapt one comparison column to the Similarities trait exporter shape."""
    matches_by_section: dict[str, list[tuple[object, ...]]] = {}
    for norm in norms:
        section = _TRAIT_EXPORT_SECTION_BY_CATEGORY.get(norm.category, norm.category)
        if section is None:
            continue
        label = norm.label
        if section == "Signs in houses in common" and " in H" in label:
            sign, house_number = label.rsplit(" in H", 1)
            if house_number.isdigit():
                label = f"House {int(house_number)}: {sign}"
        matches_by_section.setdefault(section, []).append(
            (
                label,
                counts[norm],
                known_totals[norm],
                database_counts[norm],
                database_known_totals[norm],
                (),
                "",
                max(0, int(cohort_size)) if cohort_size is not None else 0,
            )
        )
    return tuple(
        (section, tuple(matches)) for section, matches in matches_by_section.items()
    )


def filter_aggregable_charts(charts: Iterable[object]) -> tuple[list[object], int]:
    """Return aggregation candidates and the placeholder/hypothetical omission count."""
    candidates = list(charts)
    omitted = sum(
        chart is not None and chart_is_non_aggregable(chart) for chart in candidates
    )
    return [
        chart
        for chart in candidates
        if chart is not None and not chart_is_non_aggregable(chart)
    ], omitted


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
) -> tuple[Counter[CollectionNorm], Counter[CollectionNorm], int]:
    """Return factor counts, factor-specific known totals, and usable population."""
    usable = [chart for chart in charts if getattr(chart, "positions", None)]
    counts: Counter[CollectionNorm] = Counter()
    for chart in usable:
        counts.update(_chart_norms(chart))
    known_totals: Counter[CollectionNorm] = Counter()
    for norm in counts:
        known_totals[norm] = sum(_chart_knows_norm(chart, norm) for chart in usable)
    return counts, known_totals, len(usable)


def _chart_knows_norm(chart: object, norm: CollectionNorm) -> bool:
    """Return whether ``chart`` has usable data for a norm's underlying factor."""
    if norm.category == "Placements":
        body, separator, _sign = norm.label.partition(" in ")
        if not separator:
            return False
        positions = getattr(chart, "positions", {}) or {}
        uncertain_bodies = {
            str(value).strip().casefold()
            for value in (getattr(chart, "unknown_signs", ()) or ())
        }
        return (
            body in positions
            and positions[body] is not None
            and body.casefold() not in uncertain_bodies
            and (body not in ASPECT_DISPLAY_ANGLE_BODIES or chart_uses_houses(chart))
        )
    if norm.category == "House Signs":
        house_token = norm.label.partition(":")[0].removeprefix("House ").strip()
        if not house_token.isdigit() or not chart_uses_houses(chart):
            return False
        houses = list(getattr(chart, "houses", ()) or ())
        house_index = int(house_token) - 1
        return 0 <= house_index < len(houses) and houses[house_index] is not None
    attribute = {
        "Human Design Gates": "human_design_gates",
        "Human Design Channels": "human_design_channels",
    }.get(norm.category)
    return attribute is not None and getattr(chart, attribute, None) is not None


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
