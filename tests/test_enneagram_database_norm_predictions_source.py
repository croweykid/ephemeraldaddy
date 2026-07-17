from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENNEAGRAM_SOURCE = (ROOT / "ephemeraldaddy/gui/features/charts/enneagram_predictions.py").read_text(encoding="utf-8")
APP_SOURCE = (ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def test_enneagram_predictions_score_against_database_norms_source():
    assert "def calculate_database_enneagram_type_averages" in ENNEAGRAM_SOURCE
    assert "def enneagram_score_parts" in ENNEAGRAM_SOURCE
    assert '"deviation": chart_score - database_score' in ENNEAGRAM_SOURCE
    assert 'scores = {enneagram_type: values["deviation"] for enneagram_type, values in parts.items()}' in ENNEAGRAM_SOURCE
    assert '"parts": parts' in ENNEAGRAM_SOURCE
    assert '"db_norm_averages": db_norm_averages' in ENNEAGRAM_SOURCE
    assert '"score_semantics": ENNEAGRAM_PREDICTION_SCORE_SEMANTICS' in ENNEAGRAM_SOURCE


def test_legacy_raw_enneagram_cache_fallbacks_are_stale_source():
    restore = ENNEAGRAM_SOURCE.split("def _restore_cache", 1)[1].split("def _cache_is_stale", 1)[0]
    stale = ENNEAGRAM_SOURCE.split("def _cache_is_stale", 1)[1].split("def cache_metadata", 1)[0]
    assert '"key": ("legacy_raw_enneagram_type_weights", _enneagram_chart_state_token(self, chart))' in restore
    assert '"score_semantics": "legacy_raw"' in restore
    assert 'cached.get("score_semantics") != ENNEAGRAM_PREDICTION_SCORE_SEMANTICS' in stale


def test_enneagram_adapter_uses_chart_view_prediction_norm_scope_source():
    adapter = APP_SOURCE.split("def _enneagram_prediction_adapter", 1)[1].split("def _draw_enneagram_predictions", 1)[0]
    assert "norm_charts_provider=self._prediction_norm_charts" in adapter
    assert "norm_charts_token_provider=self._prediction_norms_render_token" in adapter


def test_enneagram_cache_key_includes_norm_token_source():
    cache_key = ENNEAGRAM_SOURCE.split("def _cache_key", 1)[1].split("def _restore_cache", 1)[0]
    assert "self._norms_token()" in cache_key


def test_enneagram_predictor_uses_analysis_enneagrams_reference_source():
    assert "from ephemeraldaddy.analysis.enneagram import ENNEAGRAMS" in APP_SOURCE
    calculator = APP_SOURCE.split("def _calculate_enneagram_type_weights", 1)[1].split("def _normalize_chart_row", 1)[0]
    adapter = APP_SOURCE.split("def _enneagram_prediction_adapter", 1)[1].split("def _draw_enneagram_predictions", 1)[0]
    assert "enneagram=ENNEAGRAMS" in calculator
    assert "enneagram=ENNEAGRAMS" in adapter
