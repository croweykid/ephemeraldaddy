"""Shared batch-edit helpers for the Database Manager panel."""

from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Any


ChartMutation = Callable[[Any, int], dict[str, Any] | None]
_BATCH_MUTATION_LOCK = RLock()


def apply_batch_chart_mutation(
    chart_ids: list[int] | set[int],
    *,
    load_chart: Callable[[int], Any],
    update_chart: Callable[..., Any],
    chart_cache: dict[int, Any],
    mutate_chart: ChartMutation,
    calculate_dominant_sign_weights: Callable[[Any], Any] | None = None,
    calculate_dominant_planet_weights: Callable[[Any], Any] | None = None,
    operation_name: str = "batch edit",
) -> set[int]:
    """Apply one mutation function across multiple charts and persist each update.

    The mutation callback can optionally return extra kwargs for ``update_chart``.
    """

    changed_ids: set[int] = set()
    normalized_ids = list(chart_ids)

    with _BATCH_MUTATION_LOCK:
        for chart_id in normalized_ids:
            try:
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
            except Exception as exc:  # pragma: no cover - UI handles and surfaces context
                raise RuntimeError(
                    f"{operation_name} failed while updating chart_id={chart_id}"
                ) from exc

    return changed_ids
