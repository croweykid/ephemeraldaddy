"""Score semantic theme prominence for one chart and database populations.

Theme prominence is deliberately separate from interpretation.  The reference
file decides which chart factors belong to each semantic subtheme; this module
only measures how strongly those configured factors are activated in a chart.

Scoring rules
-------------
* Every configured factor activation is normalized to 0..1.
* Items are weighted by ``theme_reference.theme_item_weight``.
* Items are averaged inside their own factor category first.
* Scorable categories are then averaged equally.  This prevents a category
  with a long list (Human Design gates, for example) from overwhelming a short
  but equally intentional category such as elements or houses.
* A macrotheme/family score is the arithmetic mean of its scorable subthemes.
* Public scores are percentages in the 0..100 range.  DB comparisons are
  percentage-point differences between the chart and the selected snapshot.

The functions here are pure with respect to persistence: they never scan or
write the database unless the caller explicitly supplies a chart population.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from ephemeraldaddy.analysis import weighted_chart_predictor as _weighted
from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.core.theme_reference import (
    THEMES,
    THEME_FAMILIES,
    WEIGHTED_THEME_PROPERTIES,
    theme_item_weight,
    themes_in_family,
)


THEME_DEVIATION_ASSIGNMENT_THRESHOLD = 5.0

_ELEMENT_SIGNS: dict[str, tuple[str, ...]] = {
    "Fire": ("Aries", "Leo", "Sagittarius"),
    "Earth": ("Taurus", "Virgo", "Capricorn"),
    "Air": ("Gemini", "Libra", "Aquarius"),
    "Water": ("Cancer", "Scorpio", "Pisces"),
}
_MODE_SIGNS: dict[str, tuple[str, ...]] = {
    "Cardinal": ("Aries", "Cancer", "Libra", "Capricorn"),
    "Fixed": ("Taurus", "Leo", "Scorpio", "Aquarius"),
    "Mutable": ("Gemini", "Virgo", "Sagittarius", "Pisces"),
}


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def theme_definition_signature() -> str:
    """Hash only analytical Theme fields used by prominence scoring."""
    payload = {
        "families": {
            key: {"subthemes": sorted(themes_in_family(key))}
            for key in sorted(THEME_FAMILIES)
        },
        "themes": {
            key: {
                "family": str(theme.get("family", "")),
                "default_weight": float(theme.get("default_weight", 1.0)),
                "weight_overrides": theme.get("weight_overrides", {}) or {},
                **{
                    property_name: list(theme.get(property_name, []) or [])
                    for property_name in WEIGHTED_THEME_PROPERTIES
                },
            }
            for key, theme in sorted(THEMES.items())
        },
    }
    return _stable_hash(payload)


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _normalized_dominance(values: Mapping[Any, Any] | None) -> dict[Any, float]:
    """Normalize a dominance map to 0..1 using the app's range convention."""
    cleaned = {
        key: number
        for key, value in (values or {}).items()
        if (number := _finite_float(value)) is not None
    }
    if not cleaned:
        return {}
    return {
        key: max(0.0, min(1.0, float(value)))
        for key, value in _weighted.normalize_weight_map_by_range(cleaned).items()
    }


def _normalized_sparse_counts(values: Mapping[Any, Any] | None) -> dict[Any, float]:
    """Normalize sparse non-negative counts by their maximum observed count.

    BaZi pillar counts only contain signs that are actually present.  Range
    normalization is inappropriate for that representation because four
    distinct pillars produce a zero range (all present signs have count 1),
    incorrectly erasing every valid activation.
    """
    cleaned = {
        key: max(0.0, number)
        for key, value in (values or {}).items()
        if (number := _finite_float(value)) is not None
    }
    if not cleaned:
        return {}
    maximum = max(cleaned.values(), default=0.0)
    if maximum <= 0.0:
        return {key: 0.0 for key in cleaned}
    return {
        key: max(0.0, min(1.0, value / maximum))
        for key, value in cleaned.items()
    }


def _grouped_sign_dominance(
    raw_sign_weights: Mapping[str, Any] | None,
    groups: Mapping[str, Sequence[str]],
) -> dict[str, float]:
    cleaned = {
        str(sign): number
        for sign, value in (raw_sign_weights or {}).items()
        if (number := _finite_float(value)) is not None
    }
    if not cleaned:
        return {}
    totals = {
        group: sum(float(cleaned.get(sign, 0.0)) for sign in signs)
        for group, signs in groups.items()
    }
    return _normalized_dominance(totals)


def _casefold_lookup(mapping: Mapping[Any, float], item: Any) -> float:
    if item in mapping:
        return float(mapping[item])
    token = str(item).strip().casefold()
    for key, value in mapping.items():
        if str(key).strip().casefold() == token:
            return float(value)
    return 0.0


def _normalized_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _human_design_activations(chart: Any) -> dict[str, Any]:
    """Return HD activations needed by the Theme reference, or empty data."""
    try:
        from ephemeraldaddy.analysis.human_design import build_human_design_result

        result = build_human_design_result(chart)
    except Exception:
        return {
            "gates": set(),
            "channels": set(),
            "centers": set(),
            "profile": "",
            "authority": "",
            "cross": "",
            "available": False,
        }

    channels = {
        tuple(sorted((int(gate_a), int(gate_b))))
        for gate_a, gate_b, _center_a, _center_b in result.defined_channels
    }
    return {
        "gates": {int(gate) for gate in result.active_gates},
        "channels": channels,
        "centers": {str(center).strip().casefold() for center in result.defined_centers},
        "profile": _normalized_text(result.profile).replace(" ", ""),
        "authority": _normalized_text(result.authority),
        "cross": str(result.incarnation_cross or "").strip(),
        "available": True,
    }


def _theme_reference_uses_human_design() -> bool:
    hd_properties = {"gates", "channels", "crosses", "centers", "profiles", "authorities"}
    return any(
        theme.get(property_name)
        for theme in THEMES.values()
        for property_name in hd_properties
    )


def _theme_reference_uses_bazi() -> bool:
    return any(theme.get("bazisigns") for theme in THEMES.values())


def _activation_context(chart: Any) -> dict[str, Any]:
    raw_sign_weights = (
        getattr(chart, "dominant_sign_weights", None)
        or _weighted.calculate_dominant_sign_weights(chart)
    )
    raw_body_weights = (
        getattr(chart, "dominant_planet_weights", None)
        or _weighted.calculate_dominant_planet_weights(chart)
    )
    use_houses = bool(chart_uses_houses(chart))
    raw_house_weights = _weighted.calculate_dominant_house_weights(chart) if use_houses else {}
    raw_nakshatra_weights = (
        getattr(chart, "dominant_nakshatra_weights", None)
        or _weighted.calculate_dominant_nakshatra_weights(chart)
    )

    # Human Design requires a usable birth time.  Unknown-time charts carry a
    # placeholder datetime for other calculations; feeding that arbitrary time
    # into HD would fabricate gates, channels, centers, profile, authority, and
    # incarnation-cross evidence.  Until we add an all-day stability resolver,
    # omit HD from Theme scoring whenever the chart cannot use timed houses.
    hd = (
        _human_design_activations(chart)
        if use_houses and _theme_reference_uses_human_design()
        else {
            "gates": set(),
            "channels": set(),
            "centers": set(),
            "profile": "",
            "authority": "",
            "cross": "",
            "available": False,
        }
    )
    raw_bazi = _weighted.active_bazi_sign_weights(chart) if _theme_reference_uses_bazi() else {}

    return {
        "signs": _normalized_dominance(raw_sign_weights),
        "bodies": _normalized_dominance(raw_body_weights),
        "houses": _normalized_dominance(raw_house_weights) if use_houses else {},
        "houses_available": use_houses,
        "elements": _grouped_sign_dominance(raw_sign_weights, _ELEMENT_SIGNS),
        "modes": _grouped_sign_dominance(raw_sign_weights, _MODE_SIGNS),
        "nakshatras": _normalized_dominance(raw_nakshatra_weights),
        "bazisigns": _normalized_sparse_counts(raw_bazi),
        "bazi_available": bool(raw_bazi),
        "hd": hd,
    }


def _channel_key(value: Any) -> tuple[int, int] | None:
    return _weighted.normalize_channel_value(value)


def _canonical_cross_name(value: Any) -> str:
    """Reduce generated Human Design cross display text to its named cross."""
    text = _normalized_text(value)
    if not text:
        return ""

    # Generated display values look like:
    # ``Right Angle Cross of the Sphinx 4 (gates 1/2 • 7/13)``.
    # Gate decorations and the variant number are display metadata, not part of
    # the canonical cross name stored by the Theme reference.
    text = re.split(r"\bgates\b", text, maxsplit=1)[0].strip()
    text = re.sub(
        r"^(?:(?:right|left)\s+angle|juxtaposition)\s+cross\s+of\s+",
        "",
        text,
    )
    text = re.sub(r"^cross\s+of\s+", "", text)
    text = re.sub(r"\s+\d+\s*$", "", text).strip()
    return text


def _cross_matches(active_cross: str, configured_cross: Any) -> bool:
    configured = _canonical_cross_name(configured_cross)
    active = _canonical_cross_name(active_cross)
    if not configured or not active:
        return False
    return (
        active == configured
        or active.endswith(f" {configured}")
        or configured.endswith(f" {active}")
    )


def _activation_for_item(
    property_name: str,
    item: Any,
    context: Mapping[str, Any],
) -> float | None:
    if property_name == "houses" and not bool(context.get("houses_available")):
        return None
    if property_name == "bazisigns" and not bool(context.get("bazi_available")):
        return None

    if property_name in {"signs", "bodies", "houses", "elements", "modes", "nakshatras", "bazisigns"}:
        values = context.get(property_name, {})
        if not isinstance(values, Mapping):
            return None
        if property_name == "houses":
            try:
                house_num = int(item)
            except (TypeError, ValueError):
                return 0.0
            return max(0.0, min(1.0, float(values.get(house_num, 0.0))))
        return max(0.0, min(1.0, _casefold_lookup(values, item)))

    hd = context.get("hd", {})
    if not isinstance(hd, Mapping) or not bool(hd.get("available")):
        return None
    if property_name == "gates":
        try:
            return 1.0 if int(item) in set(hd.get("gates", set())) else 0.0
        except (TypeError, ValueError):
            return 0.0
    if property_name == "channels":
        channel = _channel_key(item)
        return 1.0 if channel is not None and channel in set(hd.get("channels", set())) else 0.0
    if property_name == "centers":
        return 1.0 if str(item).strip().casefold() in set(hd.get("centers", set())) else 0.0
    if property_name == "profiles":
        configured = _normalized_text(item).replace(" ", "")
        return 1.0 if configured and configured == str(hd.get("profile", "")) else 0.0
    if property_name == "authorities":
        return 1.0 if _normalized_text(item) == str(hd.get("authority", "")) else 0.0
    if property_name == "crosses":
        return 1.0 if _cross_matches(str(hd.get("cross", "")), item) else 0.0
    return None


def _category_score(
    theme_key: str,
    property_name: str,
    items: Sequence[Any],
    context: Mapping[str, Any],
) -> float | None:
    numerator = 0.0
    denominator = 0.0
    category_available = False
    for item in items:
        activation = _activation_for_item(property_name, item, context)
        if activation is None:
            continue
        category_available = True
        weight = _finite_float(theme_item_weight(theme_key, property_name, item))
        if weight is None or weight == 0.0:
            continue
        numerator += max(0.0, min(1.0, activation)) * float(weight)
        denominator += abs(float(weight))
    if not category_available or denominator <= 0.0:
        return None
    return max(0.0, min(1.0, numerator / denominator))


def calculate_theme_subtheme_scores(chart: Any) -> dict[str, float]:
    """Return 0..100 prominence scores keyed by stable subtheme key."""
    context = _activation_context(chart)
    scores: dict[str, float] = {}
    for theme_key, theme in THEMES.items():
        category_scores: list[float] = []
        for property_name in WEIGHTED_THEME_PROPERTIES:
            items = list(theme.get(property_name, []) or [])
            if not items:
                continue
            score = _category_score(theme_key, property_name, items, context)
            if score is not None:
                category_scores.append(score)
        if category_scores:
            scores[theme_key] = 100.0 * (sum(category_scores) / float(len(category_scores)))
    return scores


def calculate_theme_family_scores(
    chart: Any,
    *,
    subtheme_scores: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Return 0..100 macrotheme scores keyed by stable family key."""
    subthemes = dict(subtheme_scores or calculate_theme_subtheme_scores(chart))
    family_scores: dict[str, float] = {}
    for family_key in THEME_FAMILIES:
        values = [
            float(subthemes[theme_key])
            for theme_key in themes_in_family(family_key)
            if theme_key in subthemes and math.isfinite(float(subthemes[theme_key]))
        ]
        if values:
            family_scores[family_key] = sum(values) / float(len(values))
    return family_scores


def calculate_database_theme_family_averages(charts: Sequence[Any]) -> dict[str, float]:
    """Calculate macrotheme population means for an explicit chart sequence."""
    totals = {family_key: 0.0 for family_key in THEME_FAMILIES}
    counts = {family_key: 0 for family_key in THEME_FAMILIES}
    for chart in charts:
        try:
            scores = calculate_theme_family_scores(chart)
        except Exception:
            continue
        for family_key, value in scores.items():
            number = _finite_float(value)
            if number is None:
                continue
            totals[family_key] += number
            counts[family_key] += 1
    return {
        family_key: totals[family_key] / float(counts[family_key])
        for family_key in THEME_FAMILIES
        if counts[family_key] > 0
    }


def theme_family_snapshot_averages(snapshot: Mapping[str, Any] | None) -> dict[str, float]:
    """Read complete, definition-current macrotheme baselines from a snapshot."""
    payload = snapshot if isinstance(snapshot, Mapping) else {}
    if str(payload.get("theme_family_definition_signature", "") or "") != theme_definition_signature():
        return {}
    rows = payload.get("theme_family_raw_averages", {})
    if not isinstance(rows, Mapping):
        return {}
    averages: dict[str, float] = {}
    for family_key in THEME_FAMILIES:
        value = _finite_float(rows.get(family_key))
        if value is None:
            return {}
        averages[family_key] = value
    return averages if len(averages) == len(THEME_FAMILIES) else {}


def theme_snapshot_unavailability_reason(snapshot: Mapping[str, Any] | None) -> str:
    """Explain why the selected static snapshot cannot compare macrothemes."""
    payload = snapshot if isinstance(snapshot, Mapping) else {}
    if not payload:
        return "The selected DB Norms snapshot is unavailable."
    stored_signature = str(payload.get("theme_family_definition_signature", "") or "")
    if not stored_signature:
        return "The selected DB Norms snapshot does not contain Theme baselines yet."
    if stored_signature != theme_definition_signature():
        return "Theme definitions changed after this DB Norms snapshot was calculated."
    rows = payload.get("theme_family_raw_averages", {})
    if not isinstance(rows, Mapping) or any(_finite_float(rows.get(key)) is None for key in THEME_FAMILIES):
        return "The selected DB Norms snapshot contains incomplete Theme baselines."
    return "Theme DB Norms are unavailable."
