import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtGui = pytest.importorskip("PySide6.QtGui", exc_type=ImportError)
QtWidgets = pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
QTextCursor = QtGui.QTextCursor
QApplication = QtWidgets.QApplication
QPlainTextEdit = QtWidgets.QPlainTextEdit

from ephemeraldaddy.gui.features.chart_information.plugin_renderer import (
    CHART_DATA_HIGHLIGHT_COLOR,
    append_plugin_paragraphs,
)


def _app():
    return QApplication.instance() or QApplication([])


def test_chart_info_plugin_renderer_appends_and_resets_each_segment_format():
    _app()
    output = QPlainTextEdit()
    output.setPlainText("Native Sun interpretation")
    append_plugin_paragraphs(
        output,
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
    append_plugin_paragraphs(output, [[], [{}], ["bad"]])
    assert output.toPlainText() == "native"
