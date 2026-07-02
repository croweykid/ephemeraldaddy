from ephemeraldaddy.gui.features.charts import trait_predictions


def test_load_trait_norm_cache_logs_and_skips_corrupt_cache(tmp_path, monkeypatch, caplog):
    cache_path = tmp_path / "trait_db_norms.json"
    cache_path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(trait_predictions, "TRAIT_DB_NORMS_CACHE_PATH", cache_path)
    caplog.set_level("DEBUG", logger="ephemeraldaddy.gui.features.charts.trait_predictions")

    assert trait_predictions._load_trait_norm_cache() == {}

    assert "Traits panel skipped corrupt DB norm cache" in caplog.text
    assert str(cache_path) in caplog.text
