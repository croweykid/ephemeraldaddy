from pathlib import Path

APP_SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py").read_text()


def test_gender_guesser_reautoscrolls_after_lazy_canvas_refresh():
    assert "def _schedule_database_metrics_section_bottom_autoscroll" in APP_SOURCE
    assert "for delay_ms in (0, 80, 220, 420, 700):" in APP_SOURCE
    assert 'self._schedule_database_metrics_section_bottom_autoscroll("gender")' in APP_SOURCE


def test_gender_guesser_expansion_resets_horizontal_offset_and_left_aligns_canvas():
    assert "horizontal_scrollbar.setValue(horizontal_scrollbar.minimum())" in APP_SOURCE
    assert "self.gender_chart_layout.addWidget(gender_canvas, 0, Qt.AlignLeft)" in APP_SOURCE
