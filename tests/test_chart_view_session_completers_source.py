from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()


def test_chart_view_tag_completers_preserve_session_tags_before_save():
    assert "def _tag_completer_tags_for_session" in APP_SOURCE
    helper_start = APP_SOURCE.index("def _tag_completer_tags_for_session")
    helper_end = APP_SOURCE.index("def _update_tag_completers", helper_start)
    helper_source = APP_SOURCE[helper_start:helper_end]
    assert "list_recognized_tags()" in helper_source
    assert "_known_chart_tags" in helper_source
    assert "_chart_tags_current" in helper_source
    assert "normalize_tag_list" in helper_source


def test_chart_view_completers_refresh_when_session_sensitive_fields_gain_focus():
    assert "self.chart_tags_input.installEventFilter(self)" in APP_SOURCE
    assert "self.reminds_me_of_input.installEventFilter(self)" in APP_SOURCE
    assert "event.type() == QEvent.FocusIn" in APP_SOURCE
    assert 'getattr(self, "chart_tags_input", None)' in APP_SOURCE
    assert 'getattr(self, "reminds_me_of_input", None)' in APP_SOURCE
    assert "refresh_location_completers=False" in APP_SOURCE
    assert "refresh_tag_lists=False" in APP_SOURCE
