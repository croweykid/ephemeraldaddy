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
    assert "update_chart_weirdness_score(chart_id, weirdness_score)" in hydrate_method
    assert "mutable_row[31] = float(weirdness_score)" in hydrate_method
