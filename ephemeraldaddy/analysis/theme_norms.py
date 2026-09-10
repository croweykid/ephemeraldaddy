"""Availability-stratified population norms for semantic Theme prominence.

Theme prominence intentionally omits factor categories that cannot be known for
one chart (for example houses and Human Design on an unknown-time chart).  That
makes the chart-level score more honest, but it also means two charts can have
different score denominators.  Population comparisons must therefore stay
inside the same data-availability stratum instead of averaging incompatible
scales together.

This module reuses ``theme_prominence``'s private activation/category helpers so
stratification and snapshot lookup follow the exact same availability decisions
as the production scorer.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from ephemeraldaddy.analysis import theme_prominence as prominence


THEME_NORMS_AVAILABILITY_SCHEMA_VERSION = 1
THEME_FAMILY_AVAILABILITY_ROWS_FIELD = "theme_family_raw_averages_by_availability"
THEME_FAMILY_AVAILABILITY_COUNTS_FIELD = "theme_family_availability_counts"
THEME_NORMS_AVAILABILITY_SCHEMA_FIELD = "theme_family_availability_schema_version"


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
    """Return subtheme and family scores without rebuilding ``context``."""
    subthemes = calculate_theme_subtheme_scores_from_context(context)
    families = prominence.calculate_theme_family_scores(
        None,
        subtheme_scores=subthemes,
    )
    return subthemes, families


def _averages_from_totals(
    totals: Mapping[str, float],
    counts: Mapping[str, int],
) -> dict[str, float]:
    return {
        family_key: float(totals[family_key]) / float(counts[family_key])
        for family_key in prominence.THEME_FAMILIES
        if int(counts.get(family_key, 0)) > 0
    }


def calculate_database_theme_family_baselines(
    charts: Sequence[Any],
) -> tuple[dict[str, float], dict[str, dict[str, float]], dict[str, int]]:
    """Return legacy aggregate + availability-stratified Theme family means.

    The first return value exists only so the current snapshot builder can keep
    its pre-existing completeness check/legacy field while this PR remains
    stacked.  Runtime ``vs DB`` comparisons must use the second value.
    """
    overall_totals = {family_key: 0.0 for family_key in prominence.THEME_FAMILIES}
    overall_counts = {family_key: 0 for family_key in prominence.THEME_FAMILIES}
    stratum_totals: dict[str, dict[str, float]] = {}
    stratum_counts: dict[str, dict[str, int]] = {}
    stratum_chart_counts: dict[str, int] = {}

    for chart in charts:
        try:
            context = prominence._activation_context(chart)
            _subthemes, family_scores = calculate_theme_scores_from_context(context)
            availability_key = theme_availability_key_from_context(context)
        except Exception:
            continue

        stratum_chart_counts[availability_key] = (
            int(stratum_chart_counts.get(availability_key, 0)) + 1
        )
        totals = stratum_totals.setdefault(
            availability_key,
            {family_key: 0.0 for family_key in prominence.THEME_FAMILIES},
        )
        counts = stratum_counts.setdefault(
            availability_key,
            {family_key: 0 for family_key in prominence.THEME_FAMILIES},
        )

        for family_key, raw_value in family_scores.items():
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value):
                continue
            overall_totals[family_key] += value
            overall_counts[family_key] += 1
            totals[family_key] += value
            counts[family_key] += 1

    overall = _averages_from_totals(overall_totals, overall_counts)
    by_availability = {
        availability_key: _averages_from_totals(
            stratum_totals[availability_key],
            stratum_counts[availability_key],
        )
        for availability_key in sorted(stratum_totals)
    }
    return overall, by_availability, stratum_chart_counts


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
    if (
        int(payload.get(THEME_NORMS_AVAILABILITY_SCHEMA_FIELD, 0) or 0)
        != THEME_NORMS_AVAILABILITY_SCHEMA_VERSION
    ):
        return (
            "The selected DB Norms snapshot predates availability-stratified "
            "Theme baselines."
        )
    rows_by_availability = payload.get(THEME_FAMILY_AVAILABILITY_ROWS_FIELD, {})
    if not isinstance(rows_by_availability, Mapping):
        return "The selected DB Norms snapshot contains invalid Theme availability baselines."
    rows = rows_by_availability.get(str(availability_key))
    if not isinstance(rows, Mapping):
        return (
            "The selected DB Norms snapshot has no Theme baseline for this chart's "
            "data-availability profile."
        )
    if any(
        not isinstance(rows.get(key), (int, float))
        or not math.isfinite(float(rows.get(key)))
        for key in prominence.THEME_FAMILIES
    ):
        return "The selected DB Norms snapshot contains incomplete Theme baselines for this data-availability profile."
    return "Theme DB Norms are unavailable."


def enrich_theme_snapshot_with_availability_baselines(
    payload: Mapping[str, Any],
    by_availability: Mapping[str, Mapping[str, float]],
    chart_counts: Mapping[str, int],
) -> dict[str, Any]:
    """Return a snapshot payload carrying denominator-compatible Theme norms."""
    enriched = dict(payload)
    enriched[THEME_NORMS_AVAILABILITY_SCHEMA_FIELD] = (
        THEME_NORMS_AVAILABILITY_SCHEMA_VERSION
    )
    enriched[THEME_FAMILY_AVAILABILITY_ROWS_FIELD] = {
        str(availability_key): {
            str(family_key): float(value)
            for family_key, value in rows.items()
        }
        for availability_key, rows in sorted(by_availability.items())
    }
    enriched[THEME_FAMILY_AVAILABILITY_COUNTS_FIELD] = {
        str(availability_key): int(count)
        for availability_key, count in sorted(chart_counts.items())
    }
    return enriched
