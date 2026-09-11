from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QListWidgetItem

from ephemeraldaddy.gui.features.charts.delegates import CHART_ROW_OPEN_FEEDBACK_ROLE
from ephemeraldaddy.gui.features.database_view.chart_list import ChartListWidget
from ephemeraldaddy.gui.features.database_view.collections import CHART_UIDS_MIME_TYPE


def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_chart_list_letter_navigation_uses_raw_name_and_wraps() -> None:
    _application()
    chart_list = ChartListWidget()
    ada = QListWidgetItem("#2 Ada")
    ada.setData(Qt.UserRole + 1, {"raw_name": "Ada"})
    bea = QListWidgetItem("#1 Bea")
    bea.setData(Qt.UserRole + 1, {"raw_name": "Bea"})
    chart_list.addItem(bea)
    chart_list.addItem(ada)
    chart_list.setCurrentItem(ada)

    QTest.keyClick(chart_list, Qt.Key_A)

    assert chart_list.currentItem() is ada
    assert ada.isSelected()


def test_chart_list_drag_payload_contains_chart_uids_not_row_ids() -> None:
    _application()
    chart_list = ChartListWidget()
    item = QListWidgetItem("Ada")
    item.setData(Qt.UserRole, 42)
    item.setData(Qt.UserRole + 2, "chart-uid-1")
    chart_list.addItem(item)

    mime_data = chart_list.mimeData([item])

    assert bytes(mime_data.data(CHART_UIDS_MIME_TYPE)) == b"CHART-UID-1"


def test_chart_list_open_feedback_is_cleared_after_final_step() -> None:
    _application()
    chart_list = ChartListWidget()
    item = QListWidgetItem("Ada")
    chart_list.addItem(item)

    chart_list.start_open_feedback(item)
    for _ in range(chart_list._open_feedback_steps):
        chart_list._advance_open_feedback()

    assert item.data(CHART_ROW_OPEN_FEEDBACK_ROLE) is None
    assert chart_list._open_feedback_item is None
    assert not chart_list._open_feedback_timer.isActive()
