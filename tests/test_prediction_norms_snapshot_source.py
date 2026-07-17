from pathlib import Path

from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import (
    dnd_stat_snapshot_averages,
)

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


def test_predictions_norm_snapshot_refresh_includes_dnd_alignment_traits():
    refresh_method = SNAPSHOT_SOURCE.split("def refresh_prediction_norms_snapshot", 1)[1]
    assert "_dnd_alignment_trait_items" in refresh_method
    assert '("dnd_alignment", dnd_alignment_traits)' in refresh_method
    assert '"source": source' in refresh_method
    assert '"dnd_alignment_trait_keys": [str(trait.get("name", "") or "") for trait in dnd_alignment_traits]' in refresh_method


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
    assert "or (allow_stale and same_chart_token)" not in score_method


def test_empty_dnd_stat_snapshot_does_not_fabricate_zero_norms():
    assert dnd_stat_snapshot_averages({"version": 1, "dnd_stat_raw_averages": {}}) == {}
    assert dnd_stat_snapshot_averages({"version": 1}) == {}


def test_partial_dnd_stat_snapshot_is_not_treated_as_complete_norms():
    assert dnd_stat_snapshot_averages({"version": 1, "dnd_stat_raw_averages": {"STR": 1.0}}) == {}
    assert dnd_stat_snapshot_averages(
        {
            "version": 1,
            "dnd_stat_raw_averages": {
                "STR": 1.0,
                "DEX": 2.0,
                "CON": 3.0,
                "INT": 4.0,
                "WIS": 5.0,
                "CHA": 6.0,
            },
        }
    ) == {
        "STR": 1.0,
        "DEX": 2.0,
        "CON": 3.0,
        "INT": 4.0,
        "WIS": 5.0,
        "CHA": 6.0,
    }


def test_app_adapter_avoids_loading_norm_charts_when_snapshot_has_dnd_stat_averages():
    adapter = APP_SOURCE.split("def _dnd_prediction_adapter", 1)[1].split("def _draw_dnd_statblock_predictions", 1)[0]
    assert "db_norm_averages_provider=self._prediction_norm_snapshot_dnd_stat_averages" in adapter
    assert "norm_charts_provider=lambda: [] if self._prediction_norm_snapshot_dnd_stat_averages() else self._prediction_norm_charts()" in adapter


def test_database_statistics_exposes_manual_refresh_norms_button():
    assert 'QPushButton("Refresh Predictions Norms")' in DB_INFO_SOURCE
    assert "refresh_prediction_norms_snapshot(owner)" in DB_INFO_SOURCE


def test_chart_view_traits_keep_uid_metadata_visible_when_cache_is_stale_or_incomplete():
    cached_only_method = TRAIT_SOURCE.split("def trait_metadata_for_chart", 1)[1].split("if cached_only:\n        return None", 1)[0]
    assert "if cached_only and (cached_rows_by_name or stale_rows_by_name):" in cached_only_method
    assert "rows previously persisted for this chart UID remain displayable" in cached_only_method
    assert "metadata[\"stale\"] = True" in cached_only_method
