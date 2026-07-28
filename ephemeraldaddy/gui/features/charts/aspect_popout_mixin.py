"""Narrow compatibility mixin for owners of standard aspect popouts."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from ephemeraldaddy.gui.features.charts.popout_aspects import (
    build_popout_left_panel,
    collect_aspect_category_totals,
    collect_aspect_type_counts,
    draw_popout_aspect_distribution_chart,
    extract_aspect_weight,
    normalize_aspect_type,
)
from ephemeraldaddy.gui.icons import get_share_icon_path


class AspectPopoutMixin:
    """Expose the legacy owner-method API through one shared implementation."""

    def _normalize_aspect_type(self, raw_aspect: Any) -> str:
        return normalize_aspect_type(raw_aspect)

    def _extract_aspect_weight(self, aspect_entry: Any) -> float:
        return extract_aspect_weight(aspect_entry)

    def _collect_aspect_type_counts(
        self,
        aspect_entries: list[Any],
        *,
        weighted: bool = False,
        weighted_score_for_entry: Callable[[Any], float] | None = None,
    ) -> OrderedDict[str, float]:
        return collect_aspect_type_counts(
            aspect_entries,
            weighted=weighted,
            weighted_score_for_entry=weighted_score_for_entry,
        )

    def _collect_aspect_category_totals(
        self,
        aspect_counts: OrderedDict[str, float],
        *,
        categories: dict[str, dict[str, Any]],
    ) -> OrderedDict[str, float]:
        return collect_aspect_category_totals(aspect_counts, categories=categories)

    def _draw_popout_aspect_distribution_chart(self, analytics_ax: Any, **kwargs: Any) -> None:
        draw_popout_aspect_distribution_chart(analytics_ax, **kwargs)

    def _build_popout_left_panel(self, layout: Any, **kwargs: Any) -> Any:
        return build_popout_left_panel(
            layout,
            parent=self,
            get_share_icon_path=get_share_icon_path,
            **kwargs,
        )
