"""Background locality enrichment for saved coordinate points."""

from __future__ import annotations

import logging
from threading import Event, Lock, Thread

from PySide6.QtCore import QObject, Signal, Slot

from ephemeraldaddy.core import db
from ephemeraldaddy.io.geocode import locality_for_coordinates
from ephemeraldaddy.io.web_profile.pacing import paced_requests

logger = logging.getLogger(__name__)
_repair_lock = Lock()


class BirthplaceRepairController(QObject):
    changed = Signal(object)
    finished = Signal()

    def __init__(self, parent, on_changed):
        super().__init__(parent)
        self._cancelled = Event()
        self._attempted = set()
        self._running = False
        self._rerun = False
        self.changed.connect(on_changed)
        self.finished.connect(self._finished)
        parent.destroyed.connect(self._cancelled.set)

    def request(self):
        if self._cancelled.is_set():
            return
        if self._running:
            self._rerun = True
            return
        self._running = True
        # A daemon owns no Qt/native thread child of the closing window.
        Thread(target=self._run, name="birthplace-localities", daemon=True).start()

    def _emit_changed(self, uids):
        if not self._cancelled.is_set():
            self.changed.emit(uids)

    def _run(self):
        try:
            # Multiple database windows must not launch parallel repair batches.
            if _repair_lock.acquire(blocking=False):
                try:
                    with paced_requests(self._cancelled):
                        db.repair_birthplace_localities(
                            locality_for_coordinates,
                            cancel_event=self._cancelled, attempted=self._attempted,
                            on_changed=self._emit_changed,
                        )
                finally:
                    _repair_lock.release()
        except RuntimeError:
            # The QObject may have been deleted during an outstanding request.
            if not self._cancelled.is_set():
                logger.exception("Birthplace locality repair failed")
        except Exception:
            logger.exception("Birthplace locality repair failed")
        finally:
            if not self._cancelled.is_set():
                try:
                    self.finished.emit()
                except RuntimeError:
                    pass

    @Slot()
    def _finished(self):
        self._running = False
        if self._rerun:
            self._rerun = False
            self.request()
