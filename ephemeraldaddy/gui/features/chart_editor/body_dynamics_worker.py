"""Background calculation worker for Chart Editor Body Dynamics."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal, Slot

from ephemeraldaddy.core.chart import Chart

# The calculation remains in the legacy charts staging module until the shared
# metrics family is split by workflow; this worker is the only Chart Editor
# thread/lifecycle owner and does not duplicate that calculation.
from ephemeraldaddy.gui.features.charts.metrics import calculate_planet_dynamics_scores


class PlanetDynamicsWorker(QObject):
    """Compute Body Dynamics scores away from the GUI thread."""

    finished = Signal(str, tuple, object)
    failed = Signal(str, tuple, str)

    def __init__(
        self,
        request_id: str,
        signature: tuple[object, ...],
        chart: Chart,
    ) -> None:
        super().__init__()
        self._request_id = request_id
        self._signature = signature
        self._chart = chart

    @Slot()
    def run(self) -> None:
        try:
            if QThread.currentThread().isInterruptionRequested():
                return
            scores = calculate_planet_dynamics_scores(self._chart)
            self.finished.emit(self._request_id, self._signature, scores)
        except Exception as exc:  # pragma: no cover - defensive GUI worker path
            self.failed.emit(self._request_id, self._signature, str(exc))
