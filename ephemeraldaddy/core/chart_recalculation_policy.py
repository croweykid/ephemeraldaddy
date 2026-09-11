"""Pure policy for classifying the downstream impact of chart edits.

This module deliberately has no Qt dependencies.  Persistence and GUI layers can
use the same classification without making a window the owner of calculation
policy.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.core.chart_data_fields import astro_data_recalculation_token
from ephemeraldaddy.core.db import SOURCE_HYPOTHETICAL, normalize_chart_type


def _normalized_tags(tags: Iterable[object] | None) -> tuple[str, ...]:
    """Return the case-insensitive, order-preserving tag identity used on save."""
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in tags or ():
        tag = str(raw_value or "").strip()
        key = tag.casefold()
        if not tag or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return tuple(normalized)


def _chart_type(chart: object) -> str:
    return normalize_chart_type(
        getattr(chart, "chart_type", None) or getattr(chart, "source", None)
    )


def _is_non_aggregable(chart: object) -> bool:
    chart_type = getattr(chart, "chart_type", None) or getattr(chart, "source", None)
    return bool(getattr(chart, "is_placeholder", False)) or (
        str(chart_type or "").strip().lower() == "placeholder"
        or normalize_chart_type(chart_type) == SOURCE_HYPOTHETICAL
    )


class ChartRecalculationPolicy:
    """Classify saved chart changes without reading widgets or mutable UI state."""

    @staticmethod
    def astro_data_token(
        chart: object | None,
        *,
        birth_place: str | None = None,
    ) -> tuple[Any, ...]:
        """Return the authoritative calculation-input token for ``chart``."""
        return astro_data_recalculation_token(
            chart,
            birth_place=birth_place,
            chart_uses_houses_value=(
                bool(chart_uses_houses(chart)) if chart is not None else None
            ),
        )

    @classmethod
    def changed_fields(
        cls,
        previous_chart: object | None,
        chart: object,
        *,
        birth_place: str | None = None,
    ) -> set[str] | None:
        """Return refresh-impact field names, or ``None`` for a newly saved chart."""
        if previous_chart is None:
            return None

        changed_fields: set[str] = set()
        if cls.astro_data_token(previous_chart) != cls.astro_data_token(
            chart, birth_place=birth_place
        ):
            changed_fields.add("birth_data")
        if _chart_type(previous_chart) != _chart_type(chart):
            changed_fields.add("chart_type")
        if _is_non_aggregable(previous_chart) != _is_non_aggregable(chart):
            changed_fields.add("aggregation_scope")

        comparisons: dict[str, Callable[[object], object]] = {
            "name": lambda value: str(getattr(value, "name", "") or "").strip(),
            "alias": lambda value: str(getattr(value, "alias", "") or "").strip(),
            "sentiments": lambda value: tuple(
                sorted(
                    str(item).casefold()
                    for item in (getattr(value, "sentiments", []) or [])
                )
            ),
            "relationship_types": lambda value: tuple(
                sorted(
                    str(item).casefold()
                    for item in (getattr(value, "relationship_types", []) or [])
                )
            ),
            "tags": lambda value: _normalized_tags(getattr(value, "tags", []) or []),
            "gender": lambda value: getattr(value, "gender", None),
            "alignment": lambda value: getattr(value, "alignment_score", None),
            "positive_sentiment_intensity": lambda value: getattr(
                value, "positive_sentiment_intensity", None
            ),
            "negative_sentiment_intensity": lambda value: getattr(
                value, "negative_sentiment_intensity", None
            ),
            "familiarity": lambda value: getattr(value, "familiarity", None),
            "matched_expectations": lambda value: getattr(
                value, "matched_expectations", None
            ),
        }
        for field, getter in comparisons.items():
            if getter(previous_chart) != getter(chart):
                changed_fields.add(field)
        return changed_fields
