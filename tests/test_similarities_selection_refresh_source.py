from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def _selection_changed_source() -> str:
    start = APP_SOURCE.index("    def _on_selection_changed")
    end = APP_SOURCE.index("\n    @staticmethod", start)
    return APP_SOURCE[start:end]


def test_visible_similarities_panel_refreshes_even_when_metrics_refresh_is_skipped():
    source = _selection_changed_source()

    similarities_refresh = source.index("self.similarities_controller.update_analysis(")
    metrics_skip = source.index("if not refresh_metrics:")

    assert similarities_refresh < metrics_skip
    assert 'self._active_left_panel == "similarities"' in source
    assert "update_similarities=False" in source


def test_direct_similarities_refresh_stabilizes_layout_and_restores_inner_scroll():
    source = _selection_changed_source()
    direct_refresh = source[source.index("if similarities_visible:"):]

    assert "similarities_analysis_panel_scroll" in direct_refresh
    assert "similarities_scrollbar.value()" in direct_refresh
    assert "finally:" in direct_refresh
    assert "self._stabilize_left_scroll_panel_layout(similarities_scroll)" in direct_refresh
    assert "self._restore_scrollbar_position(" in direct_refresh
