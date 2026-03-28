"""Shared batch-edit helpers for the Database Manager panel."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


ChartMutation = Callable[[Any, int], dict[str, Any] | None]


def apply_batch_chart_mutation(
    chart_ids: list[int] | set[int],
    *,
    load_chart: Callable[[int], Any],
    update_chart: Callable[..., Any],
    chart_cache: dict[int, Any],
    mutate_chart: ChartMutation,
    calculate_dominant_sign_weights: Callable[[Any], Any] | None = None,
    calculate_dominant_planet_weights: Callable[[Any], Any] | None = None,
) -> set[int]:
    """Apply one mutation function across multiple charts and persist each update.

    The mutation callback can optionally return extra kwargs for ``update_chart``.
    """

    changed_ids: set[int] = set()
    for chart_id in chart_ids:
        chart = load_chart(chart_id)
        update_kwargs = mutate_chart(chart, chart_id) or {}

        if (
            calculate_dominant_sign_weights is not None
            and calculate_dominant_planet_weights is not None
        ):
            chart.dominant_sign_weights = calculate_dominant_sign_weights(chart)
            chart.dominant_planet_weights = calculate_dominant_planet_weights(chart)

        update_chart(
            chart_id,
            chart,
            retcon_time_used=getattr(chart, "retcon_time_used", False),
            **update_kwargs,
        )
        chart_cache[chart_id] = chart
        changed_ids.add(chart_id)

    return changed_ids
