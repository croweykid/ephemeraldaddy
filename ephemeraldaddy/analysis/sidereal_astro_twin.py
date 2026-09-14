"""Coordinate-consistent Astro Twin experiments for Sidereal D1 and D9.

The production Astro Twin scorer is reused through a narrow chart-like adapter;
no alternate representation becomes a persisted person or receives another UID.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from copy import copy
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ephemeraldaddy.analysis.get_astro_twin import chart_similarity_score
from ephemeraldaddy.core.sidereal_service import (
    SiderealCalculationRequest,
    SiderealChartDataService,
)


class SiderealAstroTwinMode(str, Enum):
    D1_TO_D1 = "d1_to_d1"
    D9_TO_D9 = "d9_to_d9"
    D9_TO_D1 = "d9_to_d1"


@dataclass(frozen=True)
class SiderealAstroTwinCandidate:
    chart: object
    request: SiderealCalculationRequest


@dataclass(frozen=True)
class SiderealAstroTwinMatch:
    chart_uid: str
    chart_name: str
    score: float
    subject_division: str
    candidate_division: str
    ayanamsha: str = "lahiri"


def _context_chart(parent: object, context: object) -> object:
    adapted = copy(parent)
    adapted.chart_uid = str(getattr(context, "chart_uid"))
    adapted.positions = dict(getattr(context, "positions"))
    adapted.retrogrades = dict(getattr(context, "retrogrades", {}))
    house_cusps = getattr(context, "house_cusps", None)
    adapted.houses = list(house_cusps or ())
    adapted.housesPo = []
    adapted.aspects = [dict(aspect) for aspect in getattr(context, "aspects", ())]
    adapted.zodiac = "sidereal"
    adapted.division = str(getattr(context, "division"))
    adapted.ayanamsha = str(getattr(context, "ayanamsha"))
    # A parent Chart may carry persisted Tropical dominance/cache fields. They
    # are coordinate-derived and must never influence a Sidereal comparison.
    adapted.dominant_planet_weights = {}
    adapted.dominant_sign_weights = {}
    adapted.dominant_nakshatra_weights = {}
    adapted.dominant_element_weights = {}
    adapted._similarity_derived_cache = {}
    # Existing Astro Twin house gates consult chart_uses_houses(). D9 currently
    # has no validated house projection, so a chart-like adapter must make the
    # canonical source facts resolve FALSE instead of inventing another gate.
    if not bool(getattr(context, "uses_houses", house_cusps is not None)):
        adapted.birthtime_unknown = True
        adapted.retcon_time_used = False
        adapted.rectification_range_used = False
    return adapted


def _view_for_mode(
    service: SiderealChartDataService,
    candidate: SiderealAstroTwinCandidate,
    division: str,
) -> object:
    context = (
        service.get_or_calculate(candidate.request)
        if division == "D1"
        else service.get_varga(candidate.request, division)
    )
    return _context_chart(candidate.chart, context)


def rank_sidereal_astro_twins(
    subject: SiderealAstroTwinCandidate,
    candidates: Iterable[SiderealAstroTwinCandidate],
    *,
    service: SiderealChartDataService,
    mode: SiderealAstroTwinMode | str = SiderealAstroTwinMode.D1_TO_D1,
    top_k: int = 3,
    scorer: Callable[[Any, Any], tuple[float, ...]] = chart_similarity_score,
) -> list[SiderealAstroTwinMatch]:
    """Rank candidates in one explicitly Sidereal coordinate comparison."""

    resolved_mode = SiderealAstroTwinMode(mode)
    subject_division = "D1" if resolved_mode is SiderealAstroTwinMode.D1_TO_D1 else "D9"
    candidate_division = "D9" if resolved_mode is SiderealAstroTwinMode.D9_TO_D9 else "D1"
    subject_chart = _view_for_mode(service, subject, subject_division)
    subject_uid = str(getattr(subject_chart, "chart_uid", ""))
    matches: list[SiderealAstroTwinMatch] = []
    for candidate in candidates:
        if candidate.request.chart_uid.strip().upper() == subject_uid:
            continue
        candidate_chart = _view_for_mode(service, candidate, candidate_division)
        candidate_uid = str(getattr(candidate_chart, "chart_uid", ""))
        if not candidate_uid or candidate_uid == subject_uid:
            continue
        result = scorer(subject_chart, candidate_chart)
        score = float(result[0])
        matches.append(
            SiderealAstroTwinMatch(
                chart_uid=candidate_uid,
                chart_name=str(getattr(candidate_chart, "name", "") or "Unnamed"),
                score=score,
                subject_division=subject_division,
                candidate_division=candidate_division,
            )
        )
    matches.sort(key=lambda match: (-match.score, match.chart_uid))
    return matches[: max(1, int(top_k))]
