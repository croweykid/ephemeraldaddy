from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_style_defines_shared_cursor_policy_and_installs_button_defaults():
    source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()

    assert "APP_CHART_INFO_LINK_CURSOR = Qt.WhatsThisCursor" in source
    assert "APP_POPOUT_CURSOR = Qt.PointingHandCursor" in source
    assert "APP_BUTTON_CURSOR = Qt.PointingHandCursor" in source
    assert "def apply_chart_info_link_cursor" in source
    assert "def apply_popout_cursor" in source
    assert "def apply_button_cursor" in source
    assert "def install_appwide_cursor_defaults" in source
    assert "for child in obj.findChildren(QAbstractButton):" in source


def test_application_installs_appwide_cursor_defaults_at_startup():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()

    assert "install_appwide_cursor_defaults(app)" in source


def test_chart_info_popout_contexts_update_hover_cursor():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    event_filter_start = source.index("    def eventFilter(self, obj, event):")
    manage_event_filter = source[
        event_filter_start : source.index("    def _handle_list_letter_jump", event_filter_start)
    ]

    assert "event.type() == QEvent.MouseMove" in manage_event_filter
    assert "_update_summary_info_hover_cursor" in manage_event_filter
    assert "event.type() == QEvent.Leave" in manage_event_filter
    assert "obj.unsetCursor()" in manage_event_filter


def test_chart_view_and_database_view_graphs_use_shared_popout_cursor():
    app_source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    database_source = (
        REPO_ROOT / "ephemeraldaddy/gui/features/charts/database_analytics.py"
    ).read_text()

    assert "apply_popout_cursor(canvas)" in database_source
    render_chart_start = app_source.index("    def _render_chart(self, chart: Chart) -> None:")
    render_chart = app_source[
        render_chart_start : app_source.index("    def _clear_chart_displays", render_chart_start)
    ]
    assert "apply_popout_cursor(canvas)" in render_chart


def test_feature_panels_import_shared_cursor_helpers_instead_of_raw_button_cursors():
    paths = [
        "ephemeraldaddy/gui/app.py",
        "ephemeraldaddy/gui/dev_tools.py",
        "ephemeraldaddy/gui/features/controllers/main_window.py",
        "ephemeraldaddy/gui/features/controllers/chart_view_window.py",
        "ephemeraldaddy/gui/features/controllers/db_info.py",
        "ephemeraldaddy/gui/features/charts/anagrams.py",
        "ephemeraldaddy/gui/features/charts/aspect_weight_graphs.py",
        "ephemeraldaddy/gui/features/charts/db_info_panel.py",
        "ephemeraldaddy/gui/features/charts/popout_helpers.py",
        "ephemeraldaddy/gui/features/charts/similar_charts_popout.py",
    ]

    for relative_path in paths:
        source = (REPO_ROOT / relative_path).read_text()
        assert "apply_button_cursor" in source
        assert "setCursor(Qt.CursorShape.PointingHandCursor)" not in source


def test_chart_info_detail_links_use_question_cursor_helper():
    paths = [
        "ephemeraldaddy/gui/features/charts/db_info_panel.py",
        "ephemeraldaddy/gui/features/charts/dnd_predictions.py",
        "ephemeraldaddy/gui/features/charts/human_design_analytics_panel.py",
        "ephemeraldaddy/gui/features/dialogues.py",
    ]

    for relative_path in paths:
        source = (REPO_ROOT / relative_path).read_text()
        assert "apply_chart_info_link_cursor" in source
