import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.gui.appwide_input import install_appwide_input_focus_policy


def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_enter_submits_focused_line_edit_instead_of_other_panel_shortcut():
    app = _application()
    install_appwide_input_focus_policy(app)
    window = QWidget()
    layout = QVBoxLayout(window)
    search_input = QLineEdit()
    other_panel = QWidget()
    layout.addWidget(search_input)
    layout.addWidget(other_panel)

    submissions: list[str] = []
    stolen_shortcuts: list[bool] = []
    search_input.returnPressed.connect(lambda: submissions.append(search_input.text()))
    shortcut = QShortcut(QKeySequence("Return"), window)
    shortcut.setContext(Qt.WidgetWithChildrenShortcut)
    shortcut.activated.connect(lambda: stolen_shortcuts.append(True))

    window.show()
    search_input.setText("Ada Lovelace")
    search_input.setFocus()
    QTest.keyClick(search_input, Qt.Key_Return)

    assert submissions == ["Ada Lovelace"]
    assert stolen_shortcuts == []
    window.close()


def test_enter_remains_a_newline_in_multiline_editor():
    app = _application()
    install_appwide_input_focus_policy(app)
    window = QWidget()
    layout = QVBoxLayout(window)
    editor = QTextEdit()
    layout.addWidget(editor)
    window.show()
    editor.setFocus()
    editor.setPlainText("first line")
    editor.moveCursor(editor.textCursor().MoveOperation.End)
    QTest.keyClick(editor, Qt.Key_Return)

    assert editor.toPlainText() == "first line\n"
    window.close()


def test_modified_enter_shortcut_is_not_reserved_for_line_edit():
    app = _application()
    install_appwide_input_focus_policy(app)
    window = QWidget()
    layout = QVBoxLayout(window)
    search_input = QLineEdit()
    layout.addWidget(search_input)
    shortcut_hits: list[bool] = []
    shortcut = QShortcut(QKeySequence("Ctrl+Return"), window)
    shortcut.setContext(Qt.WidgetWithChildrenShortcut)
    shortcut.activated.connect(lambda: shortcut_hits.append(True))

    window.show()
    search_input.setFocus()
    QTest.keyClick(search_input, Qt.Key_Return, Qt.ControlModifier)

    assert shortcut_hits == [True]
    window.close()


def test_batch_editor_enter_bindings_are_scoped_and_use_native_submit_signals():
    source = (
        Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py"
    ).read_text()
    method_start = source.index("    def _bind_batch_enter_apply(")
    method_end = source.index("    def _set_batch_metric_spin_state(", method_start)

    assert source[method_start:method_end].count(
        "shortcut.setContext(Qt.WidgetWithChildrenShortcut)"
    ) == 1
    assert source[method_start:method_end].count(
        "shortcut2.setContext(Qt.WidgetWithChildrenShortcut)"
    ) == 1
    assert "widget.returnPressed.connect(callback)" in source[method_start:method_end]
    assert "inner_line_edit.returnPressed.connect(_submit_composite_input)" in source[
        method_start:method_end
    ]
    assert 'interpret_text = getattr(widget, "interpretText", None)' in source[
        method_start:method_end
    ]
