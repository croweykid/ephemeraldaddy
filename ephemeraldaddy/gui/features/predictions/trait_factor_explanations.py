"""Build Chart Info evidence for custom Trait predictions.

This module owns presentation-oriented factor grouping for the Predictions
workflow. It intentionally does not change weighted predictor scoring: it uses
the scorer's existing normalizers, eligibility rules, active scoring options,
and matched-factor result to explain which configured positive opportunities
did not contribute to the current chart.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any, Mapping

from ephemeraldaddy.analysis import weighted_chart_predictor as predictor
from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.core.interpretations import ZODIAC_NAMES


@dataclass(frozen=True)
class TraitFactorEvidence:
    """Ordered Chart Info evidence for one trait/profile pair."""

    supporting: tuple[str, ...]
    counter_factors: tuple[str, ...]
    missing: tuple[str, ...]


@dataclass(frozen=True)
class _PositiveCandidate:
    category: str
    criterion: Any
    label: str
    dominance: bool = False
    position_subject: str = ""
    position_destination: str = ""


def _weighted_text_entries(values: Any) -> tuple[str, ...]:
    """Match weighted_chart_predictor's aspect-entry normalization and order."""
    return tuple(
        token
        for raw_value in predictor.coerce_weighted_entries(values)
        if (token := str(raw_value).strip())
    )


def _position_candidate(spec: str) -> _PositiveCandidate:
    parsed = predictor.parse_position_spec(spec)
    if parsed is None:
        return _PositiveCandidate("positions", spec, spec)
    category, container, subject = parsed
    if category == "body_in_sign" and isinstance(container, str):
        return _PositiveCandidate(
            "positions",
            spec,
            spec,
            position_subject=str(subject),
            position_destination=container,
        )
    if category == "body_in_house" and isinstance(container, int):
        return _PositiveCandidate(
            "positions",
            spec,
            spec,
            position_subject=str(subject),
            position_destination=f"House {container}",
        )
    if category == "sign_in_house" and isinstance(container, int):
        return _PositiveCandidate(
            "positions",
            spec,
            spec,
            position_subject=f"House {container}",
            position_destination=str(subject),
        )
    return _PositiveCandidate("positions", spec, spec)


def _eligible_positive_candidates(chart: Any, factors: Mapping[str, Any]) -> list[_PositiveCandidate]:
    """Return positive criteria in the same category order as Supporting evidence."""
    use_houses = bool(chart_uses_houses(chart))
    candidates: list[_PositiveCandidate] = []

    def add_strings(category: str, values: Any, *, dominance: bool = False) -> None:
        candidates.extend(
            _PositiveCandidate(category, label, label, dominance=dominance)
            for label in predictor.weighted_string_entries(values)
        )

    add_strings("signs", factors.get("signs", set()), dominance=True)
    add_strings("bodies", factors.get("bodies", set()), dominance=True)
    add_strings("nakshatras", factors.get("nakshatras", set()), dominance=True)

    if use_houses:
        candidates.extend(
            _PositiveCandidate("houses", house, f"House {house}", dominance=True)
            for house in predictor.weighted_house_entries(factors.get("houses", set()))
        )

    candidates.extend(
        _PositiveCandidate("gates", gate, f"Gate {gate}")
        for gate in predictor.weighted_gate_entries(factors.get("gates", set()))
    )
    candidates.extend(
        _PositiveCandidate("channels", channel, f"Channel {channel[0]}–{channel[1]}")
        for channel in predictor.weighted_channel_entries(factors.get("channels", set()))
    )
    candidates.extend(
        _PositiveCandidate("hdtypes", value, str(value).replace("_", " ").title())
        for value in predictor.weighted_hd_type_entries(factors.get("hdtypes", set()))
    )
    candidates.extend(
        _PositiveCandidate("centers", value, f"{value} Center")
        for value in predictor.weighted_hd_center_entries(factors.get("centers", set()))
    )
    candidates.extend(
        _PositiveCandidate("profiles", value, f"Profile {value}")
        for value in predictor.weighted_hd_profile_entries(factors.get("profiles", set()))
    )
    candidates.extend(
        _PositiveCandidate("authorities", value, f"{value} Authority")
        for value in predictor.weighted_hd_authority_entries(factors.get("authorities", set()))
    )
    candidates.extend(
        _PositiveCandidate("bazisigns", value, f"BaZi {value}")
        for value in predictor.weighted_bazi_sign_entries(factors.get("bazisigns", set()))
    )

    for spec in predictor.weighted_position_entries(factors.get("positions", set())):
        if use_houses or not predictor.position_spec_uses_houses(spec):
            candidates.append(_position_candidate(spec))

    for spec in _weighted_text_entries(factors.get("aspects", set())):
        if use_houses or not predictor.aspect_spec_uses_houses(spec):
            candidates.append(_PositiveCandidate("aspects", spec, spec))

    return candidates


def _scorer_mutual_exclusive_bucket(candidate: _PositiveCandidate) -> tuple[str, Any] | None:
    """Return the active scorer bucket for a positive candidate, if any.

    The scorer currently keeps the bucket helpers private, so the explainer
    deliberately calls those exact helpers instead of maintaining a second
    implementation. If the scorer's global option disables mutual-exclusive
    bucket scoring, Missing must also treat every criterion independently.
    """
    if not predictor.DEFAULT_SCORING_OPTIONS.use_mutual_exclusive_bucket_scoring:
        return None
    if candidate.category == "positions":
        bucket = predictor._singleton_position_bucket(candidate.criterion)
    elif candidate.category in {"hdtypes", "profiles", "authorities"}:
        bucket = predictor._one_bucket(candidate.criterion)
    else:
        return None
    return (candidate.category, bucket) if bucket is not None else None


def _join_values(values: list[str], *, conjunction: str) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} {conjunction} {values[1]}"
    return f"{', '.join(values[:-1])} {conjunction} {values[-1]}"


def _format_missing_gates(gate_labels: list[str]) -> str:
    gates = [label.removeprefix("Gate ") for label in gate_labels]
    if len(gates) == 1:
        return f"Missing Gate {gates[0]}"
    return f"Missing Gates {_join_values(gates, conjunction='&')}"


def _semantic_span(text: str, color: str | None) -> str:
    escaped = html.escape(text)
    if not color:
        return escaped
    return f'<span style="color:{html.escape(str(color), quote=True)};font-weight:700;">{escaped}</span>'


def _gate_number_html(gate: str, color_map: Mapping[str, str]) -> str:
    return _semantic_span(gate, color_map.get(f"Gate {gate}"))


def _profile_html(token: str, color_map: Mapping[str, str]) -> str:
    match = re.fullmatch(r"Profile\s+([1-6])/([1-6])", token)
    if not match:
        return html.escape(token)
    first, second = match.groups()
    return (
        "Profile "
        f"{_semantic_span(first, color_map.get(f'Line {first}'))}/"
        f"{_semantic_span(second, color_map.get(f'Line {second}'))}"
    )


def _house_html(token: str, color_map: Mapping[str, str]) -> str:
    match = re.fullmatch(r"House\s+(1[0-2]|[1-9])", token)
    if not match:
        return html.escape(token)
    house = int(match.group(1))
    sign = ZODIAC_NAMES[house - 1] if 1 <= house <= len(ZODIAC_NAMES) else ""
    return _semantic_span(token, color_map.get(sign))


def _channel_html(token: str, color_map: Mapping[str, str]) -> str:
    match = re.fullmatch(r"Channel\s+(\d{1,2})([-–])(\d{1,2})", token)
    if not match:
        return html.escape(token)
    first, dash, second = match.groups()
    return (
        "Channel "
        f"{_gate_number_html(first, color_map)}{html.escape(dash)}{_gate_number_html(second, color_map)}"
    )


def missing_factor_html(value: str) -> str:
    """Escape one Missing row while retaining semantic colors for every factor family.

    The shared Chart Info colorizer already covers signs, bodies, nakshatras,
    aspects, HD types, centers, authorities, gates, and their occurrences inside
    position text. This formatter fills the remaining gaps introduced by Missing:
    compact gate groups, houses, profiles, en-dash channels, and BaZi labels.
    """
    text = str(value or "")
    from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR, chart_info_token_color_map

    color_map = chart_info_token_color_map()
    if text.startswith("Missing Gate ") or text.startswith("Missing Gates "):
        rendered: list[str] = []
        last = 0
        for match in re.finditer(r"\b\d{1,2}\b", text):
            rendered.append(html.escape(text[last:match.start()]))
            rendered.append(_gate_number_html(match.group(0), color_map))
            last = match.end()
        rendered.append(html.escape(text[last:]))
        return "".join(rendered)

    pattern = re.compile(
        r"\bProfile\s+[1-6]/[1-6]\b"
        r"|\bHouse\s+(?:1[0-2]|[1-9])\b"
        r"|\bChannel\s+\d{1,2}[-–]\d{1,2}\b"
        r"|\bBaZi\s+[A-Za-z]+\b"
    )
    rendered = []
    last = 0
    for match in pattern.finditer(text):
        rendered.append(html.escape(text[last:match.start()]))
        token = match.group(0)
        if token.startswith("Profile "):
            rendered.append(_profile_html(token, color_map))
        elif token.startswith("House "):
            rendered.append(_house_html(token, color_map))
        elif token.startswith("Channel "):
            rendered.append(_channel_html(token, color_map))
        else:
            rendered.append(_semantic_span(token, CHART_DATA_HIGHLIGHT_COLOR))
        last = match.end()
    rendered.append(html.escape(text[last:]))
    return "".join(rendered)


def _format_missing_position_group(candidates: list[_PositiveCandidate]) -> str:
    first = candidates[0]
    destinations = [candidate.position_destination for candidate in candidates if candidate.position_destination]
    if not first.position_subject or not destinations:
        return first.label
    return f"{first.position_subject} not in {_join_values(destinations, conjunction='or')}"


def build_trait_factor_evidence(
    chart: Any,
    factors: Mapping[str, Any] | None,
    *,
    matches: Mapping[str, list[str]] | None = None,
) -> TraitFactorEvidence:
    """Return Supporting, Counter-factors, and compact Missing explanations.

    ``Missing`` is the complement of *eligible positive* criteria only. Anti
    criteria remain Counter-factors and are never presented as missing
    positives. Mutual-exclusion suppression follows the scorer's active global
    option and its exact bucket helpers for positions, HD type, profile, and
    authority. Position alternatives are compacted only while that scorer
    option is enabled.
    """
    profile = factors if isinstance(factors, Mapping) else {}
    resolved_matches = matches if isinstance(matches, Mapping) else predictor.matched_weighted_criteria(chart, profile)
    supporting = tuple(str(value) for value in resolved_matches.get("positive", []) if str(value))
    counter_factors = tuple(str(value) for value in resolved_matches.get("negative", []) if str(value))
    matched_positive = set(supporting)
    candidates = _eligible_positive_candidates(chart, profile)

    exclusive_groups: dict[tuple[str, Any], list[_PositiveCandidate]] = {}
    matched_exclusive_buckets: set[tuple[str, Any]] = set()
    bucket_by_candidate: dict[int, tuple[str, Any] | None] = {}
    for candidate in candidates:
        bucket = _scorer_mutual_exclusive_bucket(candidate)
        bucket_by_candidate[id(candidate)] = bucket
        if bucket is None:
            continue
        exclusive_groups.setdefault(bucket, []).append(candidate)
        if candidate.label in matched_positive:
            matched_exclusive_buckets.add(bucket)

    unmatched_gates = [
        candidate.label
        for candidate in candidates
        if candidate.category == "gates" and candidate.label not in matched_positive
    ]
    emitted_gate_group = False
    emitted_position_groups: set[tuple[str, Any]] = set()
    missing: list[str] = []

    for candidate in candidates:
        if candidate.label in matched_positive:
            continue
        if candidate.category == "gates":
            if not emitted_gate_group and unmatched_gates:
                missing.append(_format_missing_gates(unmatched_gates))
                emitted_gate_group = True
            continue

        bucket = bucket_by_candidate.get(id(candidate))
        if bucket is not None and bucket in matched_exclusive_buckets:
            continue
        if candidate.category == "positions" and bucket is not None:
            if bucket in emitted_position_groups:
                continue
            group = [item for item in exclusive_groups.get(bucket, []) if item.label not in matched_positive]
            if group:
                missing.append(_format_missing_position_group(group))
            emitted_position_groups.add(bucket)
            continue

        if candidate.dominance:
            missing.append(f"{candidate.label} not above baseline in chart")
        else:
            missing.append(candidate.label)

    return TraitFactorEvidence(
        supporting=supporting,
        counter_factors=counter_factors,
        missing=tuple(missing),
    )
