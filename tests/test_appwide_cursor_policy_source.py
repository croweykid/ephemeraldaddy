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
