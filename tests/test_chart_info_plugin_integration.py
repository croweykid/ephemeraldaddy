import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtGui = pytest.importorskip("PySide6.QtGui", exc_type=ImportError)
QtWidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QTextCursor = QtGui.QTextCursor
QApplication = QtWidgets.QApplication
QPlainTextEdit = QtWidgets.QPlainTextEdit

from ephemeraldaddy.gui.app import CHART_DATA_HIGHLIGHT_COLOR, MainWindow


def _app():
    return QApplication.instance() or QApplication([])


def test_chart_info_plugin_renderer_appends_and_resets_each_segment_format():
    _app()
    output = QPlainTextEdit()
    output.setPlainText("Native Sun interpretation")
    owner = SimpleNamespace(chart_info_output=output)
    MainWindow._append_chart_info_plugin_paragraphs(
        owner,
        [
            [
                {"text": "Header", "bold": True, "color_role": "highlight"},
                {"text": "\naverage", "italic": True},
            ],
            [{"text": "Best case: ", "bold": True}, {"text": "body"}],
        ],
    )
    assert output.toPlainText() == (
        "Native Sun interpretation\n\nHeader\naverage\n\nBest case: body"
    )

    document = output.document()
    cursor = QTextCursor(document)
    text = output.toPlainText()

    def char_format(fragment):
        cursor.setPosition(text.index(fragment))
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(fragment))
        return cursor.charFormat()

    header = char_format("Header")
    assert header.font().bold()
    assert header.foreground().color().name().lower() == CHART_DATA_HIGHLIGHT_COLOR.lower()
    average = char_format("average")
    assert average.fontItalic() and not average.font().bold()
    body = char_format("body")
    assert not body.fontItalic() and not body.font().bold()


def test_chart_info_plugin_renderer_ignores_malformed_empty_output():
    _app()
    output = QPlainTextEdit()
    output.setPlainText("native")
    owner = SimpleNamespace(chart_info_output=output)
    MainWindow._append_chart_info_plugin_paragraphs(owner, [[], [{}], ["bad"]])
    assert output.toPlainText() == "native"


def test_generic_hook_dispatch_is_restricted_to_main_chart_info_source():
    source = (MainWindow._handle_summary_info_click.__code__.co_filename)
    text = open(source, encoding="utf-8").read()
    method = text.split("    def _handle_summary_info_click(", 1)[1].split(
        "    def _run_with_chart_info_output(", 1
    )[0]
    assert "targets_main_chart_info = target_info_widget is self.chart_info_output" in method
    assert "if targets_main_chart_info:" in method
    assert "chart_info_plugin_paragraphs(" in method
    assert method.index("self._show_position_info(body, sign, house_num)") < method.index(
        "chart_info_plugin_paragraphs("
    )
