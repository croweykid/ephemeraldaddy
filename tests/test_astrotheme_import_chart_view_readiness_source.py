from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()


def test_astrotheme_import_waits_for_complete_chart_view_form() -> None:
    handler_start = APP_SOURCE.index("    def _on_import_astrotheme_from_search_panel")
    handler_end = APP_SOURCE.index("    def ", handler_start + 8)
    handler = APP_SOURCE[handler_start:handler_end]

    readiness_guard = handler.index('getattr(parent, "_chart_view_form_ready", False)')
    form_reset = handler.index("parent._reset_new_chart_form()")
    assert readiness_guard < form_reset
    assert "self._pending_astrotheme_import = True" in handler


def test_main_window_resumes_deferred_astrotheme_import_after_setup() -> None:
    init_start = APP_SOURCE.index("    def __init__(self):", APP_SOURCE.index("class MainWindow"))
    init_end = APP_SOURCE.index("    def _decrease_chart_view_label_font_sizes", init_start)
    init = APP_SOURCE[init_start:init_end]

    assert init.index("self._chart_view_form_ready = False") < init.index(
        "self._chart_view_form_ready = True"
    )
    ready = init.index("self._chart_view_form_ready = True")
    resume = init.index("QTimer.singleShot(0, manage_charts_dialog._on_import_astrotheme_from_search_panel)")
    assert ready < resume
