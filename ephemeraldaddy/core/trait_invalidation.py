"""Granular invalidation rules for Traits and Trait rankings.

The Trait subsystem must respond to semantic change categories rather than a
coarse "database changed" signal.  This module is deliberately pure so GUI,
cache, and persistence callers can share one contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ephemeraldaddy.core.chart_data_fields import (
    ASTRO_DATA_CATEGORY,
    CHART_INFO_STATUS_CATEGORY,
    NONASTRAL_DATA_CATEGORY,
)


@dataclass(frozen=True)
class TraitInvalidation:
    """The smallest Trait work made stale by one semantic change."""

    score_chart_uids: frozenset[str] = frozenset()
    reposition_chart_uids: frozenset[str] = frozenset()
    membership_chart_uids: frozenset[str] = frozenset()
    trait_names: frozenset[str] = frozenset()
    refresh_trait_ui: bool = False

    @property
    def has_trait_work(self) -> bool:
        return bool(
            self.score_chart_uids
            or self.reposition_chart_uids
            or self.membership_chart_uids
            or self.trait_names
            or self.refresh_trait_ui
        )


def _normalize_chart_uids(chart_uids: Iterable[object]) -> frozenset[str]:
    return frozenset(
        normalized
        for raw_uid in chart_uids
        if (normalized := str(raw_uid or "").strip().upper())
    )


def trait_invalidation_for_chart_change(
    category: str,
    chart_uids: Iterable[object],
) -> TraitInvalidation:
    """Return the exact Trait work implied by a chart-data category.

    ``astro_data`` invalidates only the changed chart scores and their positions.
    ``chart_info_status`` changes membership only and must reuse cached scores.
    ``nonastral_data`` has no Trait consequence whatsoever.
    """

    normalized_uids = _normalize_chart_uids(chart_uids)
    if category == NONASTRAL_DATA_CATEGORY:
        return TraitInvalidation()
    if category == ASTRO_DATA_CATEGORY:
        return TraitInvalidation(
            score_chart_uids=normalized_uids,
            reposition_chart_uids=normalized_uids,
            refresh_trait_ui=bool(normalized_uids),
        )
    if category == CHART_INFO_STATUS_CATEGORY:
        return TraitInvalidation(
            membership_chart_uids=normalized_uids,
            refresh_trait_ui=bool(normalized_uids),
        )
    raise ValueError(f"Unknown chart-data category: {category!r}")


def trait_definition_invalidation(
    trait_name: str,
    *,
    change_type: str,
) -> TraitInvalidation:
    """Return Trait work for one Trait-definition event.

    Definition changes make only that Trait's scores stale. Rename/archive/
    unarchive/delete events are presentation/availability operations and must not
    numerically rescore other Traits.
    """

    normalized_name = str(trait_name or "").strip()
    trait_names = frozenset({normalized_name}) if normalized_name else frozenset()
    if change_type == "definition_changed":
        return TraitInvalidation(
            trait_names=trait_names,
            refresh_trait_ui=bool(trait_names),
        )
    if change_type in {"renamed", "archived", "unarchived", "deleted"}:
        return TraitInvalidation(
            trait_names=trait_names,
            refresh_trait_ui=bool(trait_names),
        )
    raise ValueError(f"Unknown Trait change type: {change_type!r}")
