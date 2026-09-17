from __future__ import annotations

import pytest

try:
    from PySide6.QtCore import QItemSelectionModel, Qt
    from PySide6.QtWidgets import QApplication, QAbstractItemView, QListWidgetItem
except ImportError as exc:  # pragma: no cover - depends on the CI Qt runtime
    pytest.skip(f"Qt runtime unavailable: {exc}", allow_module_level=True)

from ephemeraldaddy.gui.features.database_view.chart_list import (
    ChartListWidget,
    capture_chart_roster_view_state,
    restore_chart_roster_view_state,
)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _fill(widget: ChartListWidget, uids: list[str]) -> None:
    widget.clear()
    for uid in uids:
        item = QListWidgetItem(uid)
        item.setData(Qt.UserRole, uid)
        widget.addItem(item)


def test_roster_state_restores_selection_current_and_viewport(app):
    widget = ChartListWidget()
    widget.resize(260, 120)
    widget.setSelectionMode(QAbstractItemView.MultiSelection)
    uids = [f"UID-{index:02d}" for index in range(30)]
    _fill(widget, uids)
    widget.show()
    app.processEvents()
    widget.item(9).setSelected(True)
    widget.item(14).setSelected(True)
    widget.setCurrentItem(widget.item(14), QItemSelectionModel.NoUpdate)
    widget.scrollToItem(widget.item(9), QAbstractItemView.PositionAtTop)
    app.processEvents()

    state = capture_chart_roster_view_state(widget)
    _fill(widget, uids)
    restore_chart_roster_view_state(widget, state)
    app.processEvents()

    assert {item.data(Qt.UserRole) for item in widget.selectedItems()} == {"UID-09", "UID-14"}
    assert widget.currentItem().data(Qt.UserRole) == "UID-14"
    assert widget.itemAt(0, 0).data(Qt.UserRole) == "UID-09"


def test_roster_state_uses_nearest_surviving_anchor(app):
    widget = ChartListWidget()
    widget.resize(260, 120)
    uids = [f"UID-{index:02d}" for index in range(20)]
    _fill(widget, uids)
    widget.show()
    app.processEvents()
    widget.scrollToItem(widget.item(8), QAbstractItemView.PositionAtTop)
    app.processEvents()
    state = capture_chart_roster_view_state(widget)

    _fill(widget, [uid for uid in uids if uid != "UID-08"])
    restore_chart_roster_view_state(widget, state)
    app.processEvents()

    assert widget.itemAt(0, 0).data(Qt.UserRole) == "UID-09"
