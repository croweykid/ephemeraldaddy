from types import SimpleNamespace

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
    def __init__(self, rows_token, chart_rows=None):
        self.rows_token = rows_token
        self._chart_rows = list(chart_rows or [])
        self._database_metrics_cache_revision = 0

    def _database_metrics_rows_token(self):
        return self.rows_token

    def _encode_database_metrics_cache_value(self, value):
        return value

    @staticmethod
    def _normalize_chart_row(row):
        return row


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


def test_traits_distribution_likelihood_cache_rejects_changed_chart_rows_only(tmp_path, monkeypatch):
    from ephemeraldaddy.core import db

    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    first_session = _TraitsCacheOwner(
        (("uid:one", "row"),),
        chart_rows=[(101, "Original"), (202, "Unchanged")],
    )
    trait_signature = (("Creative", "#ffffff", "{}"),)
    first_session._traits_distribution_chart_likelihood_cache = {
        (0, trait_signature, 101): {"Creative": 87.5},
        (0, trait_signature, 202): {"Creative": 42.0},
    }
    first_session._save_traits_distribution_likelihood_cache()

    next_session = _TraitsCacheOwner(
        (("uid:two", "row"),),
        chart_rows=[(101, "Changed"), (202, "Unchanged")],
    )

    assert next_session._load_traits_distribution_likelihood_cache() is True
    assert next_session._traits_distribution_chart_likelihood_cache == {
        (0, trait_signature, 202): {"Creative": 42.0}
    }
    assert next_session._traits_distribution_individual_likelihood_cache == {
        (("Creative", "#ffffff", "{}"), 202): 42.0
    }


def test_traits_distribution_collection_stops_after_time_budget(monkeypatch):
    owner = _TraitsCacheOwner((("uid:one", "row"),))
    owner._traits_distribution_chart_likelihood_cache = {}
    owner._get_chart_for_filter = lambda chart_id: {"id": chart_id}
    owner._is_placeholder_chart = lambda _chart: False
    owner._debug_chart_label = lambda chart: str(chart.get("id"))

    tick = {"value": 0.0}

    def fake_monotonic():
        tick["value"] += 1.0
        return tick["value"]

    calls = []

    def fake_likelihoods(chart, trait_items, possible_scores=None):
        calls.append(chart["id"])
        return {"Creative": 75.0}

    monkeypatch.setattr("ephemeraldaddy.gui.features.charts.database_analytics.time.monotonic", fake_monotonic)
    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.charts.database_analytics.calculate_trait_likelihoods",
        fake_likelihoods,
    )

    result = owner._collect_traits_distribution_analytics(
        [1, 2, 3],
        trait_items=[{"name": "Creative", "profile": {}}],
        trait_signature=(("Creative", "#ffffff", "{}"),),
        time_budget_seconds=0.5,
    )

    assert result["partial"] is True
    assert result["requested_chart_count"] == 3
    assert result["chart_count"] == 1
    assert calls == [1]


def test_traits_distribution_collection_uses_warm_cache_past_time_budget(monkeypatch):
    owner = _TraitsCacheOwner((("uid:one", "row"),))
    signature = (("Creative", "#ffffff", "{}"),)
    owner._traits_distribution_chart_likelihood_cache = {
        (0, signature, 1): {"Creative": 80.0},
        (0, signature, 2): {"Creative": 60.0},
    }
    owner._get_chart_for_filter = lambda chart_id: {"id": chart_id}
    owner._is_placeholder_chart = lambda _chart: False

    monkeypatch.setattr("ephemeraldaddy.gui.features.charts.database_analytics.time.monotonic", lambda: 10_000.0)

    result = owner._collect_traits_distribution_analytics(
        [1, 2],
        trait_items=[{"name": "Creative", "profile": {}}],
        trait_signature=signature,
        time_budget_seconds=0.0,
    )

    assert result["partial"] is False
    assert result["chart_count"] == 2
    assert result["totals"]["Creative"] == 1.4


def test_traits_distribution_collection_scores_only_new_trait_when_existing_trait_cached(monkeypatch):
    owner = _TraitsCacheOwner((("uid:one", "row"),))
    owner._traits_distribution_chart_likelihood_cache = {}
    owner._traits_distribution_individual_likelihood_cache = {
        (("Creative", "#ffffff", "{}"), 1): 80.0,
    }
    owner._get_chart_for_filter = lambda chart_id: {"id": chart_id}
    owner._is_placeholder_chart = lambda _chart: False
    owner._debug_chart_label = lambda chart: str(chart.get("id"))

    scored_trait_batches = []

    def fake_likelihoods(chart, trait_items, possible_scores=None):
        scored_trait_batches.append([trait["name"] for trait in trait_items])
        return {"Analytical": 65.0}

    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.charts.database_analytics.calculate_trait_likelihoods",
        fake_likelihoods,
    )

    signature = (
        ("Creative", "#ffffff", "{}"),
        ("Analytical", "#ffffff", "{}"),
    )
    result = owner._collect_traits_distribution_analytics(
        [1],
        trait_items=[{"name": "Creative", "profile": {}}, {"name": "Analytical", "profile": {}}],
        trait_signature=signature,
        time_budget_seconds=None,
    )

    assert scored_trait_batches == [["Analytical"]]
    assert result["partial"] is False
    assert result["totals"] == {"Creative": 0.8, "Analytical": 0.65}
    assert owner._traits_distribution_chart_likelihood_cache[(0, signature, 1)] == {
        "Creative": 80.0,
        "Analytical": 65.0,
    }


def test_traits_distribution_collection_passively_persists_uid_trait_metadata(monkeypatch):
    owner = _TraitsCacheOwner((("uid:one", "row"),))
    owner._traits_distribution_chart_likelihood_cache = {}
    owner._traits_distribution_individual_likelihood_cache = {}
    charts = {
        1: SimpleNamespace(id=1, chart_uid="UIDTRAIT0001"),
        2: SimpleNamespace(id=2, chart_uid="UIDTRAIT0002"),
    }
    owner._get_chart_for_filter = lambda chart_id: charts[int(chart_id)]
    owner._is_placeholder_chart = lambda _chart: False
    owner._debug_chart_label = lambda chart: str(getattr(chart, "id", ""))

    def fake_likelihoods(chart, trait_items, possible_scores=None):
        return {"Creative": 80.0 if chart.id == 1 else 40.0}

    saved = []

    def fake_upsert(chart_uid, rows, *, trait_signature, norm_signature, chart_signature=""):
        saved.append((chart_uid, rows, trait_signature, norm_signature))

    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.charts.database_analytics.calculate_trait_likelihoods",
        fake_likelihoods,
    )
    monkeypatch.setattr("ephemeraldaddy.gui.features.charts.database_analytics.db.upsert_chart_trait_metadata", fake_upsert)

    result = owner._collect_traits_distribution_analytics(
        [1, 2],
        trait_items=[{"name": "Creative", "profile": {}}],
        trait_signature=(("Creative", "#ffffff", "{}"),),
        time_budget_seconds=None,
    )

    assert result["partial"] is False
    assert [entry[0] for entry in saved] == ["UIDTRAIT0001", "UIDTRAIT0002"]
    assert saved[0][1][0]["direction"] == "above"
    assert saved[0][1][0]["db_average"] == 60.0
    assert saved[1][1][0]["direction"] == "below"
