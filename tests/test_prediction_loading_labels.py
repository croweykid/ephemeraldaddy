import pytest


pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtWidgets import QApplication, QLabel
from shiboken6 import delete

from ephemeraldaddy.gui.features.charts.prediction_loading_labels import (
    start_prediction_loading_ellipsis,
    stop_prediction_loading_ellipsis,
)


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


def test_ellipsis_restart_recovers_from_qt_deleted_timer(qt_app):
    label = QLabel()
    start_prediction_loading_ellipsis(label, "Loading traits")
    stale_timer = label._ephemeraldaddy_loading_ellipsis_timer
    delete(stale_timer)

    start_prediction_loading_ellipsis(label, "Loading traits")

    replacement = label._ephemeraldaddy_loading_ellipsis_timer
    assert replacement is not stale_timer
    assert replacement.isActive()
    stop_prediction_loading_ellipsis(label)


def test_stop_ellipsis_clears_timer_and_state(qt_app):
    label = QLabel()
    start_prediction_loading_ellipsis(label, "Loading traits")

    stop_prediction_loading_ellipsis(label)

    assert not hasattr(label, "_ephemeraldaddy_loading_ellipsis_timer")
    assert not hasattr(label, "_ephemeraldaddy_loading_ellipsis_state")


def test_obsolete_queued_tick_does_not_stop_replacement_timer(qt_app):
    label = QLabel()
    start_prediction_loading_ellipsis(label, "First load")
    obsolete_timer = label._ephemeraldaddy_loading_ellipsis_timer
    start_prediction_loading_ellipsis(label, "Replacement load")
    replacement_timer = label._ephemeraldaddy_loading_ellipsis_timer

    obsolete_timer.timeout.emit()

    assert label._ephemeraldaddy_loading_ellipsis_timer is replacement_timer
    assert replacement_timer.isActive()
    stop_prediction_loading_ellipsis(label)
