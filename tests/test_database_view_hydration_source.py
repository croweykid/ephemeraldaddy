from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def _method_source(name: str) -> str:
    marker = f"    def {name}"
    start = APP_SOURCE.index(marker)
    next_start = APP_SOURCE.find("\n    def ", start + len(marker))
    return APP_SOURCE[start:] if next_start == -1 else APP_SOURCE[start:next_start]


def test_populate_list_batches_chart_hydration_for_visible_rows_and_glyphs():
    refresh_method = _method_source("_refresh_charts")
    populate_method = _method_source("_populate_list")

    assert "self._hydrate_chart_filter_cache" not in refresh_method
    assert 'row_info_visibility.get("sign_glyphs", True)' in populate_method
    assert "self._hydrate_chart_filter_cache(int(row[0]) for row in rows)" in populate_method


def test_populate_list_skips_per_row_filter_engine_when_no_filters_are_active():
    populate_method = _method_source("_populate_list")

    assert "has_active_chart_filters = self._has_active_chart_filters()" in populate_method
    assert "if has_active_chart_filters:\n                    try:\n                        matches_filters = self._chart_matches_filters(cid)" in populate_method
