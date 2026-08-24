import json
from pathlib import Path

import pytest

from ephemeraldaddy.gui.features.charts import prediction_norms_snapshot as snapshot_module
from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import (
    ExplicitNormRecalculationRequired,
    dnd_stat_snapshot_averages,
    load_prediction_norms_snapshot,
    missing_trait_norms,
    remove_trait_from_prediction_norms_snapshot,
    refresh_prediction_norms_snapshot,
    save_prediction_norms_snapshot,
    set_trait_retired_in_prediction_norms_snapshot,
)
from ephemeraldaddy.gui.features.charts import prediction_norms_snapshot as snapshot_module

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
    assert "trait_snapshot_averages(traits, snapshot)" in method
    assert "Traits panel bypassed unavailable profiles" in method
    assert "refresh_trait_norms_snapshot(owner, missing_traits)" not in method


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
    database_stats_builder = DB_INFO_SOURCE.split("def add_database_info_settings_section", 1)[1]
    assert 'QPushButton("Recalculate DB Norms")' not in database_stats_builder
    assert "def add_prediction_norms_recalculation_tool" in DB_INFO_SOURCE
    assert "add_prediction_norms_recalculation_tool(self, dev_tools_section)" in APP_SOURCE
    assert "refresh_prediction_norms_snapshot(owner, user_initiated=True)" in DB_INFO_SOURCE


def test_whole_database_norm_refresh_requires_explicit_user_action():
    with pytest.raises(ExplicitNormRecalculationRequired):
        refresh_prediction_norms_snapshot(object())

    app_refresh = APP_SOURCE.split("def _refresh_prediction_norms_snapshot", 1)[1].split(
        "def _prediction_norm_charts", 1
    )[0]
    assert "refresh_prediction_norms_snapshot(self, user_initiated=True)" in app_refresh


def test_missing_trait_coverage_never_triggers_automatic_database_generation():
    method = TRAIT_SOURCE.split("def _database_trait_averages", 1)[1].split(
        "def trait_metadata_for_chart", 1
    )[0]
    snapshot_read_path = method.split("if not force_refresh_stale:", 1)[1].split(
        "chart_uids = _database_chart_uids(owner)", 1
    )[0]
    assert "return {name: float(snapshot_averages[name])" in snapshot_read_path
    assert "refresh_trait_norms_snapshot" not in snapshot_read_path
    assert "_database_chart_uids" not in snapshot_read_path
    assert "_calculate_database_trait_averages_direct" not in snapshot_read_path


def test_missing_trait_coverage_returns_available_norms_and_logs_omissions():
    method = TRAIT_SOURCE.split("def _database_trait_averages", 1)[1].split(
        "def trait_metadata_for_chart", 1
    )[0]
    assert 'logger.warning("Traits panel bypassed unavailable profiles: %s", reason)' in method
    assert "if name in snapshot_averages" in method


def test_chart_view_traits_keep_uid_metadata_visible_when_cache_is_stale_or_incomplete():
    cached_only_method = TRAIT_SOURCE.split("def trait_metadata_for_chart", 1)[1].split("if cached_only:\n        return None", 1)[0]
    assert "if cached_only and (cached_rows_by_name or stale_rows_by_name):" in cached_only_method
    assert "rows previously persisted for this chart UID remain displayable" in cached_only_method
    assert "display_is_stale =" in cached_only_method
    assert "metadata = _metadata_from_vectors(" in cached_only_method


def test_rankings_panel_traits_prefer_shared_prediction_norm_snapshot():
    ranking_panel_source = (ROOT / "ephemeraldaddy" / "gui" / "ranking_panel.py").read_text(encoding="utf-8")
    method = ranking_panel_source.split("def _refresh_rankings_panel", 1)[1].split(
        "def _refresh_sign_dominance_rankings", 1
    )[0]
    assert "trait_snapshot_averages(trait_items)" in method
    assert "requested_trait_names.issubset(set(snapshot_averages))" in method
    assert "_rankings_trait_likelihood_cache_complete" in method
    assert method.index("trait_snapshot_averages(trait_items)") < method.index("_collect_traits_distribution_analytics")
    snapshot_fast_path = method.split(
        "if requested_trait_names and requested_trait_names.issubset(set(snapshot_averages)):", 1
    )[1].split("if not database_values:", 1)[0]
    assert "_collect_traits_distribution_analytics" not in snapshot_fast_path


def test_restore_window_settings_refreshes_open_rankings_panel_after_widgets_exist():
    restore_method = APP_SOURCE.split("def _restore_window_settings", 1)[1].split(
        "stored_active_right_panel", 1
    )[0]
    assert 'if self._left_panel_visible and self._active_left_panel == "rankings":' in restore_method
    assert "QTimer.singleShot(0, self._refresh_rankings_panel)" in restore_method


def test_rankings_panel_falls_back_when_trait_likelihood_cache_is_incomplete():
    ranking_panel_source = (ROOT / "ephemeraldaddy" / "gui" / "ranking_panel.py").read_text(encoding="utf-8")
    helper = ranking_panel_source.split("def _rankings_trait_likelihood_cache_complete", 1)[1].split(
        "def _refresh_rankings_panel", 1
    )[0]
    refresh_method = ranking_panel_source.split("def _refresh_rankings_panel", 1)[1].split(
        "def _refresh_sign_dominance_rankings", 1
    )[0]
    assert "return False" in helper
    assert "profile_cache_key in profile_cache" in helper
    assert "if not self._rankings_trait_likelihood_cache_complete" in refresh_method
    assert "database_values = {}" in refresh_method
    assert "if not database_values:" in refresh_method

def test_prediction_norm_snapshot_loads_norm_charts_by_uid_not_id():
    helper = SNAPSHOT_SOURCE.split("def _owner_chart_uids", 1)[1].split("def refresh_prediction_norms_snapshot", 1)[0]
    assert "def _owner_chart_ids" not in SNAPSHOT_SOURCE
    assert "db.load_charts_by_uids(chart_uids)" in helper
    assert "db.load_charts(chart_ids)" not in helper


def test_trait_direct_database_averages_load_charts_by_uid_not_id():
    helper = TRAIT_SOURCE.split("def _calculate_database_trait_averages_direct", 1)[1].split("def _database_trait_averages", 1)[0]
    assert "chart_uids: tuple[str, ...]" in helper
    assert "db.load_charts_by_uids(chart_uids)" in helper
    assert "db.load_chart(int(chart_id))" not in helper
    caller = TRAIT_SOURCE.split("def _database_trait_averages", 1)[1].split("def _trait_metadata_cache_key", 1)[0]
    assert "_calculate_database_trait_averages_direct(owner, chart_uids" in caller


def test_static_snapshot_short_circuits_live_cohort_signature_work():
    helper = TRAIT_SOURCE.split("def _trait_render_signatures", 1)[1].split(
        "def _traits_pending_cached_metadata", 1
    )[0]
    assert "missing_trait_norms(traits, snapshot)" in helper
    assert "_trait_snapshot_norm_signature(traits, snapshot)" in helper
    assert "_database_norm_state(owner)" not in helper
    assert "_database_chart_uids(owner)" not in helper
    assert "norm_signature = _trait_snapshot_norm_signature(traits, snapshot)" in helper
    assert "get_chart_uid(" not in helper
    assert "get_chart_id_by_uid(" not in helper
    assert "get_chart_ids_by_uid(" not in helper


def test_snapshot_requires_matching_profile_hash_for_full_trait_coverage(tmp_path):
    trait = {"uid": "doctor", "name": "Doctor", "profile": {"signs": {"Aries": 1}}}
    path = tmp_path / "norms.json"
    save_prediction_norms_snapshot(
        {
            "version": 1,
            "snapshot_id": "partial",
            "trait_baselines": {
                "uid:doctor": {
                    "uid": "doctor",
                    "name": "Doctor",
                    "profile_hash": "stale-profile",
                    "db_average": 55.0,
                }
            },
        },
        path,
    )
    snapshot = load_prediction_norms_snapshot(path)

    assert missing_trait_norms([trait], snapshot) == [trait]


def test_population_source_is_exclusive_and_official_uses_custom_trait_extension(
    tmp_path, monkeypatch
):
    official_path = tmp_path / "official.json"
    local_path = tmp_path / "local.json"
    extension_path = tmp_path / "extensions.json"
    source_path = tmp_path / "source.json"
    official_path.write_text(
        json.dumps(
            {
                "version": 1,
                "snapshot_id": "official",
                "trait_baselines": {"uid:official": {"db_average": 51.0}},
            }
        ),
        encoding="utf-8",
    )
    local_path.write_text(
        json.dumps(
            {
                "version": 1,
                "snapshot_id": "local",
                "trait_baselines": {"uid:custom": {"db_average": 62.0}},
            }
        ),
        encoding="utf-8",
    )
    extension_path.write_text(
        json.dumps(
            {
                "version": 1,
                "snapshot_id": "extension",
                "trait_baselines": {
                    "uid:custom": {"db_average": 62.0},
                    "uid:official": {"db_average": 99.0},
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(snapshot_module, "OFFICIAL_PREDICTION_NORMS_SNAPSHOT_PATH", official_path)
    monkeypatch.setattr(snapshot_module, "PREDICTION_NORMS_SNAPSHOT_PATH", local_path)
    monkeypatch.setattr(snapshot_module, "PREDICTION_NORMS_TRAIT_EXTENSIONS_PATH", extension_path)
    monkeypatch.setattr(snapshot_module, "PREDICTION_NORMS_SOURCE_PATH", source_path)

    official = load_prediction_norms_snapshot(source="official")
    my_database = load_prediction_norms_snapshot(source="my_database")

    assert set(official["trait_baselines"]) == {"uid:official", "uid:custom"}
    assert official["trait_baselines"]["uid:official"]["db_average"] == 51.0
    assert official["population_snapshot_id"] == "official"
    assert set(my_database["trait_baselines"]) == {"uid:custom"}
    assert my_database["population_snapshot_id"] == "local"
    assert my_database["trait_extension_snapshot_id"] == ""
    assert json.loads(official_path.read_text(encoding="utf-8"))["snapshot_id"] == "official"


def test_norm_source_selection_is_persisted_without_mutating_snapshots(tmp_path, monkeypatch):
    source_path = tmp_path / "source.json"
    official_path = tmp_path / "official.json"
    official_path.write_text('{"version": 1, "snapshot_id": "official"}', encoding="utf-8")
    monkeypatch.setattr(snapshot_module, "PREDICTION_NORMS_SOURCE_PATH", source_path)
    monkeypatch.setattr(snapshot_module, "OFFICIAL_PREDICTION_NORMS_SNAPSHOT_PATH", official_path)

    assert snapshot_module.load_prediction_norms_source() == "official"
    snapshot_module.save_prediction_norms_source("my_database")

    assert snapshot_module.load_prediction_norms_source() == "my_database"
    assert json.loads(official_path.read_text(encoding="utf-8"))["snapshot_id"] == "official"


def test_deleted_trait_is_removed_without_rebuilding_other_snapshot_rows(tmp_path):
    path = tmp_path / "norms.json"
    original = {
        "version": 1,
        "snapshot_id": "before",
        "trait_baselines": {
            "uid:delete-me": {"uid": "delete-me", "name": "Delete Me", "db_average": 40.0},
            "uid:keep-me": {"uid": "keep-me", "name": "Keep Me", "db_average": 60.0},
        },
        "retired_trait_keys": ["uid:delete-me", "uid:keep-me"],
    }
    save_prediction_norms_snapshot(original, path)

    updated = remove_trait_from_prediction_norms_snapshot(trait_uid="delete-me", path=path)

    assert set(updated["trait_baselines"]) == {"uid:keep-me"}
    assert updated["trait_baselines"]["uid:keep-me"] == original["trait_baselines"]["uid:keep-me"]
    assert updated["retired_trait_keys"] == ["uid:keep-me"]
    assert load_prediction_norms_snapshot(path) == updated


def test_deleted_uid_trait_does_not_remove_uidless_baseline_with_same_name(tmp_path):
    path = tmp_path / "norms.json"
    save_prediction_norms_snapshot(
        {
            "version": 1,
            "snapshot_id": "before",
            "trait_baselines": {
                "uid:custom-good": {"uid": "custom-good", "name": "Good", "db_average": 61.0},
                "profile:alignment-good": {"uid": "", "name": "Good", "db_average": 54.0},
            },
            "retired_trait_keys": [],
        },
        path,
    )

    updated = remove_trait_from_prediction_norms_snapshot(
        trait_uid="custom-good", trait_name="Good", path=path
    )

    assert set(updated["trait_baselines"]) == {"profile:alignment-good"}


def test_archiving_retains_norm_and_only_toggles_retired_membership(tmp_path):
    path = tmp_path / "norms.json"
    original_row = {"uid": "stable", "name": "Stable", "db_average": 52.5}
    save_prediction_norms_snapshot(
        {
            "version": 1,
            "snapshot_id": "stable-snapshot",
            "trait_baselines": {"uid:stable": original_row},
            "retired_trait_keys": [],
        },
        path,
    )
    trait = {"uid": "stable", "name": "Stable", "profile": {}}

    archived = set_trait_retired_in_prediction_norms_snapshot(trait, retired=True, path=path)
    reactivated = set_trait_retired_in_prediction_norms_snapshot(trait, retired=False, path=path)

    assert archived["trait_baselines"]["uid:stable"] == original_row
    assert archived["retired_trait_keys"] == ["uid:stable"]
    assert reactivated["trait_baselines"]["uid:stable"] == original_row
    assert reactivated["retired_trait_keys"] == []
