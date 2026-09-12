"""Build Chart Info evidence for custom Trait predictions.

This module owns presentation-oriented factor grouping for the Predictions
workflow. It intentionally does not change weighted predictor scoring: it uses
the scorer's existing normalizers, eligibility rules, active scoring options,
and matched-factor result to explain signed trait evidence.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any, Mapping

from ephemeraldaddy.analysis import weighted_chart_predictor as predictor
from ephemeraldaddy.core.chart import chart_uses_houses


@dataclass(frozen=True)
class TraitFactorEvidence:
    """Ordered Chart Info evidence for one trait/profile pair."""

    supporting: tuple[str, ...]
    missing: tuple[str, ...]
    inverse_present: tuple[str, ...]
    inverse_missing: tuple[str, ...]
    negative_indicators_present: tuple[str, ...]
    negative_indicators_missing: tuple[str, ...]
    positive_unknown: tuple[str, ...] = ()
    inverse_unknown: tuple[str, ...] = ()
    negative_indicators_unknown: tuple[str, ...] = ()
    has_negative_definitions: bool = False

    @property
    def counter_factors(self) -> tuple[str, ...]:
        """Compatibility view used by older callers/tests."""
        return self.inverse_present + self.negative_indicators_present


@dataclass(frozen=True)
class _FactorCandidate:
    category: str
    criterion: Any
    label: str
    weight: float
    dominance: bool = False
    position_subject: str = ""
    position_destination: str = ""
    requires_houses: bool = False


def _weighted_text_entries(values: Any) -> dict[str, float]:
    """Match weighted_chart_predictor's aspect-entry normalization and weights."""
    entries: dict[str, float] = {}
    for raw_value, weight in predictor.coerce_weighted_entries(values).items():
        token = str(raw_value).strip()
        if token:
            entries[token] = float(weight)
    return entries


def _position_candidate(
    spec: str,
    weight: float,
    *,
    requires_houses: bool = False,
) -> _FactorCandidate:
    parsed = predictor.parse_position_spec(spec)
    if parsed is None:
        return _FactorCandidate(
            "positions",
            spec,
            spec,
            weight,
            requires_houses=requires_houses,
        )
    category, container, subject = parsed
    if category == "body_in_sign" and isinstance(container, str):
        return _FactorCandidate(
            "positions",
            spec,
            spec,
            weight,
            position_subject=str(subject),
            position_destination=container,
            requires_houses=requires_houses,
        )
    if category == "body_in_house" and isinstance(container, int):
        return _FactorCandidate(
            "positions",
            spec,
            spec,
            weight,
            position_subject=str(subject),
            position_destination=f"House {container}",
            requires_houses=requires_houses,
        )
    if category == "sign_in_house" and isinstance(container, int):
        return _FactorCandidate(
            "positions",
            spec,
            spec,
            weight,
            position_subject=f"House {container}",
            position_destination=str(subject),
            requires_houses=requires_houses,
        )
    return _FactorCandidate(
        "positions",
        spec,
        spec,
        weight,
        requires_houses=requires_houses,
    )


def _configured_candidates(
    factors: Mapping[str, Any],
    *,
    prefix: str = "",
) -> list[_FactorCandidate]:
    """Return every configured nonzero criterion in scorer presentation order."""
    candidates: list[_FactorCandidate] = []

    def values_for(category: str) -> Any:
        return factors.get(f"{prefix}{category}", set())

    def add_strings(category: str, *, dominance: bool = False) -> None:
        candidates.extend(
            _FactorCandidate(category, label, label, float(weight), dominance=dominance)
            for label, weight in predictor.weighted_string_entries(values_for(category)).items()
            if float(weight) != 0.0
        )

    add_strings("signs", dominance=True)
    add_strings("bodies", dominance=True)
    add_strings("nakshatras", dominance=True)

    candidates.extend(
        _FactorCandidate(
            "houses",
            house,
            f"House {house}",
            float(weight),
            dominance=True,
            requires_houses=True,
        )
        for house, weight in predictor.weighted_house_entries(values_for("houses")).items()
        if float(weight) != 0.0
    )

    candidates.extend(
        _FactorCandidate("gates", gate, f"Gate {gate}", float(weight))
        for gate, weight in predictor.weighted_gate_entries(values_for("gates")).items()
        if float(weight) != 0.0
    )
    candidates.extend(
        _FactorCandidate("channels", channel, f"Channel {channel[0]}–{channel[1]}", float(weight))
        for channel, weight in predictor.weighted_channel_entries(values_for("channels")).items()
        if float(weight) != 0.0
    )
    candidates.extend(
        _FactorCandidate("hdtypes", value, str(value).replace("_", " ").title(), float(weight))
        for value, weight in predictor.weighted_hd_type_entries(values_for("hdtypes")).items()
        if float(weight) != 0.0
    )
    candidates.extend(
        _FactorCandidate("centers", value, f"{value} Center", float(weight))
        for value, weight in predictor.weighted_hd_center_entries(values_for("centers")).items()
        if float(weight) != 0.0
    )
    candidates.extend(
        _FactorCandidate("profiles", value, f"Profile {value}", float(weight))
        for value, weight in predictor.weighted_hd_profile_entries(values_for("profiles")).items()
        if float(weight) != 0.0
    )
    candidates.extend(
        _FactorCandidate("authorities", value, f"{value} Authority", float(weight))
        for value, weight in predictor.weighted_hd_authority_entries(values_for("authorities")).items()
        if float(weight) != 0.0
    )
    candidates.extend(
        _FactorCandidate("bazisigns", value, f"BaZi {value}", float(weight))
        for value, weight in predictor.weighted_bazi_sign_entries(values_for("bazisigns")).items()
        if float(weight) != 0.0
    )

    for spec, weight in predictor.weighted_position_entries(values_for("positions")).items():
        if float(weight) == 0.0:
            continue
        candidates.append(
            _position_candidate(
                spec,
                float(weight),
                requires_houses=bool(predictor.position_spec_uses_houses(spec)),
            )
        )

    for spec, weight in _weighted_text_entries(values_for("aspects")).items():
        if float(weight) == 0.0:
            continue
        candidates.append(
            _FactorCandidate(
                "aspects",
                spec,
                spec,
                float(weight),
                requires_houses=bool(predictor.aspect_spec_uses_houses(spec)),
            )
        )

    return candidates


def _eligible_candidates(
    chart: Any,
    factors: Mapping[str, Any],
    *,
    prefix: str = "",
) -> list[_FactorCandidate]:
    """Return configured criteria that the chart can actually evaluate."""
    configured = _configured_candidates(factors, prefix=prefix)
    if bool(chart_uses_houses(chart)):
        return configured
    return [candidate for candidate in configured if not candidate.requires_houses]


def _scorer_mutual_exclusive_bucket(candidate: _FactorCandidate) -> tuple[str, Any] | None:
    """Return the active scorer bucket for a candidate, if any.

    The scorer currently keeps the bucket helpers private, so the explainer
    deliberately calls those exact helpers instead of maintaining a second
    implementation. If the scorer's global option disables mutual-exclusive
    bucket scoring, Chart Info also treats every criterion independently.
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
    """Escape one absent-factor row while retaining semantic factor colors."""
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
        elif token.startswith("Channel "):
            rendered.append(_channel_html(token, color_map))
        else:
            rendered.append(_semantic_span(token, CHART_DATA_HIGHLIGHT_COLOR))
        last = match.end()
    rendered.append(html.escape(text[last:]))
    return "".join(rendered)


def _format_missing_position_group(candidates: list[_FactorCandidate]) -> str:
    first = candidates[0]
    destinations = [candidate.position_destination for candidate in candidates if candidate.position_destination]
    if not first.position_subject or not destinations:
        return first.label
    return f"{first.position_subject} not in {_join_values(destinations, conjunction='or')}"


def _candidate_buckets(candidates: list[_FactorCandidate]) -> list[tuple[str, Any] | None]:
    return [_scorer_mutual_exclusive_bucket(candidate) for candidate in candidates]


def _missing_rows(
    candidates: list[_FactorCandidate],
    *,
    family_candidates: list[_FactorCandidate],
    family_buckets: list[tuple[str, Any] | None],
    matched_labels: set[str],
) -> tuple[str, ...]:
    """Format absent candidates while honoring scorer-wide exclusivity rules."""
    bucket_by_id = {
        id(candidate): bucket
        for candidate, bucket in zip(family_candidates, family_buckets)
    }
    matched_buckets = {
        bucket
        for candidate, bucket in zip(family_candidates, family_buckets)
        if bucket is not None and candidate.label in matched_labels
    }

    unmatched_gates = [
        candidate.label
        for candidate in candidates
        if candidate.category == "gates" and candidate.label not in matched_labels
    ]
    position_groups: dict[tuple[str, Any], list[_FactorCandidate]] = {}
    for candidate in candidates:
        bucket = bucket_by_id.get(id(candidate))
        if candidate.category == "positions" and bucket is not None:
            position_groups.setdefault(bucket, []).append(candidate)

    emitted_gate_group = False
    emitted_position_groups: set[tuple[str, Any]] = set()
    missing: list[str] = []

    for candidate in candidates:
        if candidate.label in matched_labels:
            continue
        bucket = bucket_by_id.get(id(candidate))
        if bucket is not None and bucket in matched_buckets:
            continue

        if candidate.category == "gates":
            if not emitted_gate_group and unmatched_gates:
                missing.append(_format_missing_gates(unmatched_gates))
                emitted_gate_group = True
            continue

        if candidate.category == "positions" and bucket is not None:
            if bucket in emitted_position_groups:
                continue
            group = [
                item
                for item in position_groups.get(bucket, [])
                if item.label not in matched_labels
            ]
            if group:
                missing.append(_format_missing_position_group(group))
            emitted_position_groups.add(bucket)
            continue

        if candidate.dominance:
            missing.append(f"{candidate.label} not above baseline in chart")
        else:
            missing.append(candidate.label)

    return tuple(missing)


def _unknown_rows(candidates: list[_FactorCandidate]) -> tuple[str, ...]:
    """Label configured criteria that cannot be evaluated without birth time."""
    return tuple(f"{candidate.label} (no BT: unknown)" for candidate in candidates)


def build_trait_factor_evidence(
    chart: Any,
    factors: Mapping[str, Any] | None,
    *,
    matches: Mapping[str, list[str]] | None = None,
) -> TraitFactorEvidence:
    """Partition signed trait evidence for Chart Info without changing scoring.

    Normal trait properties use the sign of their configured weight:
    positive weights are supporting opportunities, negative weights are inverse
    indicators, and zero weights are omitted. Anti-properties remain a separate
    negative-indicator family regardless of their signed value.

    House-dependent criteria on charts without usable houses are retained as
    unknown rather than being mislabeled missing or undefined. Missing/absent
    rows share the scorer's mutual-exclusive buckets across normal and anti
    families, matching scorer behavior for positions, HD type, profile, and
    authority alternatives.
    """
    profile = factors if isinstance(factors, Mapping) else {}
    resolved_matches = (
        matches
        if isinstance(matches, Mapping)
        else predictor.matched_weighted_criteria(chart, profile)
    )
    matched_normal = {
        str(value)
        for value in resolved_matches.get("positive", [])
        if str(value)
    }
    matched_anti = {
        str(value)
        for value in resolved_matches.get("negative", [])
        if str(value)
    }
    matched_all = matched_normal | matched_anti

    use_houses = bool(chart_uses_houses(chart))
    normal_configured = _configured_candidates(profile)
    anti_configured = _configured_candidates(profile, prefix="anti")

    normal_candidates = [
        candidate
        for candidate in normal_configured
        if use_houses or not candidate.requires_houses
    ]
    anti_candidates = [
        candidate
        for candidate in anti_configured
        if use_houses or not candidate.requires_houses
    ]
    normal_unknown_candidates = (
        []
        if use_houses
        else [candidate for candidate in normal_configured if candidate.requires_houses]
    )
    anti_unknown_candidates = (
        []
        if use_houses
        else [candidate for candidate in anti_configured if candidate.requires_houses]
    )

    positive_candidates = [
        candidate for candidate in normal_candidates if candidate.weight > 0.0
    ]
    inverse_candidates = [
        candidate for candidate in normal_candidates if candidate.weight < 0.0
    ]
    positive_unknown_candidates = [
        candidate for candidate in normal_unknown_candidates if candidate.weight > 0.0
    ]
    inverse_unknown_candidates = [
        candidate for candidate in normal_unknown_candidates if candidate.weight < 0.0
    ]

    scorer_family_candidates = normal_candidates + anti_candidates
    scorer_family_buckets = _candidate_buckets(scorer_family_candidates)

    supporting = tuple(
        candidate.label
        for candidate in positive_candidates
        if candidate.label in matched_normal
    )
    inverse_present = tuple(
        candidate.label
        for candidate in inverse_candidates
        if candidate.label in matched_normal
    )
    negative_indicators_present = tuple(
        candidate.label
        for candidate in anti_candidates
        if candidate.label in matched_anti
    )

    missing = _missing_rows(
        positive_candidates,
        family_candidates=scorer_family_candidates,
        family_buckets=scorer_family_buckets,
        matched_labels=matched_all,
    )
    inverse_missing = _missing_rows(
        inverse_candidates,
        family_candidates=scorer_family_candidates,
        family_buckets=scorer_family_buckets,
        matched_labels=matched_all,
    )
    negative_indicators_missing = _missing_rows(
        anti_candidates,
        family_candidates=scorer_family_candidates,
        family_buckets=scorer_family_buckets,
        matched_labels=matched_all,
    )

    return TraitFactorEvidence(
        supporting=supporting,
        missing=missing,
        inverse_present=inverse_present,
        inverse_missing=inverse_missing,
        negative_indicators_present=negative_indicators_present,
        negative_indicators_missing=negative_indicators_missing,
        positive_unknown=_unknown_rows(positive_unknown_candidates),
        inverse_unknown=_unknown_rows(inverse_unknown_candidates),
        negative_indicators_unknown=_unknown_rows(anti_unknown_candidates),
        has_negative_definitions=bool(anti_configured),
    )
