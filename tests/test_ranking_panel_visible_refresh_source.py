from pathlib import Path


RANKINGS_SOURCE = Path("ephemeraldaddy/gui/ranking_panel.py").read_text(encoding="utf-8")
APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def test_database_population_refreshes_only_visible_rankings_sections():
    populate = APP_SOURCE.split("def _populate_list", 1)[1].split(
        "def _run_database_metrics_refresh", 1
    )[0]
    assert "self._refresh_visible_rankings_sections()" in populate

    visible_refresh = RANKINGS_SOURCE.split(
        "def _refresh_visible_rankings_sections", 1
    )[1].split("@staticmethod", 1)[0]
    assert '_active_left_panel", None) != "rankings"' in visible_refresh
    assert '_left_panel_visible", False' in visible_refresh
    assert '"_is_left_panel_collapsed", None' in visible_refresh
    assert "if is_expanded" in visible_refresh


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
