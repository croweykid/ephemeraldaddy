from pathlib import Path

CHART_EDITOR_SOURCE = Path(
    "ephemeraldaddy/gui/features/controllers/chart_view_window.py"
).read_text()
MAIN_WINDOW_SOURCE = Path(
    "ephemeraldaddy/gui/features/controllers/main_window.py"
).read_text()
TIME_SENSITIVITY_SOURCE = Path(
    "ephemeraldaddy/gui/features/charts/time_sensitivity_panel.py"
).read_text()


def test_chart_analysis_expansion_defers_initial_render_until_geometry_settles():
    start = CHART_EDITOR_SOURCE.index("def _set_chart_analysis_section_expanded")
    end = CHART_EDITOR_SOURCE.index("def _is_chart_analysis_section_visible", start)
    method = CHART_EDITOR_SOURCE[start:end]

    assert (
        "Collapsed right-panel sections can have stale or zero child geometry" in method
    )
    assert "QTimer.singleShot(0, schedule_expanded_section_render)" in method
    assert "QTimer.singleShot(75, schedule_expanded_section_render)" in method


def test_collapsible_metric_sections_refresh_visible_canvases_after_expansion():
    start = MAIN_WINDOW_SOURCE.index("    def add_collapsible_section")
    end = MAIN_WINDOW_SOURCE.index("    def add_section", start)
    method = MAIN_WINDOW_SOURCE[start:end]

    assert "_request_visible_metric_canvas_layouts" in method
    assert "refresh_visible_canvases()" in method
    assert "QTimer.singleShot(0, refresh_visible_canvases)" not in method


def test_time_sensitivity_html_sections_remeasure_browser_after_expansion():
    start = TIME_SENSITIVITY_SOURCE.index("    def _add_html_section")
    end = TIME_SENSITIVITY_SOURCE.index("    def _render_weight_sections", start)
    method = TIME_SENSITIVITY_SOURCE[start:end]

    assert "from PySide6.QtCore import Qt, QTimer, QUrl" in TIME_SENSITIVITY_SOURCE
    assert "def schedule_browser_height_adjustments" in method
    assert "if browser.parentWidget() is None:" in method
    assert "except RuntimeError:" in method
    assert "finally:" in method
    assert "adjusting_browser_height = False" in method
    assert "for delay_ms in (0, 50, 150, 300):" in method
    assert "QTimer.singleShot(delay_ms, adjust_browser_height)" in method


def test_time_sensitivity_collapsed_html_sections_defer_html_and_height_work():
    start = TIME_SENSITIVITY_SOURCE.index("    def _add_html_section")
    end = TIME_SENSITIVITY_SOURCE.index("    def _render_weight_sections", start)
    method = TIME_SENSITIVITY_SOURCE[start:end]

    assert "html_loaded = expanded" in method
    assert "if expanded:\n            browser.setHtml(html)" in method
    assert "def ensure_browser_html_loaded" in method
    assert "if not toggle.isChecked():\n                return" in method
    assert "if not content.isVisible():\n                return" not in method
    assert "if expanded:\n            schedule_browser_height_adjustments()" in method


def test_time_sensitivity_human_design_section_starts_expanded():
    render_start = TIME_SENSITIVITY_SOURCE.index("    def _render_weight_sections")
    render_end = TIME_SENSITIVITY_SOURCE.index(
        "    def _show_likelihood_popout", render_start
    )
    method = TIME_SENSITIVITY_SOURCE[render_start:render_end]

    assert (
        '"human_design", "Human Design", _human_design_html(result), expanded=True'
        in method
    )


def test_predictions_gender_guesser_section_starts_expanded():
    build_start = CHART_EDITOR_SOURCE.index("def _build_predictions_panel")
    build_end = CHART_EDITOR_SOURCE.index(
        "def _ensure_photo_gallery_chart_uid", build_start
    )
    method = CHART_EDITOR_SOURCE[build_start:build_end]
    gender_start = method.index('section_key="gender_guesser"')
    gender_section = method[gender_start:]

    assert "expanded=True" in gender_section
