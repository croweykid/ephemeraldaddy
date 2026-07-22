from pathlib import Path


PROPERTY_MANAGER_SOURCE = Path("ephemeraldaddy/gui/property_manager.py").read_text()


def test_property_manager_defers_host_chart_refresh_until_dialog_close() -> None:
    create_widget_block = PROPERTY_MANAGER_SOURCE.split("def create_widget(", 1)[1].split(
        "def launch(", 1
    )[0]
    refresh_after_close_block = PROPERTY_MANAGER_SOURCE.split("def refresh_after_close", 1)[1].split(
        "def load_usage", 1
    )[0]

    assert "refresh_chart_context=self._mark_needs_refresh_after_close" in create_widget_block
    assert "self._host._refresh_charts" not in create_widget_block
    assert "self._needs_refresh_after_close = True" in PROPERTY_MANAGER_SOURCE
    assert "force_full_analysis_refresh=needs_refresh" in refresh_after_close_block
    assert "refresh_tag_completers=False" in refresh_after_close_block
