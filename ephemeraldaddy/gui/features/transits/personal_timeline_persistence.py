"""Persistence adapter for Personal Timeline's generated transit windows."""

from __future__ import annotations

import datetime
from types import ModuleType
from typing import Any

from ephemeraldaddy.gui.features.transits.cache import (
    PersonalTimelineDiskCache,
    personal_timeline_fingerprint,
)


PERSONAL_TIMELINE_CACHE_ALGORITHM_VERSION = 1


def _generation_config(core: ModuleType) -> dict[str, object]:
    """Describe every generation knob whose change must invalidate disk cache."""
    aspects = []
    for aspect in core.COMPOSITE_ASPECT_TYPES:
        aspects.append(
            {
                "name": str(aspect.name),
                "angle_deg": float(aspect.angle_deg),
                "orb_deg": min(
                    float(aspect.orb_deg),
                    float(core.PERSONAL_TRANSIT_MAX_ORB_DEG),
                ),
            }
        )
    return {
        "algorithm_version": PERSONAL_TIMELINE_CACHE_ALGORITHM_VERSION,
        "timeline_years": int(core.DEFAULT_TIMELINE_YEARS),
        "scan_step_days": int(core.DEFAULT_SCAN_STEP_DAYS),
        "boundary_refinement_steps": int(core._BOUNDARY_REFINEMENT_STEPS),
        "ephemeris_min_date": core.EPHEMERIS_MIN_DATE.isoformat(),
        "ephemeris_max_date": core.EPHEMERIS_MAX_DATE.isoformat(),
        "personal_transit_max_orb_deg": float(core.PERSONAL_TRANSIT_MAX_ORB_DEG),
        "transiting_bodies": list(core._timeline_transiting_bodies()),
        "aspects": aspects,
    }


def _cached_window(core: ModuleType, payload: dict[str, object], chart_uid: str) -> Any:
    transit_payload = payload.get("transit")
    if not isinstance(transit_payload, dict):
        raise ValueError("Cached Personal Timeline transit payload is malformed.")

    cached_uid = str(payload.get("chart_uid") or "").strip().upper()
    expected_uid = str(chart_uid or "").strip().upper()
    if cached_uid != expected_uid:
        raise ValueError("Cached Personal Timeline window belongs to another chart.")

    start = datetime.datetime.fromisoformat(str(payload["start"]))
    end = datetime.datetime.fromisoformat(str(payload["end"]))
    if start.tzinfo is None or end.tzinfo is None or end < start:
        raise ValueError("Cached Personal Timeline bounds are invalid.")

    transit = core.TimelineTransitDefinition(
        transiting_body=str(transit_payload["transiting_body"]),
        natal_body=str(transit_payload["natal_body"]),
        natal_longitude=float(transit_payload["natal_longitude"]),
        aspect_name=str(transit_payload["aspect_name"]),
        aspect_angle=float(transit_payload["aspect_angle"]),
        orb_deg=float(transit_payload["orb_deg"]),
    )
    return core.PersonalTimelineWindow(
        chart_uid=expected_uid,
        transit=transit,
        start=start,
        end=end,
        start_truncated=bool(payload.get("start_truncated", False)),
        end_truncated=bool(payload.get("end_truncated", False)),
    )


def _cache_state(widget: Any, core: ModuleType) -> tuple[PersonalTimelineDiskCache, str] | None:
    cache = getattr(widget, "_personal_timeline_disk_cache", None)
    fingerprint = getattr(widget, "_personal_timeline_cache_fingerprint", None)
    if isinstance(cache, PersonalTimelineDiskCache) and isinstance(fingerprint, str):
        return cache, fingerprint

    try:
        cache = PersonalTimelineDiskCache()
        fingerprint = personal_timeline_fingerprint(
            widget.chart_uid,
            widget.chart,
            _generation_config(core),
        )
    except Exception:
        return None

    widget._personal_timeline_disk_cache = cache
    widget._personal_timeline_cache_fingerprint = fingerprint
    return cache, fingerprint


def install_personal_timeline_persistence(core: ModuleType) -> None:
    """Add transparent permanent-cache behavior without changing generator semantics."""
    widget_type = core.PersonalTimelineWindowWidget
    if bool(getattr(widget_type, "_ephemeraldaddy_persistent_cache_installed", False)):
        return

    original_start_generation = widget_type._start_generation
    original_on_finished = widget_type._on_finished

    def _start_generation_with_cache(self: Any) -> None:
        state = _cache_state(self, core)
        if state is not None:
            cache, fingerprint = state
            payloads = cache.get(self.chart_uid, fingerprint)
            if payloads is not None:
                try:
                    windows = [
                        _cached_window(core, payload, self.chart_uid)
                        for payload in payloads
                    ]
                except Exception:
                    cache.invalidate(self.chart_uid)
                else:
                    self.progress_bar.setRange(0, 1)
                    self.progress_bar.setValue(1)
                    self._all_windows = windows
                    self.results_button.setEnabled(True)
                    self._rerender_filtered()
                    self.status_label.setText(
                        self.status_label.text()
                        + " Loaded from permanent per-chart cache."
                    )
                    return
        original_start_generation(self)

    def _on_finished_with_cache(self: Any, windows: object) -> None:
        thread = getattr(self, "_thread", None)
        interrupted = bool(
            thread is not None
            and callable(getattr(thread, "isInterruptionRequested", None))
            and thread.isInterruptionRequested()
        )
        original_on_finished(self, windows)
        if interrupted:
            return

        state = _cache_state(self, core)
        if state is None:
            return
        cache, fingerprint = state
        try:
            cache.put(self.chart_uid, fingerprint, self._all_windows)
        except Exception:
            # Cache persistence is an optimization. A write failure must never
            # turn a successfully generated timeline into a UI failure.
            return

    widget_type._start_generation = _start_generation_with_cache
    widget_type._on_finished = _on_finished_with_cache
    widget_type._ephemeraldaddy_persistent_cache_installed = True
