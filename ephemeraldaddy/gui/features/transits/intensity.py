"""Chart-relative intensity scoring for Personal Transit aspects.

This module deliberately keeps four concepts separate:

* aspect type strength (from ``ASPECT_SCORE_WEIGHTS``),
* orb/exactness,
* natal prominence of the bodies in the selected chart, and
* temporary reinforcement from other simultaneous transit contacts.

Natal dominance already contains the chart's natal aspect network, so this
module does not add natal connectivity again.  Reinforcement here is based
only on the currently active Personal Transit contacts.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import statistics
from typing import Iterable, Mapping

from ephemeraldaddy.core.interpretations import ASPECT_SCORE_WEIGHTS


SOURCE_DOMINANCE_EXPONENT = 0.35
TARGET_DOMINANCE_EXPONENT = 0.65
SOURCE_REINFORCEMENT_CAP = 0.75
TARGET_REINFORCEMENT_CAP = 0.35
REINFORCEMENT_SCALE = 2.5
DOMINANCE_FLOOR = 0.65
DOMINANCE_CEILING = 1.55
ORB_STRENGTH_FLOOR = 0.25
DISPLAY_SCALE = 100.0

_MAX_ASPECT_WEIGHT = float(max(ASPECT_SCORE_WEIGHTS.values(), default=1.0))
_ASPECT_WEIGHTS = {
    "".join(ch for ch in str(name).lower() if ch.isalnum()): float(weight)
    for name, weight in ASPECT_SCORE_WEIGHTS.items()
}
_ASPECT_ALIASES = {
    "sesquiquadrate": "sesquisquare",
}


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def normalize_aspect_name(value: object) -> str:
    """Return a stable aspect key across display spelling variants."""
    key = "".join(ch for ch in str(value).lower() if ch.isalnum())
    return _ASPECT_ALIASES.get(key, key)


def aspect_identity(source: object, aspect: object, target: object) -> tuple[str, str, str]:
    return str(source), normalize_aspect_name(aspect), str(target)


def normalize_natal_dominance(weights: Mapping[object, object] | None) -> dict[str, float]:
    """Convert raw chart dominance scores into bounded relative multipliers.

    Raw dominance scores are useful ordinal/relative scores, but they should
    not transfer linearly into transit intensity.  The square-root transform
    preserves the selected chart's hierarchy while compressing extremes.
    Bodies absent from the dominance map (notably angles) are handled by the
    scorer as neutral 1.0 multipliers.
    """
    usable: dict[str, float] = {}
    for body, raw_value in dict(weights or {}).items():
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if value > 0.0 and math.isfinite(value):
            usable[str(body)] = value
    if not usable:
        return {}

    median = float(statistics.median(usable.values()))
    if median <= 0.0 or not math.isfinite(median):
        return {}
    return {
        body: _clamp(math.sqrt(value / median), DOMINANCE_FLOOR, DOMINANCE_CEILING)
        for body, value in usable.items()
    }


@dataclass(frozen=True)
class TransitAspectInput:
    source: str
    aspect: str
    target: str
    orb: float
    orb_cap: float


@dataclass(frozen=True)
class AspectIntensity:
    source: str
    aspect: str
    target: str
    base_aspect_strength: float
    orb_strength: float
    source_dominance: float
    target_dominance: float
    source_activation_load: float
    target_activation_load: float
    source_reinforcement: float
    target_reinforcement: float
    base_potential: float
    intensity: float

    @property
    def display_score(self) -> float:
        return self.intensity * DISPLAY_SCALE


@dataclass(frozen=True)
class BodyActivation:
    body: str
    baseline_dominance: float
    source_load: float
    target_load: float
    source_count: int
    target_count: int
    source_reinforcement: float
    target_reinforcement: float
    current_activation: float

    @property
    def contact_count(self) -> int:
        return self.source_count + self.target_count


@dataclass(frozen=True)
class TransitIntensityResult:
    aspect_scores: Mapping[tuple[str, str, str], AspectIntensity]
    body_activations: Mapping[str, BodyActivation]

    def score_for(self, source: object, aspect: object, target: object) -> AspectIntensity | None:
        return self.aspect_scores.get(aspect_identity(source, aspect, target))


def _aspect_strength(aspect: object) -> float:
    weight = _ASPECT_WEIGHTS.get(normalize_aspect_name(aspect), 0.0)
    return _clamp(weight / _MAX_ASPECT_WEIGHT, 0.0, 1.0)


def _orb_strength(orb: float, orb_cap: float) -> float:
    cap = max(float(orb_cap), 0.01)
    exactness = _clamp(1.0 - (max(0.0, float(orb)) / cap), 0.0, 1.0)
    return ORB_STRENGTH_FLOOR + ((1.0 - ORB_STRENGTH_FLOOR) * exactness)


def _reinforcement(load: float, cap: float) -> float:
    return cap * (1.0 - math.exp(-max(0.0, load) / REINFORCEMENT_SCALE))


def calculate_transit_intensities(
    aspects: Iterable[TransitAspectInput],
    natal_dominance_weights: Mapping[object, object] | None,
) -> TransitIntensityResult:
    """Score current Personal Transit contacts and body activation.

    Duplicate physical aspects are collapsed by ``(source, aspect, target)``.
    If the same contact arrives through two display modes, the version with
    the stronger normalized orb contribution is retained so it cannot inflate
    convergence merely by being listed twice.
    """
    dominance = normalize_natal_dominance(natal_dominance_weights)

    prepared: dict[tuple[str, str, str], dict[str, float | str]] = {}
    for entry in aspects:
        source = str(entry.source)
        target = str(entry.target)
        aspect = normalize_aspect_name(entry.aspect)
        base = _aspect_strength(aspect)
        if base <= 0.0:
            continue
        orb_strength = _orb_strength(entry.orb, entry.orb_cap)
        source_dominance = float(dominance.get(source, 1.0))
        target_dominance = float(dominance.get(target, 1.0))
        source_contribution = base * orb_strength * target_dominance
        target_contribution = base * orb_strength * source_dominance
        identity = (source, aspect, target)
        candidate = {
            "source": source,
            "aspect": aspect,
            "target": target,
            "base": base,
            "orb_strength": orb_strength,
            "source_dominance": source_dominance,
            "target_dominance": target_dominance,
            "source_contribution": source_contribution,
            "target_contribution": target_contribution,
        }
        existing = prepared.get(identity)
        if existing is None or (base * orb_strength) > (
            float(existing["base"]) * float(existing["orb_strength"])
        ):
            prepared[identity] = candidate

    source_loads: dict[str, float] = {}
    target_loads: dict[str, float] = {}
    source_counts: dict[str, int] = {}
    target_counts: dict[str, int] = {}
    source_max_contribution: dict[str, float] = {}
    target_max_contribution: dict[str, float] = {}

    for item in prepared.values():
        source = str(item["source"])
        target = str(item["target"])
        source_contribution = float(item["source_contribution"])
        target_contribution = float(item["target_contribution"])
        source_loads[source] = source_loads.get(source, 0.0) + source_contribution
        target_loads[target] = target_loads.get(target, 0.0) + target_contribution
        source_counts[source] = source_counts.get(source, 0) + 1
        target_counts[target] = target_counts.get(target, 0) + 1
        source_max_contribution[source] = max(
            source_max_contribution.get(source, 0.0), source_contribution
        )
        target_max_contribution[target] = max(
            target_max_contribution.get(target, 0.0), target_contribution
        )

    aspect_scores: dict[tuple[str, str, str], AspectIntensity] = {}
    for identity, item in prepared.items():
        source = str(item["source"])
        target = str(item["target"])
        base = float(item["base"])
        orb_strength = float(item["orb_strength"])
        source_dominance = float(item["source_dominance"])
        target_dominance = float(item["target_dominance"])
        source_companion_load = max(
            0.0,
            source_loads.get(source, 0.0) - float(item["source_contribution"]),
        )
        target_companion_load = max(
            0.0,
            target_loads.get(target, 0.0) - float(item["target_contribution"]),
        )
        source_bonus = _reinforcement(source_companion_load, SOURCE_REINFORCEMENT_CAP)
        target_bonus = _reinforcement(target_companion_load, TARGET_REINFORCEMENT_CAP)
        base_potential = (
            base
            * orb_strength
            * (source_dominance ** SOURCE_DOMINANCE_EXPONENT)
            * (target_dominance ** TARGET_DOMINANCE_EXPONENT)
        )
        intensity = base_potential * (1.0 + source_bonus + target_bonus)
        aspect_scores[identity] = AspectIntensity(
            source=source,
            aspect=str(item["aspect"]),
            target=target,
            base_aspect_strength=base,
            orb_strength=orb_strength,
            source_dominance=source_dominance,
            target_dominance=target_dominance,
            source_activation_load=source_companion_load,
            target_activation_load=target_companion_load,
            source_reinforcement=source_bonus,
            target_reinforcement=target_bonus,
            base_potential=base_potential,
            intensity=intensity,
        )

    bodies = set(dominance) | set(source_loads) | set(target_loads)
    body_activations: dict[str, BodyActivation] = {}
    for body in bodies:
        baseline = float(dominance.get(body, 1.0))
        source_load = source_loads.get(body, 0.0)
        target_load = target_loads.get(body, 0.0)

        # A lone aspect is not a cluster.  Remove the strongest contact before
        # computing the body-level convergence bonus so activation describes
        # reinforcement from additional simultaneous contacts, not self-boost.
        source_cluster_load = max(
            0.0, source_load - source_max_contribution.get(body, 0.0)
        )
        target_cluster_load = max(
            0.0, target_load - target_max_contribution.get(body, 0.0)
        )
        source_bonus = _reinforcement(source_cluster_load, SOURCE_REINFORCEMENT_CAP)
        target_bonus = _reinforcement(target_cluster_load, TARGET_REINFORCEMENT_CAP)
        source_effective = baseline * (1.0 + source_bonus)
        target_effective = baseline * (1.0 + target_bonus)
        body_activations[body] = BodyActivation(
            body=body,
            baseline_dominance=baseline,
            source_load=source_load,
            target_load=target_load,
            source_count=source_counts.get(body, 0),
            target_count=target_counts.get(body, 0),
            source_reinforcement=source_bonus,
            target_reinforcement=target_bonus,
            current_activation=max(baseline, source_effective, target_effective),
        )

    return TransitIntensityResult(
        aspect_scores=aspect_scores,
        body_activations=body_activations,
    )


def format_body_activation_summary(
    activations: Mapping[str, BodyActivation],
    *,
    limit: int = 10,
) -> str:
    """Format the selected-date convergence block used by Theme View."""
    active = [
        item
        for item in activations.values()
        if item.contact_count > 0
        and item.current_activation > (item.baseline_dominance + 1e-9)
    ]
    active.sort(
        key=lambda item: (
            item.current_activation,
            item.contact_count,
            item.source_load + item.target_load,
        ),
        reverse=True,
    )
    if not active:
        return (
            "CURRENT ASPECT ACTIVATION\n"
            "(Selected date; no multi-aspect convergence is reinforcing a body.)"
        )

    lines = [
        "CURRENT ASPECT ACTIVATION",
        "(Selected date; natal prominence → convergence-adjusted prominence)",
        "",
    ]
    for item in active[: max(1, int(limit))]:
        roles: list[str] = []
        if item.source_count:
            roles.append(f"{item.source_count} outgoing")
        if item.target_count:
            roles.append(f"{item.target_count} incoming")
        lines.append(
            f"- {item.body:<12} {item.baseline_dominance:>4.2f}× → "
            f"{item.current_activation:>4.2f}×   ({', '.join(roles)})"
        )
    return "\n".join(lines)
