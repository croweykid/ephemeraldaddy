from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtCore import QTime, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ephemeraldaddy.gui.features.chart_editor.segmented_time_edit import SegmentedTimeEdit


def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_segmented_time_edit_defaults_and_invalid_values_to_noon() -> None:
    _application()
    editor = SegmentedTimeEdit()

    assert editor.text() == "12:00"
    assert editor.time() == QTime(12, 0)

    editor.setTime(QTime())

    assert editor.text() == "12:00"
    assert editor.time() == QTime(12, 0)


def test_segmented_time_edit_normalizes_ranges_and_emits_once() -> None:
    _application()
    editor = SegmentedTimeEdit()
    emitted: list[QTime] = []
    editor.timeChanged.connect(emitted.append)
    editor.setText("29:99")

    editor._normalize_and_emit()
    editor._normalize_and_emit()

    assert editor.text() == "23:59"
    assert editor.time() == QTime(23, 59)
    assert emitted == [QTime(23, 59)]


def test_segmented_time_edit_skips_colon_during_arrow_navigation() -> None:
    _application()
    editor = SegmentedTimeEdit()
    editor.setCursorPosition(3)

    QTest.keyClick(editor, Qt.Key_Left)

    assert editor.cursorPosition() == 1

    editor.setCursorPosition(1)
    QTest.keyClick(editor, Qt.Key_Right)

    assert editor.cursorPosition() == 3
