from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_SOURCE = (ROOT / "ephemeraldaddy" / "core" / "db.py").read_text(encoding="utf-8")
APP_SOURCE = (ROOT / "ephemeraldaddy" / "gui" / "app.py").read_text(encoding="utf-8")


def test_db_can_clear_one_dnd_prediction_metadata_section() -> None:
    assert "def clear_chart_dnd_prediction_metadata_section" in DB_SOURCE
    assert "metadata = get_all_chart_dnd_prediction_metadata()" in DB_SOURCE
    assert "updated_payload.pop(normalized_section, None)" in DB_SOURCE
    assert "upsert_chart_dnd_prediction_metadata(chart_uid, updated_payload)" in DB_SOURCE


def test_dev_tool_clears_memory_and_persisted_species_class_caches() -> None:
    method = APP_SOURCE.split("def _on_refresh_dnd_species_class_cache_in_db", 1)[1].split("def _on_recalculate_all_weights_in_db", 1)[0]
    assert 'clear_chart_dnd_prediction_metadata_section("species_class")' in method
    assert '_dnd_species_class_prediction_view_cache' in method
    assert '_dnd_species_search_filter_cache' in method
    assert 'delattr(chart, "_dnd_species_class_prediction_cache")' in method
    assert "adapter.cache_species_class_metadata(chart)" in method
