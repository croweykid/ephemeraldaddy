from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()
CHART_VIEW_SOURCE = Path("ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()
TAGGING_SOURCE = Path("ephemeraldaddy/gui/features/charts/tagging.py").read_text()


def test_tag_completer_refresh_reuses_existing_completer_model():
    assert "QStringListModel" in TAGGING_SOURCE
    assert 'existing_completer = getattr(line_edit, "_tags_completer", None)' in TAGGING_SOURCE
    assert "existing_model.setStringList(list(known_tags))" in TAGGING_SOURCE
    assert "return" in TAGGING_SOURCE.split("existing_model.setStringList", 1)[1].split(
        "completer = QCompleter", 1
    )[0]


def test_chart_view_tag_add_has_terminal_debug_breadcrumbs():
    handler = CHART_VIEW_SOURCE.split("def on_chart_view_tag_add", 1)[1].split(
        "def on_chart_view_tag_remove_link", 1
    )[0]
    assert "logger.debug" in handler
    assert "Chart View tag add requested" in handler
    assert "refreshing tag catalog" in handler
    assert "catalog refresh finished" in handler


def test_startup_debug_enables_faulthandler_for_native_crashes():
    assert "import faulthandler" in APP_SOURCE
    debug_config = APP_SOURCE.split("def _configure_debug_logging", 1)[1].split(
        "def _should_run_startup_dependency_check", 1
    )[0]
    assert "faulthandler.enable(all_threads=True)" in debug_config
    assert "faulthandler.is_enabled()" in debug_config
