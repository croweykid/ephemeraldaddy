from __future__ import annotations

import datetime
import threading
from typing import Callable

from PySide6.QtCore import QObject, Signal


class SwissEphemerisPrefetchWorker(QObject):
    finished = Signal(bool, str)

    def __init__(
        self,
        offline_mode_checker: Callable[[], bool] | None = None,
        prefetch_fn: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self._offline_mode_checker = offline_mode_checker
        self._prefetch_fn = prefetch_fn

    def _resolve_offline_mode_checker(self) -> Callable[[], bool]:
        if self._offline_mode_checker is None:
            from ephemeraldaddy.core.ephemeris import is_offline_mode

            self._offline_mode_checker = is_offline_mode
        return self._offline_mode_checker

    def _resolve_prefetch_fn(self) -> Callable[[], None]:
        if self._prefetch_fn is None:
            from ephemeraldaddy.core.ephemeris import prepare_swiss_ephemeris_data

            self._prefetch_fn = prepare_swiss_ephemeris_data
        return self._prefetch_fn

    def run(self) -> None:
        if self._resolve_offline_mode_checker()():
            self.finished.emit(True, "Skipped Swiss Ephemeris prefetch (offline mode).")
            return
        try:
            self._resolve_prefetch_fn()()
        except Exception as exc:
            self.finished.emit(False, str(exc))
            return
        self.finished.emit(True, "Swiss Ephemeris prefetch complete.")


class RetconSearchWorker(QObject):
    progress = Signal(int, int)
    match_found = Signal(dict)
    finished = Signal(list)
    failed = Signal(str)

    def __init__(
        self,
        criteria: dict[str, str],
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
        lat: float,
        lon: float,
        step_minutes: int,
        max_results: int,
        search_fn: Callable[..., list[dict]] | None = None,
    ) -> None:
        super().__init__()
        self._criteria = criteria
        self._start_dt = start_dt
        self._end_dt = end_dt
        self._lat = lat
        self._lon = lon
        self._step_minutes = step_minutes
        self._max_results = max_results
        self._search_fn = search_fn
        self._cancel_event = threading.Event()

    def _resolve_search_fn(self) -> Callable[..., list[dict]]:
        if self._search_fn is None:
            from ephemeraldaddy.core.retcon import search_retcon_candidates

            self._search_fn = search_retcon_candidates
        return self._search_fn

    def cancel(self) -> None:
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def run(self) -> None:
        try:
            matches = self._resolve_search_fn()(
                self._criteria,
                self._start_dt,
                self._end_dt,
                self._lat,
                self._lon,
                step_minutes=self._step_minutes,
                max_results=self._max_results,
                progress_cb=self.progress.emit,
                match_cb=self.match_found.emit,
                should_cancel_cb=self._cancel_event.is_set,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(matches)


class AstrothemeImportWorker(QObject):
    progress = Signal(str)
    finished = Signal(dict)
    failed = Signal(str)
    canceled = Signal()

    def __init__(self, query: str) -> None:
        super().__init__()
        self._query = (query or "").strip()
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def run(self) -> None:
        if self._cancel_event.is_set():
            self.canceled.emit()
            return

        from ephemeraldaddy.gui.astrotheme_search import (
            parse_astrotheme_profile,
            search_astrotheme_profile_url,
        )

        raw_query = self._query
        try:
            if raw_query.lower().startswith(("http://", "https://")):
                resolved_url = raw_query
            else:
                self.progress.emit("Searching Astrotheme profiles…")
                resolved_url = search_astrotheme_profile_url(raw_query)
                if not resolved_url:
                    raise ValueError("No matching Astrotheme profile was found.")
            if self._cancel_event.is_set():
                self.canceled.emit()
                return
            self.progress.emit("Parsing Astrotheme profile…")
            profile_data = parse_astrotheme_profile(resolved_url)
            if self._cancel_event.is_set():
                self.canceled.emit()
                return
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        self.finished.emit(profile_data)
