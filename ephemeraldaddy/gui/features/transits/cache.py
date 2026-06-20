"""Cache helpers for expensive Transit View window calculations."""

from __future__ import annotations

import datetime as _dt
from collections import OrderedDict
from typing import Any

from ephemeraldaddy.core.composite import TRANSIT_ASPECT_RULES
from ephemeraldaddy.gui.features.retcon.transit_window import TRANSIT_WINDOW_CACHE_LIMIT


class TransitWindowCache:
    """Owns transit-window cache keys, cached payloads, and metrics."""

    def __init__(self, *, limit: int = TRANSIT_WINDOW_CACHE_LIMIT) -> None:
        self.limit = int(limit)
        self.results: OrderedDict[tuple[object, ...], dict[str, object]] = OrderedDict()
        self.metrics: dict[str, int | float] = {
            "cache_hits": 0,
            "cache_misses": 0,
            "inflight_dedupes": 0,
            "completed_requests": 0,
        }

    def build_key(
        self,
        *,
        mode: str,
        hit_obj: Any,
        chart_dt: _dt.datetime,
        transit_location: tuple[float, float],
        mode_rules: dict[str, Any],
        scan_config: Any,
    ) -> tuple[object, ...]:
        chart_dt_utc = (
            chart_dt.astimezone(_dt.timezone.utc)
            if chart_dt.tzinfo
            else chart_dt.replace(tzinfo=_dt.timezone.utc)
        )
        rules = mode_rules.get(mode, TRANSIT_ASPECT_RULES)
        return (
            mode,
            hit_obj.a.name,
            hit_obj.aspect,
            hit_obj.b.name,
            chart_dt_utc.isoformat(),
            round(float(transit_location[0]), 4),
            round(float(transit_location[1]), 4),
            tuple(
                (asp.name, float(asp.angle_deg), float(asp.orb_deg))
                for asp in rules.aspect_types
            ),
            float(scan_config.scan_step_hours),
            float(scan_config.scan_precision_minutes),
        )

    def get(self, cache_key: tuple[object, ...]) -> dict[str, object] | None:
        cached = self.results.get(cache_key)
        if cached is None:
            self.metrics["cache_misses"] = int(self.metrics["cache_misses"]) + 1
            return None
        self.metrics["cache_hits"] = int(self.metrics["cache_hits"]) + 1
        self.results.move_to_end(cache_key)
        return dict(cached)

    def put(self, cache_key: tuple[object, ...], payload: dict[str, object]) -> None:
        self.results[cache_key] = dict(payload)
        self.results.move_to_end(cache_key)
        self.metrics["completed_requests"] = int(self.metrics["completed_requests"]) + 1
        while len(self.results) > self.limit:
            self.results.popitem(last=False)

    def record_inflight_dedupe(self) -> None:
        self.metrics["inflight_dedupes"] = int(self.metrics["inflight_dedupes"]) + 1
