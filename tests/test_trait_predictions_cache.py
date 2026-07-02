from ephemeraldaddy.gui.features.charts import trait_predictions
from ephemeraldaddy.gui.features.charts.database_analytics import DatabaseAnalyticsChartsMixin


def test_load_trait_norm_cache_logs_and_skips_corrupt_cache(tmp_path, monkeypatch, caplog):
    cache_path = tmp_path / "trait_db_norms.json"
    cache_path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(trait_predictions, "TRAIT_DB_NORMS_CACHE_PATH", cache_path)
    caplog.set_level("DEBUG", logger="ephemeraldaddy.gui.features.charts.trait_predictions")

    assert trait_predictions._load_trait_norm_cache() == {}

    assert "Traits panel skipped corrupt DB norm cache" in caplog.text
    assert str(cache_path) in caplog.text


class _TraitsCacheOwner(DatabaseAnalyticsChartsMixin):
    def __init__(self, rows_token):
        self.rows_token = rows_token
        self._database_metrics_cache_revision = 0

    def _database_metrics_rows_token(self):
        return self.rows_token

    def _encode_database_metrics_cache_value(self, value):
        return value


def test_traits_distribution_likelihood_cache_persists_across_matching_sessions(tmp_path, monkeypatch):
    from ephemeraldaddy.core import db

    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    trait_signature = (("Creative", "#ffffff", "{}"),)
    first_session = _TraitsCacheOwner((("uid:one", "row"),))
    first_session._traits_distribution_chart_likelihood_cache = {
        (0, trait_signature, 101): {"Creative": 87.5}
    }

    first_session._save_traits_distribution_likelihood_cache()

    next_session = _TraitsCacheOwner((("uid:one", "row"),))
    assert next_session._load_traits_distribution_likelihood_cache() is True
    assert next_session._traits_distribution_chart_likelihood_cache == {
        (0, trait_signature, 101): {"Creative": 87.5}
    }


def test_traits_distribution_likelihood_cache_rejects_changed_database_rows(tmp_path, monkeypatch):
    from ephemeraldaddy.core import db

    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    first_session = _TraitsCacheOwner((("uid:one", "row"),))
    first_session._traits_distribution_chart_likelihood_cache = {
        (0, (("Creative", "#ffffff", "{}"),), 101): {"Creative": 87.5}
    }
    first_session._save_traits_distribution_likelihood_cache()

    next_session = _TraitsCacheOwner((("uid:two", "row"),))
    assert next_session._load_traits_distribution_likelihood_cache() is False
    assert not hasattr(next_session, "_traits_distribution_chart_likelihood_cache")
