"""Availability-stratified population norms for semantic Theme prominence.

Theme prominence intentionally omits factor categories that cannot be known for
one chart (for example houses and Human Design on an unknown-time chart). That
makes the chart-level score more honest, but it also means two charts can have
different score denominators. Population comparisons therefore stay inside the
same data-availability stratum.

The legacy family-prominence snapshot fields remain intact for compatibility.
The chart-share fields added here are the source of the Predictions table's
``% of chart`` and empirical ``vs DB`` percentile displays.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

from ephemeraldaddy.analysis import theme_prominence as prominence


THEME_NORMS_AVAILABILITY_SCHEMA_VERSION = 1
THEME_FAMILY_AVAILABILITY_ROWS_FIELD = "theme_family_raw_averages_by_availability"
THEME_FAMILY_AVAILABILITY_COUNTS_FIELD = "theme_family_availability_counts"
THEME_NORMS_AVAILABILITY_SCHEMA_FIELD = "theme_family_availability_schema_version"

THEME_CHART_SHARE_SCHEMA_VERSION = 1
THEME_CHART_SHARE_SCHEMA_FIELD = "theme_chart_share_schema_version"
THEME_SUBTHEME_SHARE_AVERAGES_FIELD = "theme_subtheme_chart_share_averages_by_availability"
THEME_SUBTHEME_SHARE_VALUES_FIELD = "theme_subtheme_chart_share_values_by_availability"
THEME_FAMILY_SHARE_AVERAGES_FIELD = "theme_family_chart_share_averages_by_availability"
THEME_FAMILY_SHARE_VALUES_FIELD = "theme_family_chart_share_values_by_availability"
THEME_FACTOR_ACTIVATION_VALUES_FIELD = "theme_factor_activation_values_by_availability"


def theme_availability_key_from_context(context: Mapping[str, Any]) -> str:
    """Return the stable denominator/availability key for one scoring context."""
    hd = context.get("hd", {})
    hd_available = isinstance(hd, Mapping) and bool(hd.get("available"))
    return "|".join(
        (
            f"houses:{int(bool(context.get('houses_available')))}",
            f"hd:{int(hd_available)}",
            f"bazi:{int(bool(context.get('bazi_available')))}",
        )
    )


def theme_availability_key(chart: Any) -> str:
    """Return the production scoring availability key for ``chart``."""
    return theme_availability_key_from_context(prominence._activation_context(chart))


def calculate_theme_subtheme_scores_from_context(
    context: Mapping[str, Any],
) -> dict[str, float]:
    """Score subthemes from an already-built production activation context."""
    scores: dict[str, float] = {}
    for theme_key, theme in prominence.THEMES.items():
        category_scores: list[float] = []
        for property_name in prominence.WEIGHTED_THEME_PROPERTIES:
            items = list(theme.get(property_name, []) or [])
            if not items:
                continue
            score = prominence._category_score(theme_key, property_name, items, context)
            if score is not None:
                category_scores.append(float(score))
        if category_scores:
            scores[theme_key] = 100.0 * (
                sum(category_scores) / float(len(category_scores))
            )
    return scores


def calculate_theme_scores_from_context(
    context: Mapping[str, Any],
) -> tuple[dict[str, float], dict[str, float]]:
    """Return subtheme and family prominence scores without rebuilding context."""
    subthemes = calculate_theme_subtheme_scores_from_context(context)
    families = prominence.calculate_theme_family_scores(
        None,
        subtheme_scores=subthemes,
    )
    return subthemes, families


def calculate_theme_chart_shares(
    subtheme_scores: Mapping[str, float],
) -> tuple[dict[str, float], dict[str, float]]:
    """Normalize subtheme prominence into additive shares of Theme activation.

    Subtheme shares sum to 100 across scorable configured subthemes. Family
    shares are the sums of their child shares, so the seven macrothemes also
    sum to 100. These shares are presentation/comparison values; the underlying
    prominence scorer remains unchanged.
    """
    clean: dict[str, float] = {}
    for theme_key in prominence.THEMES:
        try:
            value = float(subtheme_scores.get(theme_key, 0.0))
        except (TypeError, ValueError):
            value = 0.0
        clean[theme_key] = value if math.isfinite(value) and value > 0.0 else 0.0

    total = sum(clean.values())
    if total <= 0.0:
        subtheme_shares = {theme_key: 0.0 for theme_key in clean}
    else:
        subtheme_shares = {
            theme_key: (value / total) * 100.0
            for theme_key, value in clean.items()
        }

    family_shares: dict[str, float] = {}
    for family_key in prominence.THEME_FAMILIES:
        family_shares[family_key] = sum(
            subtheme_shares.get(theme_key, 0.0)
            for theme_key in prominence.themes_in_family(family_key)
        )
    return subtheme_shares, family_shares


def empirical_percentile(value: float, samples: Sequence[float]) -> float | None:
    """Return a mid-rank empirical percentile for ``value`` among ``samples``."""
    try:
        target = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(target):
        return None
    clean: list[float] = []
    for sample in samples:
        try:
            numeric = float(sample)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            clean.append(numeric)
    if not clean:
        return None
    less = sum(1 for sample in clean if sample < target)
    equal = sum(1 for sample in clean if sample == target)
    return 100.0 * (less + (0.5 * equal)) / float(len(clean))


def format_theme_percentile(percentile: float | None) -> str:
    """Format an empirical percentile as the compact UI label ``94th p``."""
    if percentile is None:
        return "—"
    rounded = max(0, min(100, int(round(float(percentile)))))
    if 10 <= rounded % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(rounded % 10, "th")
    return f"{rounded}{suffix} p"


def theme_factor_distribution_key(property_name: str, item: Any) -> str:
    """Return a stable JSON key for one configured Theme factor."""
    return json.dumps([str(property_name), item], ensure_ascii=False, separators=(",", ":"))


def _averages_from_totals(
    totals: Mapping[str, float],
    counts: Mapping[str, int],
) -> dict[str, float]:
    return {
        family_key: float(totals[family_key]) / float(counts[family_key])
        for family_key in prominence.THEME_FAMILIES
        if int(counts.get(family_key, 0)) > 0
    }


def _mean_rows(values: Mapping[str, Sequence[float]]) -> dict[str, float]:
    rows: dict[str, float] = {}
    for key, samples in values.items():
        clean = [float(sample) for sample in samples if math.isfinite(float(sample))]
        if clean:
            rows[str(key)] = sum(clean) / float(len(clean))
    return rows


def _configured_factor_items() -> tuple[tuple[str, Any], ...]:
    unique: dict[str, tuple[str, Any]] = {}
    for theme in prominence.THEMES.values():
        for property_name in prominence.WEIGHTED_THEME_PROPERTIES:
            for item in theme.get(property_name, []) or []:
                key = theme_factor_distribution_key(property_name, item)
                unique.setdefault(key, (property_name, item))
    return tuple(unique.values())


def calculate_database_theme_norms(charts: Sequence[Any]) -> dict[str, Any]:
    """Calculate legacy prominence means plus chart-share percentile samples."""
    overall_totals = {family_key: 0.0 for family_key in prominence.THEME_FAMILIES}
    overall_counts = {family_key: 0 for family_key in prominence.THEME_FAMILIES}
    raw_stratum_totals: dict[str, dict[str, float]] = {}
    raw_stratum_counts: dict[str, dict[str, int]] = {}
    stratum_chart_counts: dict[str, int] = {}

    subtheme_values: dict[str, dict[str, list[float]]] = {}
    family_values: dict[str, dict[str, list[float]]] = {}
    factor_values: dict[str, dict[str, list[float]]] = {}
    configured_factors = _configured_factor_items()

    for chart in charts:
        try:
            context = prominence._activation_context(chart)
            subtheme_scores, family_scores = calculate_theme_scores_from_context(context)
            availability_key = theme_availability_key_from_context(context)
            subtheme_shares, family_shares = calculate_theme_chart_shares(subtheme_scores)
        except Exception:
            continue

        stratum_chart_counts[availability_key] = int(stratum_chart_counts.get(availability_key, 0)) + 1
        raw_totals = raw_stratum_totals.setdefault(
            availability_key,
            {family_key: 0.0 for family_key in prominence.THEME_FAMILIES},
        )
        raw_counts = raw_stratum_counts.setdefault(
            availability_key,
            {family_key: 0 for family_key in prominence.THEME_FAMILIES},
        )
        sub_rows = subtheme_values.setdefault(availability_key, {})
        family_rows = family_values.setdefault(availability_key, {})
        factor_rows = factor_values.setdefault(availability_key, {})

        for family_key, raw_value in family_scores.items():
            try:
                numeric = float(raw_value)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(numeric):
                continue
            overall_totals[family_key] += numeric
            overall_counts[family_key] += 1
            raw_totals[family_key] += numeric
            raw_counts[family_key] += 1

        for theme_key, share in subtheme_shares.items():
            sub_rows.setdefault(theme_key, []).append(float(share))
        for family_key, share in family_shares.items():
            family_rows.setdefault(family_key, []).append(float(share))

        for property_name, item in configured_factors:
            try:
                activation = prominence._activation_for_item(property_name, item, context)
            except Exception:
                continue
            if activation is None:
                continue
            try:
                numeric = float(activation)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(numeric):
                continue
            factor_rows.setdefault(
                theme_factor_distribution_key(property_name, item), []
            ).append(max(0.0, min(1.0, numeric)))

    legacy_overall = _averages_from_totals(overall_totals, overall_counts)
    legacy_by_availability = {
        availability_key: _averages_from_totals(
            raw_stratum_totals[availability_key], raw_stratum_counts[availability_key]
        )
        for availability_key in sorted(raw_stratum_totals)
    }

    return {
        "legacy_family_averages": legacy_overall,
        "legacy_family_averages_by_availability": legacy_by_availability,
        "chart_counts": dict(sorted(stratum_chart_counts.items())),
        "subtheme_share_averages_by_availability": {
            key: _mean_rows(rows) for key, rows in sorted(subtheme_values.items())
        },
        "subtheme_share_values_by_availability": {
            key: {name: sorted(values) for name, values in sorted(rows.items())}
            for key, rows in sorted(subtheme_values.items())
        },
        "family_share_averages_by_availability": {
            key: _mean_rows(rows) for key, rows in sorted(family_values.items())
        },
        "family_share_values_by_availability": {
            key: {name: sorted(values) for name, values in sorted(rows.items())}
            for key, rows in sorted(family_values.items())
        },
        "factor_activation_values_by_availability": {
            key: {name: sorted(values) for name, values in sorted(rows.items())}
            for key, rows in sorted(factor_values.items())
        },
    }


def calculate_database_theme_family_baselines(
    charts: Sequence[Any],
) -> tuple[dict[str, float], dict[str, dict[str, float]], dict[str, int]]:
    """Return legacy aggregate + availability-stratified Theme family means."""
    norms = calculate_database_theme_norms(charts)
    return (
        dict(norms["legacy_family_averages"]),
        dict(norms["legacy_family_averages_by_availability"]),
        dict(norms["chart_counts"]),
    )


def theme_family_snapshot_averages_for_availability(
    snapshot: Mapping[str, Any] | None,
    availability_key: str,
) -> dict[str, float]:
    """Read complete Theme family baselines for one denominator stratum."""
    payload = snapshot if isinstance(snapshot, Mapping) else {}
    if (
        str(payload.get("theme_family_definition_signature", "") or "")
        != prominence.theme_definition_signature()
    ):
        return {}
    if (
        int(payload.get(THEME_NORMS_AVAILABILITY_SCHEMA_FIELD, 0) or 0)
        != THEME_NORMS_AVAILABILITY_SCHEMA_VERSION
    ):
        return {}
    rows_by_availability = payload.get(THEME_FAMILY_AVAILABILITY_ROWS_FIELD, {})
    if not isinstance(rows_by_availability, Mapping):
        return {}
    rows = rows_by_availability.get(str(availability_key), {})
    if not isinstance(rows, Mapping):
        return {}

    averages: dict[str, float] = {}
    for family_key in prominence.THEME_FAMILIES:
        try:
            value = float(rows.get(family_key))
        except (TypeError, ValueError):
            return {}
        if not math.isfinite(value):
            return {}
        averages[family_key] = value
    return averages if len(averages) == len(prominence.THEME_FAMILIES) else {}


def theme_chart_share_norms_for_availability(
    snapshot: Mapping[str, Any] | None,
    availability_key: str,
) -> dict[str, Any]:
    """Read complete chart-share and factor distributions for one stratum."""
    payload = snapshot if isinstance(snapshot, Mapping) else {}
    if str(payload.get("theme_family_definition_signature", "") or "") != prominence.theme_definition_signature():
        return {}
    if int(payload.get(THEME_CHART_SHARE_SCHEMA_FIELD, 0) or 0) != THEME_CHART_SHARE_SCHEMA_VERSION:
        return {}

    requested_key = str(availability_key)
    fields = (
        THEME_SUBTHEME_SHARE_AVERAGES_FIELD,
        THEME_SUBTHEME_SHARE_VALUES_FIELD,
        THEME_FAMILY_SHARE_AVERAGES_FIELD,
        THEME_FAMILY_SHARE_VALUES_FIELD,
        THEME_FACTOR_ACTIVATION_VALUES_FIELD,
    )
    selected: dict[str, Mapping[str, Any]] = {}
    for field in fields:
        by_availability = payload.get(field, {})
        if not isinstance(by_availability, Mapping) or requested_key not in by_availability:
            return {}
        rows = by_availability[requested_key]
        if not isinstance(rows, Mapping) or not rows:
            return {}
        selected[field] = rows

    family_keys = set(prominence.THEME_FAMILIES)
    subtheme_keys = set(prominence.THEMES)
    if not family_keys.issubset(selected[THEME_FAMILY_SHARE_AVERAGES_FIELD]):
        return {}
    if not family_keys.issubset(selected[THEME_FAMILY_SHARE_VALUES_FIELD]):
        return {}
    if not subtheme_keys.issubset(selected[THEME_SUBTHEME_SHARE_AVERAGES_FIELD]):
        return {}
    if not subtheme_keys.issubset(selected[THEME_SUBTHEME_SHARE_VALUES_FIELD]):
        return {}

    return {
        "subtheme_means": dict(selected[THEME_SUBTHEME_SHARE_AVERAGES_FIELD]),
        "subtheme_values": dict(selected[THEME_SUBTHEME_SHARE_VALUES_FIELD]),
        "family_means": dict(selected[THEME_FAMILY_SHARE_AVERAGES_FIELD]),
        "family_values": dict(selected[THEME_FAMILY_SHARE_VALUES_FIELD]),
        "factor_values": dict(selected[THEME_FACTOR_ACTIVATION_VALUES_FIELD]),
    }


def theme_snapshot_unavailability_reason_for_availability(
    snapshot: Mapping[str, Any] | None,
    availability_key: str,
) -> str:
    """Explain why a chart cannot use an availability-matched Theme baseline."""
    payload = snapshot if isinstance(snapshot, Mapping) else {}
    if not payload:
        return "The selected DB Norms snapshot is unavailable."
    stored_signature = str(payload.get("theme_family_definition_signature", "") or "")
    if not stored_signature:
        return "The selected DB Norms snapshot does not contain Theme baselines yet."
    if stored_signature != prominence.theme_definition_signature():
        return "Theme definitions changed after this DB Norms snapshot was calculated."
    if int(payload.get(THEME_NORMS_AVAILABILITY_SCHEMA_FIELD, 0) or 0) != THEME_NORMS_AVAILABILITY_SCHEMA_VERSION:
        return "The selected DB Norms snapshot predates availability-stratified Theme baselines."
    rows_by_availability = payload.get(THEME_FAMILY_AVAILABILITY_ROWS_FIELD, {})
    if not isinstance(rows_by_availability, Mapping):
        return "The selected DB Norms snapshot contains invalid Theme availability baselines."
    rows = rows_by_availability.get(str(availability_key))
    if not isinstance(rows, Mapping):
        return "The selected DB Norms snapshot has no Theme baseline for this chart's data-availability profile."
    if any(
        not isinstance(rows.get(key), (int, float)) or not math.isfinite(float(rows.get(key)))
        for key in prominence.THEME_FAMILIES
    ):
        return "The selected DB Norms snapshot contains incomplete Theme baselines for this data-availability profile."
    return "Theme DB Norms are unavailable."


def theme_chart_share_unavailability_reason(
    snapshot: Mapping[str, Any] | None,
    availability_key: str,
) -> str:
    """Explain why chart-share/percentile Theme norms cannot be used."""
    legacy_reason = theme_snapshot_unavailability_reason_for_availability(snapshot, availability_key)
    if legacy_reason != "Theme DB Norms are unavailable.":
        return legacy_reason
    payload = snapshot if isinstance(snapshot, Mapping) else {}
    if int(payload.get(THEME_CHART_SHARE_SCHEMA_FIELD, 0) or 0) != THEME_CHART_SHARE_SCHEMA_VERSION:
        return "The selected DB Norms snapshot predates Theme chart-share percentiles."
    if not theme_chart_share_norms_for_availability(payload, availability_key):
        return "The selected DB Norms snapshot has no Theme chart-share percentile data for this chart."
    return "Theme chart-share DB Norms are unavailable."


def enrich_theme_snapshot_with_availability_baselines(
    payload: Mapping[str, Any],
    by_availability: Mapping[str, Mapping[str, float]],
    chart_counts: Mapping[str, int],
    *,
    extended_norms: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a snapshot payload carrying denominator-compatible Theme norms."""
    enriched = dict(payload)
    enriched[THEME_NORMS_AVAILABILITY_SCHEMA_FIELD] = THEME_NORMS_AVAILABILITY_SCHEMA_VERSION
    enriched[THEME_FAMILY_AVAILABILITY_ROWS_FIELD] = {
        str(availability_key): {
            str(family_key): float(value) for family_key, value in rows.items()
        }
        for availability_key, rows in sorted(by_availability.items())
    }
    enriched[THEME_FAMILY_AVAILABILITY_COUNTS_FIELD] = {
        str(availability_key): int(count)
        for availability_key, count in sorted(chart_counts.items())
    }

    if extended_norms:
        enriched[THEME_CHART_SHARE_SCHEMA_FIELD] = THEME_CHART_SHARE_SCHEMA_VERSION
        enriched[THEME_SUBTHEME_SHARE_AVERAGES_FIELD] = dict(
            extended_norms.get("subtheme_share_averages_by_availability", {})
        )
        enriched[THEME_SUBTHEME_SHARE_VALUES_FIELD] = dict(
            extended_norms.get("subtheme_share_values_by_availability", {})
        )
        enriched[THEME_FAMILY_SHARE_AVERAGES_FIELD] = dict(
            extended_norms.get("family_share_averages_by_availability", {})
        )
        enriched[THEME_FAMILY_SHARE_VALUES_FIELD] = dict(
            extended_norms.get("family_share_values_by_availability", {})
        )
        enriched[THEME_FACTOR_ACTIVATION_VALUES_FIELD] = dict(
            extended_norms.get("factor_activation_values_by_availability", {})
        )
    return enriched
