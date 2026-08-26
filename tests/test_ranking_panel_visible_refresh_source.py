from pathlib import Path


RANKINGS_SOURCE = Path("ephemeraldaddy/gui/ranking_panel.py").read_text(encoding="utf-8")
APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def test_database_reload_refreshes_only_visible_dirty_rankings_sections():
    populate = APP_SOURCE.split("def _populate_list", 1)[1].split(
        "def _run_database_metrics_refresh", 1
    )[0]
    assert "self._refresh_visible_rankings_sections()" not in populate

    reload_method = APP_SOURCE.split("def _refresh_charts", 1)[1].split(
        "def _normalize_chart_row", 1
    )[0]
    assert "self._rankings_data_dirty = True" in reload_method
    assert "self._refresh_visible_rankings_sections()" in reload_method

    visible_refresh = RANKINGS_SOURCE.split(
        "def _refresh_visible_rankings_sections", 1
    )[1].split("@staticmethod", 1)[0]
    assert '"_rankings_data_dirty", True' in visible_refresh
    assert '_active_left_panel", None) != "rankings"' in visible_refresh
    assert '_left_panel_visible", False' in visible_refresh
    assert '"_is_left_panel_collapsed", None' in visible_refresh
    assert "if is_expanded" in visible_refresh
    assert "self._rankings_data_dirty = False" in visible_refresh


def test_revealing_collapsed_left_splitter_refreshes_dirty_rankings():
    splitter_moved = APP_SOURCE.split("def _on_content_splitter_moved", 1)[1].split(
        "def _apply_content_splitter_layout", 1
    )[0]
    assert "self._left_panel_visible and sizes[0] > 0" in splitter_moved
    assert "self._refresh_visible_rankings_sections()" in splitter_moved


def test_rankings_sections_refresh_independently_when_visible():
    build = RANKINGS_SOURCE.split("def _build_rankings_panel", 1)[1].split(
        "def _on_rankings_section_toggled", 1
    )[0]
    assert '"traits", expanded' in build
    assert '"sign_dominance", expanded' in build
    assert '_refresh_rankings_panel({"traits"})' in build
    assert '_refresh_rankings_panel({"sign_dominance"})' in build

    refresh = RANKINGS_SOURCE.split("def _refresh_rankings_panel", 1)[1].split(
        "@staticmethod", 1
    )[0]
    assert 'if "traits" not in requested_sections:' in refresh
    assert 'if "sign_dominance" in requested_sections:' in refresh


def test_hidden_partial_trait_ranking_is_resumed_when_rankings_reopens():
    continuation = RANKINGS_SOURCE.split(
        "def _schedule_rankings_traits_continuation", 1
    )[1].split("def _refresh_rankings_panel", 1)[0]

    assert '"_active_left_panel", None' in continuation
    assert '== "rankings"' in continuation
    assert 'getattr(self, "_left_panel_visible", False)' in continuation
    assert 'getattr(self, "_is_left_panel_collapsed", None)' in continuation
    assert "if not rankings_visible:" in continuation
    assert "self._rankings_data_dirty = True" in continuation
    assert "self._refresh_rankings_panel({\"traits\"})" in continuation
