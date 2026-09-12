"""Final builder for reusable Similarities Analysis trait exports."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable, Mapping
from typing import Any

from ephemeraldaddy.gui.features.charts.similarities_export import (
    build_similarities_json_export_payload,
    similarity_delta_exceeds_export_standard_deviation_tier,
)

from .cohort_metadata import inject_trait_cohort_metadata


def _percentage_from_counts(count: object, total: int) -> float:
    if total <= 0:
        return 0.0
    try:
        value = max(0, int(count))
    except (TypeError, ValueError):
        value = 0
    return (value / total) * 100.0


def compact_gender_distribution_weights(
    gender_distribution: Mapping[str, Any] | None,
) -> OrderedDict[str, int] | None:
    """Reduce cohort gender metadata to reusable signed DB-norm weights.

    Gender follows the same export policy as Modal Dominance and the other
    Similarities factor buckets: retain only deviations beyond the standard-
    error tier, store the signed percentage-point delta rounded to an integer,
    and omit zero-weight categories. Raw counts and significance diagnostics
    remain available to the live Similarities UI but are not trait properties.
    """
    if gender_distribution is None:
        return None

    selected_counts = gender_distribution.get("counts")
    database_counts = gender_distribution.get("databaseCounts")
    if isinstance(selected_counts, Mapping) and isinstance(database_counts, Mapping):
        try:
            selected_total = int(gender_distribution.get("total") or 0)
        except (TypeError, ValueError):
            selected_total = 0
        try:
            database_total = int(gender_distribution.get("databaseTotal") or 0)
        except (TypeError, ValueError):
            database_total = 0
        if selected_total <= 0:
            selected_total = sum(
                max(0, int(value))
                for value in selected_counts.values()
                if isinstance(value, (int, float))
            )
        if database_total <= 0:
            database_total = sum(
                max(0, int(value))
                for value in database_counts.values()
                if isinstance(value, (int, float))
            )
        labels = sorted(set(selected_counts) | set(database_counts), key=lambda value: str(value).casefold())
        percentages = {
            str(label): (
                _percentage_from_counts(selected_counts.get(label, 0), selected_total),
                _percentage_from_counts(database_counts.get(label, 0), database_total),
            )
            for label in labels
        }
    else:
        selected_percentages = gender_distribution.get("percentages")
        database_percentages = gender_distribution.get("databasePercentages")
        if not isinstance(selected_percentages, Mapping) or not isinstance(database_percentages, Mapping):
            # Already-compact mappings remain valid when passed through this builder.
            compact = OrderedDict()
            for label, value in gender_distribution.items():
                try:
                    weight = int(value)
                except (TypeError, ValueError):
                    continue
                if weight:
                    compact[str(label)] = weight
            return compact
        try:
            selected_total = int(gender_distribution.get("total") or 0)
        except (TypeError, ValueError):
            selected_total = 0
        labels = sorted(
            set(selected_percentages) | set(database_percentages),
            key=lambda value: str(value).casefold(),
        )
        percentages = {}
        for label in labels:
            try:
                selection_percent = float(selected_percentages.get(label, 0.0))
                database_percent = float(database_percentages.get(label, 0.0))
            except (TypeError, ValueError):
                continue
            percentages[str(label)] = (selection_percent, database_percent)

    weighted = OrderedDict()
    for label, (selection_percent, database_percent) in percentages.items():
        if not similarity_delta_exceeds_export_standard_deviation_tier(
            selection_percent,
            database_percent,
            selected_total,
        ):
            continue
        weight = int(round(selection_percent - database_percent))
        if weight:
            weighted[label] = weight
    return weighted


def build_similarities_trait_export_payload(
    selection_name: str,
    export_sections: Any,
    *,
    sample_uids: Iterable[object] = (),
    gender_distribution: Mapping[str, Any] | None = None,
) -> OrderedDict:
    """Build a profile-shaped export with explicit source-sample metadata.

    The lower-level Similarities payload builder remains responsible for factor
    normalization. This final builder owns reusable Trait metadata so the file
    export path does not depend on replacing builder globals at runtime.
    Two-chart Dissimilarity bundles remain unchanged because the metadata
    injector deliberately ignores non-Trait bundles.
    """
    payload = build_similarities_json_export_payload(selection_name, export_sections)
    inject_trait_cohort_metadata(
        payload,
        selection_name,
        sample_uids=sample_uids,
        gender_distribution=compact_gender_distribution_weights(gender_distribution),
    )
    return payload
