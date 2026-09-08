"""Pure cohort metadata helpers for Similarities Analysis.

This module owns non-astrological provenance attached to a Similarities trait
export.  The original ascribed cohort is deliberately separate from factors
that survive statistical filtering: a chart may have been part of the source
sample without contributing any retained factor.
"""

from __future__ import annotations

from collections import Counter, OrderedDict
from collections.abc import Iterable, Mapping
from typing import Any

from ephemeraldaddy.gui.features.charts.statistical_significance import (
    SIGNIFICANCE_CORRECTION_DEFAULT,
    compute_proportion_significance_results,
    normalize_significance_correction,
)


def normalize_chart_uid(value: object) -> str:
    """Return a canonical permanent chart UID for provenance comparisons."""
    return str(value or "").strip().upper()


def normalize_gender_label(value: object) -> str:
    """Return a stable display/export label while preserving user categories."""
    return " ".join(str(value or "").strip().split())


def chart_uids_from_mapping(uid_map: Mapping[object, object]) -> list[str]:
    """Return unique permanent UIDs without exposing mutable chart names."""
    return sorted(
        {
            uid
            for raw_uid in uid_map.values()
            if (uid := normalize_chart_uid(raw_uid))
        }
    )


def gender_counts(charts: Iterable[Any]) -> OrderedDict[str, int]:
    """Count known gender labels with the same one-chart/one-observation model.

    Similarities Analysis factor prevalence is chart-count based.  Gender uses
    the same denominator policy: each chart with a populated gender contributes
    one observation; missing gender is omitted rather than guessed.
    """
    counts: Counter[str] = Counter()
    for chart in charts:
        if chart is None:
            continue
        label = normalize_gender_label(getattr(chart, "gender", None))
        if label:
            counts[label] += 1
    return OrderedDict(sorted(counts.items(), key=lambda item: item[0].casefold()))


def _percentages(counts: Mapping[str, int]) -> OrderedDict[str, float]:
    total = sum(max(0, int(value)) for value in counts.values())
    if total <= 0:
        return OrderedDict()
    return OrderedDict(
        (label, round((max(0, int(value)) / total) * 100.0, 1))
        for label, value in counts.items()
    )


def build_gender_distribution(
    selected_charts: Iterable[Any],
    database_charts: Iterable[Any],
    *,
    correction: object = SIGNIFICANCE_CORRECTION_DEFAULT,
) -> OrderedDict[str, Any] | None:
    """Build structured selected-vs-database gender metadata.

    Returns ``None`` when the selected cohort has no known gender data.  The
    exported structure includes the raw counts needed to re-evaluate a different
    significance policy later rather than freezing only a rendered percentage.
    """
    selected_counts = gender_counts(selected_charts)
    if not selected_counts:
        return None
    database_counts = gender_counts(database_charts)
    labels = sorted(
        set(selected_counts) | set(database_counts),
        key=str.casefold,
    )
    selected_vector = [selected_counts.get(label, 0) for label in labels]
    database_vector = [database_counts.get(label, 0) for label in labels]
    selected_total = sum(selected_vector)
    database_total = sum(database_vector)
    normalized_correction = normalize_significance_correction(correction)

    significant_categories: list[str] = []
    results_by_label: OrderedDict[str, Any] = OrderedDict()
    if database_total > 0:
        results = compute_proportion_significance_results(
            selection_counts=selected_vector,
            database_counts=database_vector,
            loaded_charts=selected_total,
            correction=normalized_correction,
            selection_total=selected_total,
            database_total=database_total,
        )
        for label, result in zip(labels, results):
            significant = bool(result.is_significant)
            if significant:
                significant_categories.append(label)
            results_by_label[label] = OrderedDict(
                [
                    ("zScore", None if result.z_score is None else round(float(result.z_score), 4)),
                    (
                        "pValue",
                        None if result.p_value is None else round(float(result.p_value), 8),
                    ),
                    (
                        "adjustedPValue",
                        None
                        if result.adjusted_p_value is None
                        else round(float(result.adjusted_p_value), 8),
                    ),
                    ("band", result.band),
                    ("significant", significant),
                ]
            )

    selected_complete = OrderedDict((label, selected_counts.get(label, 0)) for label in labels)
    database_complete = OrderedDict((label, database_counts.get(label, 0)) for label in labels)
    return OrderedDict(
        [
            ("counts", selected_complete),
            ("total", selected_total),
            ("percentages", _percentages(selected_complete)),
            ("databaseCounts", database_complete),
            ("databaseTotal", database_total),
            ("databasePercentages", _percentages(database_complete)),
            ("significanceCorrection", normalized_correction),
            ("significance", results_by_label),
            ("statisticallySignificant", bool(significant_categories)),
            ("significantCategories", significant_categories),
        ]
    )


def inject_trait_cohort_metadata(
    payload: Mapping[str, Any],
    selection_name: str,
    *,
    chart_uids: Iterable[object],
    gender_distribution: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    """Attach provenance to a normal Similarities trait profile in-place.

    Dissimilarity bundles are intentionally left alone: they are descriptive
    two-chart bundles rather than reusable population trait profiles.
    """
    profile = payload.get(selection_name)
    if not isinstance(profile, dict) or "model" not in profile:
        return payload
    profile["chartUIDs"] = sorted(
        {
            uid
            for raw_uid in chart_uids
            if (uid := normalize_chart_uid(raw_uid))
        }
    )
    if gender_distribution:
        profile["genderDistribution"] = OrderedDict(gender_distribution)
    return payload


def chart_uid_is_ascribed(profile: Mapping[str, Any], chart_uid: object) -> bool:
    """Return whether a chart UID belongs to the trait's original ascribed cohort."""
    target = normalize_chart_uid(chart_uid)
    if not target:
        return False
    raw_uids = profile.get("chartUIDs", ())
    if not isinstance(raw_uids, (list, tuple, set, frozenset)):
        return False
    return target in {normalize_chart_uid(value) for value in raw_uids if normalize_chart_uid(value)}
