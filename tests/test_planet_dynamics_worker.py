from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace


class _BoundSignal:
    def __init__(self) -> None:
        self.emissions: list[tuple[object, ...]] = []

    def emit(self, *args: object) -> None:
        self.emissions.append(args)


class _Signal:
    def __init__(self, *_types: object) -> None:
        self._name = ""

    def __set_name__(self, _owner: type, name: str) -> None:
        self._name = name

    def __get__(self, instance: object, _owner: type) -> object:
        if instance is None:
            return self
        signals = instance.__dict__.setdefault("_test_signals", {})
        return signals.setdefault(self._name, _BoundSignal())


class _QObject:
    pass


class _Thread:
    interrupted = False

    @classmethod
    def currentThread(cls):
        return SimpleNamespace(isInterruptionRequested=lambda: cls.interrupted)


def _slot(*_types: object):
    return lambda function: function


qt_core = ModuleType("PySide6.QtCore")
qt_core.QObject = _QObject
qt_core.QThread = _Thread
qt_core.Signal = _Signal
qt_core.Slot = _slot
pyside = ModuleType("PySide6")
pyside.QtCore = qt_core
sys.modules["PySide6"] = pyside
sys.modules["PySide6.QtCore"] = qt_core

chart_module = ModuleType("ephemeraldaddy.core.chart")
chart_module.Chart = object
sys.modules["ephemeraldaddy.core.chart"] = chart_module

metrics_module = ModuleType("ephemeraldaddy.gui.features.charts.metrics")
metrics_module.calculate_planet_dynamics_scores = lambda chart: {"chart": chart}
sys.modules["ephemeraldaddy.gui.features.charts.metrics"] = metrics_module

from ephemeraldaddy.gui.features.chart_editor import body_dynamics_worker
from ephemeraldaddy.gui.features.chart_editor.body_dynamics_worker import (
    PlanetDynamicsWorker,
)


def test_worker_emits_calculated_scores_with_request_identity(monkeypatch):
    chart = object()
    signature = ("signature",)
    monkeypatch.setattr(
        body_dynamics_worker,
        "calculate_planet_dynamics_scores",
        lambda received_chart: {"score": received_chart is chart},
    )
    worker = PlanetDynamicsWorker("request", signature, chart)

    worker.run()

    assert worker.finished.emissions == [
        ("request", signature, {"score": True})
    ]
    assert worker.failed.emissions == []


def test_worker_skips_calculation_after_interruption(monkeypatch):
    monkeypatch.setattr(_Thread, "interrupted", True)
    monkeypatch.setattr(
        body_dynamics_worker,
        "calculate_planet_dynamics_scores",
        lambda _chart: (_ for _ in ()).throw(AssertionError("must not calculate")),
    )
    worker = PlanetDynamicsWorker("request", (), object())

    worker.run()

    assert worker.finished.emissions == []
    assert worker.failed.emissions == []


def test_worker_reports_calculation_failure(monkeypatch):
    monkeypatch.setattr(_Thread, "interrupted", False)

    def fail(_chart: object) -> object:
        raise ValueError("invalid dynamics")

    monkeypatch.setattr(body_dynamics_worker, "calculate_planet_dynamics_scores", fail)
    worker = PlanetDynamicsWorker("request", (1, 2), object())

    worker.run()

    assert worker.finished.emissions == []
    assert worker.failed.emissions == [
        ("request", (1, 2), "invalid dynamics")
    ]
