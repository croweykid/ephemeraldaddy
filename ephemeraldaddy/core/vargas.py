"""Rule-driven, in-memory Jyotish divisional-chart projections."""

from __future__ import annotations

from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import Any, Callable, Mapping

from ephemeraldaddy.core.aspects import find_aspects
from ephemeraldaddy.core.sidereal import LAHIRI, SiderealChartData


VARGA_RULESET_VERSION = 1
D1_ANGLE_BODIES = frozenset({"AS", "MC", "DS", "IC"})
D9_PROJECTED_ANGLE_BODIES = frozenset({"AS"})
D9_EXCLUDED_DERIVED_POINTS = frozenset({"Part of Fortune"})


@dataclass(frozen=True)
class VargaRule:
    division: int
    code: str
    name: str
    tradition: str
    project_sign: Callable[[int, int], int]


@dataclass(frozen=True)
class VargaChartView:
    chart_uid: str
    zodiac: str
    ayanamsha: str
    division: str
    positions: Mapping[str, float]
    retrogrades: Mapping[str, bool]
    house_cusps: None
    aspects: tuple[Mapping[str, Any], ...]
    source_recalculation_token: str
    ruleset_version: int = VARGA_RULESET_VERSION

    @property
    def uses_houses(self) -> bool:
        """D# house geometry is unavailable until separately validated."""

        return False


def _navamsha_sign(source_sign: int, segment: int) -> int:
    # Parashara: movable signs begin from themselves, fixed from the ninth,
    # and dual from the fifth; subsequent navamshas proceed zodiacally.
    modality = source_sign % 3
    start = source_sign if modality == 0 else (source_sign + (8 if modality == 1 else 4)) % 12
    return (start + segment) % 12


VARGA_RULES = MappingProxyType({
    "D9": VargaRule(
        9,
        "D9",
        "Navamsha",
        "Parashara modality-based Navamsha",
        _navamsha_sign,
    ),
})


def project_longitude(longitude: float, division: str = "D9") -> float:
    """Project one sidereal D1 longitude using the named explicit rule."""

    if not math.isfinite(longitude):
        raise ValueError("longitude must be finite")
    try:
        rule = VARGA_RULES[division.strip().upper()]
    except KeyError as exc:
        raise ValueError(f"Unsupported varga {division!r}") from exc
    normalized = longitude % 360.0
    source_sign = int(normalized // 30.0)
    within_sign = normalized - source_sign * 30.0
    segment_size = 30.0 / rule.division
    segment = min(rule.division - 1, int(within_sign / segment_size))
    fraction = (within_sign - segment * segment_size) / segment_size
    return (rule.project_sign(source_sign, segment) * 30.0 + fraction * 30.0) % 360.0


def _projectable_d9_position(name: str) -> bool:
    """Return whether a D1 point has an intentionally defined D9 projection."""

    if name in D9_EXCLUDED_DERIVED_POINTS:
        return False
    if name in D1_ANGLE_BODIES:
        # Navamsha Lagna is intentional. MC/IC/DS are not silently promoted to
        # canonical D9 points; DS can later be derived from D9 Lagna if desired.
        return name in D9_PROJECTED_ANGLE_BODIES
    return True


def project_varga(source: SiderealChartData, division: str = "D9") -> VargaChartView:
    """Lazily derive a read-only projection from canonical Sidereal D1 data."""

    code = division.strip().upper()
    if source.ayanamsha != LAHIRI:
        raise ValueError(f"Unsupported source ayanamsha {source.ayanamsha!r}")
    if code not in VARGA_RULES:
        raise ValueError(f"Unsupported varga {division!r}")

    if code == "D9":
        source_positions = {
            name: value
            for name, value in source.positions.items()
            if _projectable_d9_position(name)
        }
    else:
        source_positions = dict(source.positions)

    positions = {
        name: project_longitude(value, code)
        for name, value in source_positions.items()
    }
    return VargaChartView(
        chart_uid=source.chart_uid,
        zodiac="sidereal",
        ayanamsha=source.ayanamsha,
        division=code,
        positions=MappingProxyType(positions),
        retrogrades=source.retrogrades,
        house_cusps=None,
        aspects=tuple(MappingProxyType(dict(value)) for value in find_aspects(positions)),
        source_recalculation_token=source.source_recalculation_token,
    )
