"""Chart Info backgrounds are fixed black regardless of semantic text color."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTextEdit

from ephemeraldaddy.gui.style import (
    APPWIDE_DARK_THEME_STYLESHEET,
    CHART_INFO_BACKGROUND_COLOR,
    set_chart_info_contrast_background,
)


def test_chart_info_surface_is_black_not_legacy_gold():
    assert CHART_INFO_BACKGROUND_COLOR == "#000000"
    assert 'QTextEdit[eddChartInfoBackground="true"]' in APPWIDE_DARK_THEME_STYLESHEET
    assert 'QPlainTextEdit[eddChartInfoBackground="true"]' in APPWIDE_DARK_THEME_STYLESHEET
    assert f"background-color: {CHART_INFO_BACKGROUND_COLOR};" in APPWIDE_DARK_THEME_STYLESHEET
    assert "eddLightContrastBackground" not in APPWIDE_DARK_THEME_STYLESHEET


def test_chart_info_foreground_colors_cannot_switch_background():
    app = QApplication.instance() or QApplication([])
    editor = QTextEdit()
    try:
        set_chart_info_contrast_background(editor)
        assert editor.property("eddChartInfoBackground") is True
        for foreground in ("#000000", "#ffffff", "#cc9900", "", None):
            set_chart_info_contrast_background(editor, foreground)
            assert editor.property("eddChartInfoBackground") is True
            assert not editor.property("eddLightContrastBackground")
    finally:
        editor.close()


def test_chart_info_widgets_apply_fixed_black_on_creation():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    chart_view_source = (
        repo / "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
    ).read_text(encoding="utf-8")
    db_view_source = (
        repo / "ephemeraldaddy/gui/features/charts/db_info_panel.py"
    ).read_text(encoding="utf-8")

    assert (
        "owner.chart_info_output = QTextEdit()\n"
        "    set_chart_info_contrast_background(owner.chart_info_output)"
    ) in chart_view_source
    assert (
        "self.output = QTextEdit(self)\n"
        "        set_chart_info_contrast_background(self.output)"
    ) in db_view_source
