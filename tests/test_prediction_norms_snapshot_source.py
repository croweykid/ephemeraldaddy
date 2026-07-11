from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (ROOT / "ephemeraldaddy" / "gui" / "app.py").read_text(encoding="utf-8")
DND_SOURCE = (ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "dnd_predictions.py").read_text(encoding="utf-8")
TRAIT_SOURCE = (ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "trait_predictions.py").read_text(encoding="utf-8")
DB_INFO_SOURCE = (ROOT / "ephemeraldaddy" / "gui" / "features" / "controllers" / "db_info.py").read_text(encoding="utf-8")
SNAPSHOT_SOURCE = (ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "prediction_norms_snapshot.py").read_text(encoding="utf-8")


def test_predictions_norm_snapshot_module_defines_shared_static_payload():
    assert 'PREDICTION_NORMS_SNAPSHOT_FILENAME = ".prediction_norms_snapshot.json"' in SNAPSHOT_SOURCE
    assert "def refresh_prediction_norms_snapshot" in SNAPSHOT_SOURCE
    assert '"trait_baselines"' in SNAPSHOT_SOURCE
    assert '"dnd_stat_raw_averages"' in SNAPSHOT_SOURCE


def test_chart_view_traits_prefer_shared_prediction_norm_snapshot():
    method = TRAIT_SOURCE.split("def _database_trait_averages", 1)[1].split("chart_ids = _database_chart_ids", 1)[0]
    assert '_prediction_norm_snapshot_trait_averages' in method
    assert 'return {name: float(snapshot_averages[name]) for name in requested_names}' in method


def test_dnd_statblock_uses_shared_snapshot_averages_before_norm_charts():
    init_method = DND_SOURCE.split("class DndPredictionPanelAdapter", 1)[1].split("def _show_calculate_prompt", 1)[0]
    assert "db_norm_averages_provider" in init_method
    score_method = DND_SOURCE.split("def _score_statblock", 1)[1].split("def draw", 1)[0]
    assert "self.db_norm_averages_provider" in score_method
    assert score_method.index("self.db_norm_averages_provider") < score_method.index("_calculate_db_norm_stat_averages(norm_charts)")
    assert "or (allow_stale and same_chart_token)" in score_method


def test_app_adapter_avoids_loading_norm_charts_when_snapshot_has_dnd_stat_averages():
    adapter = APP_SOURCE.split("def _dnd_prediction_adapter", 1)[1].split("def _draw_dnd_statblock_predictions", 1)[0]
    assert "db_norm_averages_provider=self._prediction_norm_snapshot_dnd_stat_averages" in adapter
    assert "norm_charts_provider=lambda: [] if self._prediction_norm_snapshot_dnd_stat_averages() else self._prediction_norm_charts()" in adapter


def test_database_statistics_exposes_manual_refresh_norms_button():
    assert 'QPushButton("Refresh Predictions Norms")' in DB_INFO_SOURCE
    assert "refresh_prediction_norms_snapshot(owner)" in DB_INFO_SOURCE
