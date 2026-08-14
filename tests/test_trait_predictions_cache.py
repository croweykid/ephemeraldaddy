from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

ROOT = Path(__file__).resolve().parents[1]

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


def _chart_row(chart_id: int, name: str, chart_uid: str, *, datetime_iso: str = "") -> tuple:
    """Build the subset of a list_charts row needed by the UID-first cache."""
    row = [None] * 31
    row[0] = chart_id
    row[1] = name
    row[4] = datetime_iso
    row[30] = chart_uid
    return tuple(row)


def test_stale_trait_norm_cache_remains_usable_until_background_refresh(tmp_path, monkeypatch):
    cache_path = tmp_path / "trait_db_norms.json"
    monkeypatch.setattr(trait_predictions, "TRAIT_DB_NORMS_CACHE_PATH", cache_path)
    trait = {"name": "Creative", "color": "#ffffff", "profile": {"signs": {"Leo": 1}}}
    cache_key = trait_predictions._trait_norm_cache_key(("UID1", "UID2"), trait)
    renamed_trait = {"name": "Renamed", "color": "#123456", "profile": {"signs": {"Leo": 1}}}
    assert trait_predictions._trait_norm_cache_key(("UID1", "UID2"), renamed_trait) == cache_key
    cache_path.write_text(
        trait_predictions.json.dumps(
            {
                "version": trait_predictions.TRAIT_DB_NORMS_CACHE_VERSION,
                "entries": {
                    cache_key: {
                        "trait_name": "Creative",
                        "db_average": 63.5,
                        "chart_count": 10,
                        "norm_state": {
                            "version": trait_predictions.TRAIT_DB_NORMS_CACHE_VERSION,
                            "chart_count": 10,
                            "chart_tokens": {"UID1": "old"},
                        },
                        "norm_signature": "old-norm-signature",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    owner = _TraitsCacheOwner(
        (("uid:one", "row"),),
        chart_rows=[
            (1, "One", None, None, "", None, "", 0, 0, 0, None, 0, None, 0, "Natal", 0, 0, None, None, None, None, None, None, "blank", None, None, None, None, None, None, "UID1"),
            (2, "Two", None, None, "", None, "", 0, 0, 0, None, 0, None, 0, "Natal", 0, 0, None, None, None, None, None, None, "blank", None, None, None, None, None, None, "UID2"),
            (3, "Three", None, None, "", None, "", 0, 0, 0, None, 0, None, 0, "Natal", 0, 0, None, None, None, None, None, None, "blank", None, None, None, None, None, None, "UID3"),
        ],
    )

    def fail_collect(*_args, **_kwargs):
        raise AssertionError("stale persistent DB norms should remain readable synchronously")

    owner._collect_traits_distribution_analytics = fail_collect
    owner._traits_distribution_signature = lambda traits: tuple(
        (item["name"], "#ffffff", repr(item.get("profile", {}))) for item in traits
    )

    assert trait_predictions._database_trait_averages(owner, [trait]) == {"Creative": 63.5}
    assert trait_predictions._database_norm_signature_for_traits(owner, [trait]) == "old-norm-signature"


def test_forced_trait_norm_refresh_recomputes_stale_cache(tmp_path, monkeypatch):
    cache_path = tmp_path / "trait_db_norms.json"
    monkeypatch.setattr(trait_predictions, "TRAIT_DB_NORMS_CACHE_PATH", cache_path)
    trait = {"name": "Creative", "color": "#ffffff", "profile": {"signs": {"Leo": 1}}}
    cache_key = trait_predictions._trait_norm_cache_key(("UID1", "UID2"), trait)
    cache_path.write_text(
        trait_predictions.json.dumps(
            {
                "version": trait_predictions.TRAIT_DB_NORMS_CACHE_VERSION,
                "entries": {
                    cache_key: {
                        "trait_name": "Creative",
                        "db_average": 63.5,
                        "chart_count": 1,
                        "norm_state": {
                            "version": trait_predictions.TRAIT_DB_NORMS_CACHE_VERSION,
                            "chart_count": 1,
                            "chart_tokens": {"UID1": "old"},
                        },
                        "norm_signature": "old-norm-signature",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    owner = _TraitsCacheOwner(
        (("uid:one", "row"),),
        chart_rows=[
            (1, "One", None, None, "", None, "", 0, 0, 0, None, 0, None, 0, "Natal", 0, 0, None, None, None, None, None, None, "blank", None, None, None, None, None, None, "UID1"),
            (2, "Two", None, None, "", None, "", 0, 0, 0, None, 0, None, 0, "Natal", 0, 0, None, None, None, None, None, None, "blank", None, None, None, None, None, None, "UID2"),
        ],
    )
    owner._traits_distribution_signature = lambda traits: tuple(
        (item["name"], "#ffffff", repr(item.get("profile", {}))) for item in traits
    )

    def collect(_chart_uids, *, trait_items, trait_signature):
        assert set(_chart_uids) == {"UID1", "UID2"}
        assert [item["name"] for item in trait_items] == ["Creative"]
        return {"trait_names": ["Creative"], "totals": {"Creative": 1.7}, "chart_count": 2}

    owner._collect_traits_distribution_analytics_by_uids = collect

    assert trait_predictions._database_trait_averages(owner, [trait], force_refresh_stale=True) == {"Creative": 85.0}


def test_database_chart_uids_reads_appended_list_charts_uid_slot(monkeypatch):
    owner = _TraitsCacheOwner(
        (("uid:one", "row"),),
        chart_rows=[
            (
                101,
                "Name",
                None,
                None,
                "",
                None,
                "",
                0,
                0,
                0,
                None,
                0,
                None,
                0,
                "Natal",
                0,
                0,
                None,
                None,
                None,
                None,
                None,
                None,
                "blank",
                None,
                None,
                None,
                None,
                None,
                None,
                "UIDTRAIT0001",
            )
        ],
    )

    def fail_get_chart_uid_map(_chart_ids):
        raise AssertionError("UID should be read from row slot 30 without fallback")

    monkeypatch.setattr(trait_predictions.db, "get_chart_uid_map", fail_get_chart_uid_map)

    assert trait_predictions._database_chart_uids(owner) == ("UIDTRAIT0001",)


def test_traits_distribution_likelihood_cache_persists_across_matching_sessions(tmp_path, monkeypatch):
    from ephemeraldaddy.core import db

    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    trait_signature = (("Creative", "#ffffff", "{}"),)
    first_session = _TraitsCacheOwner(
        (("uid:one", "row"),),
        chart_rows=[_chart_row(101, "One", "UID101")],
    )
    first_session._traits_distribution_chart_likelihood_cache = {
        (0, trait_signature, "UID101"): {"Creative": 87.5}
    }

    first_session._save_traits_distribution_likelihood_cache()

    next_session = _TraitsCacheOwner(
        (("uid:one", "row"),),
        chart_rows=[_chart_row(101, "One", "UID101")],
    )
    assert next_session._load_traits_distribution_likelihood_cache() is True
    assert next_session._traits_distribution_individual_profile_likelihood_cache == {
        ("{}", "UID101"): 87.5
    }


def test_traits_distribution_likelihood_cache_rejects_changed_chart_rows_only(tmp_path, monkeypatch):
    from ephemeraldaddy.core import db

    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    first_session = _TraitsCacheOwner(
        (("uid:one", "row"),),
        chart_rows=[
            _chart_row(101, "Original", "UID101", datetime_iso="2000-01-01T00:00:00"),
            _chart_row(202, "Unchanged", "UID202", datetime_iso="2000-01-01T00:00:00"),
        ],
    )
    trait_signature = (("Creative", "#ffffff", "{}"),)
    first_session._traits_distribution_chart_likelihood_cache = {
        (0, trait_signature, "UID101"): {"Creative": 87.5},
        (0, trait_signature, "UID202"): {"Creative": 42.0},
    }
    first_session._save_traits_distribution_likelihood_cache()

    next_session = _TraitsCacheOwner(
        (("uid:two", "row"),),
        chart_rows=[
            _chart_row(101, "Changed", "UID101", datetime_iso="2001-01-01T00:00:00"),
            _chart_row(202, "Unchanged", "UID202", datetime_iso="2000-01-01T00:00:00"),
        ],
    )

    assert next_session._load_traits_distribution_likelihood_cache() is True
    assert next_session._traits_distribution_chart_likelihood_cache == {}
    assert next_session._traits_distribution_individual_likelihood_cache == {}
    assert next_session._traits_distribution_individual_profile_likelihood_cache == {
        ("{}", "UID202"): 42.0
    }


def test_traits_distribution_collection_stops_after_time_budget(monkeypatch):
    owner = _TraitsCacheOwner(
        (("uid:one", "row"),),
        chart_rows=[_chart_row(index, str(index), f"UID{index}") for index in (1, 2, 3)],
    )
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

    result = owner._collect_traits_distribution_analytics_by_uids(
        ["UID1", "UID2", "UID3"],
        trait_items=[{"name": "Creative", "profile": {}}],
        trait_signature=(("Creative", "#ffffff", "{}"),),
        time_budget_seconds=0.5,
    )

    assert result["partial"] is True
    assert result["requested_chart_count"] == 3
    assert result["chart_count"] == 1
    assert calls == [1]


def test_traits_distribution_collection_uses_warm_cache_past_time_budget(monkeypatch):
    owner = _TraitsCacheOwner(
        (("uid:one", "row"),),
        chart_rows=[_chart_row(index, str(index), f"UID{index}") for index in (1, 2)],
    )
    signature = (("Creative", "#ffffff", "{}"),)
    owner._traits_distribution_chart_likelihood_cache = {
        (0, signature, "UID1"): {"Creative": 80.0},
        (0, signature, "UID2"): {"Creative": 60.0},
    }
    owner._get_chart_for_filter = lambda chart_id: {"id": chart_id}
    owner._is_placeholder_chart = lambda _chart: False

    monkeypatch.setattr("ephemeraldaddy.gui.features.charts.database_analytics.time.monotonic", lambda: 10_000.0)

    result = owner._collect_traits_distribution_analytics_by_uids(
        ["UID1", "UID2"],
        trait_items=[{"name": "Creative", "profile": {}}],
        trait_signature=signature,
        time_budget_seconds=0.0,
    )

    assert result["partial"] is False
    assert result["chart_count"] == 2
    assert result["totals"]["Creative"] == 1.4


def test_traits_distribution_collection_scores_only_new_trait_when_existing_trait_cached(monkeypatch):
    owner = _TraitsCacheOwner((("uid:one", "row"),), chart_rows=[_chart_row(1, "1", "UID1")])
    owner._traits_distribution_chart_likelihood_cache = {}
    owner._traits_distribution_individual_likelihood_cache = {
        (("Creative", "#ffffff", "{}"), "UID1"): 80.0,
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
    result = owner._collect_traits_distribution_analytics_by_uids(
        ["UID1"],
        trait_items=[{"name": "Creative", "profile": {}}, {"name": "Analytical", "profile": {}}],
        trait_signature=signature,
        time_budget_seconds=None,
    )

    assert scored_trait_batches == [["Analytical"]]
    assert result["partial"] is False
    assert result["totals"] == {"Creative": 0.8, "Analytical": 0.65}
    assert owner._traits_distribution_chart_likelihood_cache[(0, signature, "UID1")] == {
        "Creative": 80.0,
        "Analytical": 65.0,
    }


def test_traits_distribution_collection_reuses_cache_after_trait_rename(monkeypatch):
    owner = _TraitsCacheOwner((("uid:one", "row"),), chart_rows=[_chart_row(1, "1", "UID1")])
    old_signature = (("Old Name", "#ffffff", '{"signs":{"Leo":1}}'),)
    new_signature = (("New Name", "#123456", '{"signs":{"Leo":1}}'),)
    owner._traits_distribution_chart_likelihood_cache = {}
    owner._traits_distribution_individual_likelihood_cache = {
        (old_signature[0], "UID1"): 82.0,
    }
    owner._traits_distribution_individual_profile_likelihood_cache = {
        ('{"signs":{"Leo":1}}', "UID1"): 82.0,
    }
    owner._get_chart_for_filter = lambda chart_id: {"id": chart_id}
    owner._is_placeholder_chart = lambda _chart: False

    def fail_likelihoods(*_args, **_kwargs):
        raise AssertionError("display-only trait edits should not force rescoring")

    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.charts.database_analytics.calculate_trait_likelihoods",
        fail_likelihoods,
    )

    result = owner._collect_traits_distribution_analytics_by_uids(
        ["UID1"],
        trait_items=[{"name": "New Name", "color": "#123456", "profile": {"signs": {"Leo": 1}}}],
        trait_signature=new_signature,
        time_budget_seconds=None,
    )

    assert result["partial"] is False
    assert result["totals"] == {"New Name": 0.82}
    assert owner._traits_distribution_chart_likelihood_cache[(0, new_signature, "UID1")] == {"New Name": 82.0}


def test_traits_distribution_collection_passively_persists_uid_trait_metadata(monkeypatch):
    owner = _TraitsCacheOwner(
        (("uid:one", "row"),),
        chart_rows=[
            _chart_row(1, "1", "UIDTRAIT0001"),
            _chart_row(2, "2", "UIDTRAIT0002"),
        ],
    )
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

    result = owner._collect_traits_distribution_analytics_by_uids(
        ["UIDTRAIT0001", "UIDTRAIT0002"],
        trait_items=[{"name": "Creative", "profile": {}}],
        trait_signature=(("Creative", "#ffffff", "{}"),),
        time_budget_seconds=None,
    )

    assert result["partial"] is False
    assert [entry[0] for entry in saved] == ["UIDTRAIT0001", "UIDTRAIT0002"]
    assert saved[0][1][0]["direction"] == "above"
    assert saved[0][1][0]["db_average"] == 60.0
    assert saved[1][1][0]["direction"] == "below"


def test_trait_norm_cache_average_survives_trait_rename(tmp_path, monkeypatch):
    cache_path = tmp_path / "trait_db_norms.json"
    monkeypatch.setattr(trait_predictions, "TRAIT_DB_NORMS_CACHE_PATH", cache_path)
    original_trait = {"name": "Creative", "color": "#ffffff", "profile": {"signs": {"Leo": 1}}}
    renamed_trait = {"name": "Expressive", "color": "#ffffff", "profile": {"signs": {"Leo": 1}}}
    cache_key = trait_predictions._trait_norm_cache_key(("UID1",), original_trait)
    cache_path.write_text(
        trait_predictions.json.dumps(
            {
                "version": trait_predictions.TRAIT_DB_NORMS_CACHE_VERSION,
                "entries": {
                    cache_key: {
                        "trait_name": "Creative",
                        "db_average": 72.25,
                        "chart_count": 1,
                        "norm_state": {
                            "version": trait_predictions.TRAIT_DB_NORMS_CACHE_VERSION,
                            "chart_count": 1,
                            "chart_tokens": {"UID1": "same"},
                        },
                        "norm_signature": "saved-norm-signature",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    owner = _TraitsCacheOwner(
        (("uid:one", "row"),),
        chart_rows=[
            (1, "One", None, None, "", None, "", 0, 0, 0, None, 0, None, 0, "Natal", 0, 0, None, None, None, None, None, None, "blank", None, None, None, None, None, None, "UID1"),
        ],
    )

    def fail_collect(*_args, **_kwargs):
        raise AssertionError("renamed traits should reuse UID/profile keyed DB norm averages")

    owner._collect_traits_distribution_analytics = fail_collect
    owner._traits_distribution_signature = lambda traits: tuple(
        (item["name"], "#ffffff", repr(item.get("profile", {}))) for item in traits
    )

    assert trait_predictions._database_trait_averages(owner, [renamed_trait]) == {"Expressive": 72.25}


def test_chart_view_and_dnd_trait_likelihoods_use_shared_distribution_cache_source():
    trait_source = (ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "trait_predictions.py").read_text(
        encoding="utf-8"
    )
    dnd_source = (ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "dnd_predictions.py").read_text(
        encoding="utf-8"
    )

    assert "def trait_likelihoods_with_distribution_cache" in trait_source
    assert "_collect_traits_distribution_analytics" in trait_source
    assert "trait_likelihoods_with_distribution_cache(owner, chart, missing_traits)" in trait_source
    assert "trait_likelihoods_with_distribution_cache(owner, chart, trait_items)" in dnd_source


def test_dnd_statblock_reuses_precomputed_db_norm_averages_source():
    source = (ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "dnd_predictions.py").read_text(
        encoding="utf-8"
    )
    method = source.split("    def _score_statblock", 1)[1].split("    def _render_statblock", 1)[0]
    assert "db_norm_averages = _calculate_db_norm_stat_averages(norm_charts)" in method
    assert "score_dnd_statblock(chart, norm_charts=norm_charts, db_norm_averages=db_norm_averages)" in method


def test_chart_view_traits_render_uses_persisted_metadata_before_calculate_prompt_source():
    source = (ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "trait_predictions.py").read_text(
        encoding="utf-8"
    )
    render_method = source.split("def render_traits_predictions", 1)[1]
    assert "trait_metadata_for_chart(owner, chart, cached_only=True)" in render_method
    assert "_traits_prediction_view_cache" not in render_method
    assert render_method.index("trait_metadata_for_chart(owner, chart, cached_only=True)") < render_method.index("_traits_calculate_prompt_html()")
    assert "_traits_stale_recalculate_prompt_html" in render_method


def test_dnd_statblock_popout_defines_db_norm_averages_parameter_source():
    source = (ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "dnd_predictions.py").read_text(
        encoding="utf-8"
    )
    function = source.split("def build_dnd_statblock_popout_info_html", 1)[1].split("def _stat_value_color", 1)[0]
    assert "db_norm_averages: Any = None" in function
    assert "score_dnd_statblock(chart, norm_charts=norm_charts, db_norm_averages=db_norm_averages)" in function
    assert 'getattr(statblock, "_db_norm_averages", None) or db_norm_averages' in function
