from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def _method_source(method_name: str) -> str:
    start = APP_SOURCE.index(f"    def {method_name}")
    next_method = APP_SOURCE.index("\n    def ", start + 1)
    return APP_SOURCE[start:next_method]


def test_weirdness_sort_hydrates_missing_scores_before_sorting():
    populate_method = _method_source("_populate_list")
    hydrate_method = _method_source("_hydrate_missing_weirdness_scores_for_sort")

    assert 'elif self._sort_mode == "weirdness":' in populate_method
    assert "rows = self._hydrate_missing_weirdness_scores_for_sort(rows)" in populate_method
    assert "self._prediction_norm_metric_payloads()" in hydrate_method
    assert "_calculate_weirdness_score_from_metric_payloads" in hydrate_method
    assert "formula_version=_DISTINGUISHING_FORMULA_VERSION" in hydrate_method
    assert "norm_signature=norm_signature" in hydrate_method
    assert "mutable_row[31] = float(weirdness_score)" in hydrate_method
    assert "self._weirdness_sort_cache_metadata_by_id[chart_id]" in hydrate_method
    assert "mutable_row[32]" not in hydrate_method
    assert "mutable_row[33]" not in hydrate_method



def test_normalized_database_rows_keep_render_shape_and_chart_view_uses_module_signature():
    manage_normalize = _method_source("_normalize_chart_row")
    main_start = APP_SOURCE.index("    def _normalize_chart_row", APP_SOURCE.index("class MainWindow"))
    main_next = APP_SOURCE.index("\n    def ", main_start + 1)
    main_normalize = APP_SOURCE[main_start:main_next]

    assert "int(padded[32])" not in manage_normalize
    assert "str(padded[33]" not in manage_normalize
    assert "int(padded[32])" not in main_normalize
    assert "str(padded[33]" not in main_normalize
    assert "_weirdness_norm_signature_for_rows(self._prediction_norm_rows())" in APP_SOURCE
    assert "self._weirdness_norm_signature" not in APP_SOURCE
