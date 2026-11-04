import json
from types import SimpleNamespace

import pytest

from ephemeraldaddy.analysis import traits
from ephemeraldaddy.analysis.trait_reviews import (
    normalize_accuracy_rankings, perceived_accuracy, save_trait_review, without_trait_reviews,
)
from ephemeraldaddy.gui.features.charts.database_norms_cache import analytical_mapping_signature
from ephemeraldaddy.gui.features.charts import prediction_norms_snapshot_core as norms


@pytest.fixture
def catalog(tmp_path, monkeypatch):
    monkeypatch.setattr(traits, "TRAIT_DIR", tmp_path / "traits")
    defaults = tmp_path / "defaults.json"
    defaults.write_text(json.dumps({
        "Default": {"name": "Default", "uid": "default-fixed", "signs": {"Aries": 3}},
        "Other": {"name": "Other", "uid": "other-fixed", "signs": {"Cancer": 2}},
    }))
    monkeypatch.setattr(traits, "DEFAULT_TRAITS_PATH", defaults)
    return defaults


def test_old_traits_have_all_three_review_properties(catalog):
    trait = traits.list_traits()[0]
    assert trait["chart_accuracy_rankings"] == []
    assert trait["perceived_accuracy"] is None
    assert trait["astro_analysis"] == ""


def test_rating_validation_keeps_blank_uids_and_values_distinct():
    entries = normalize_accuracy_rankings([
        {"chart_uid": " a ", "value": 5},
        {"chart_uid": "A", "value": 1},
        {"chart_uid": "B", "value": True},
        {"chart_uid": "C", "value": 0},
        {"chart_uid": "D", "value": 6},
        {"chart_uid": "E", "value": None},
        {"chart_uid": "F", "value": "4"},
        {"chart_uid": "", "value": 3},
    ])
    assert [row["chart_uid"] for row in entries] == list("ABCDEF")
    assert [row["value"] for row in entries] == [5, None, None, None, None, None]
    assert perceived_accuracy(entries) == 5.0
    assert perceived_accuracy([]) is None


def test_custom_ratings_roundtrip_and_survive_rename(catalog):
    path = traits.save_trait("Custom", {"signs": {"Leo": 4}})
    trait = next(trait for trait in traits.list_traits() if trait["path"] == path)
    save_trait_review(trait, chart_accuracy_rankings=[
        {"chart_uid": "A", "value": 2},
        {"chart_uid": "B", "value": None},
        {"chart_uid": "C", "value": 5},
    ])
    save_trait_review(trait, astro_analysis="First paragraph.\n\nSecond paragraph.")
    new_path = traits.rename_trait(path, "Renamed")
    loaded = next(trait for trait in traits.list_traits() if trait["path"] == new_path)
    assert loaded["uid"] == trait["uid"]
    assert loaded["perceived_accuracy"] == 3.5
    assert loaded["profile"]["perceived_accuracy"] == 3.5
    assert loaded["astro_analysis"] == "First paragraph.\n\nSecond paragraph."
    assert loaded["profile"]["signs"] == {"Leo": 4}
    assert len(loaded["chart_accuracy_rankings"]) == 3
    save_trait_review(loaded, chart_accuracy_rankings=[{"chart_uid": "A", "value": None}])
    assert traits.parse_trait_file(new_path)["Renamed"]["perceived_accuracy"] is None


def test_bundled_reviews_are_uid_keyed_and_do_not_modify_packaged_traits(catalog):
    original = catalog.read_bytes()
    first, other = traits.list_traits()
    save_trait_review(first, chart_accuracy_rankings=[{"chart_uid": "CHART", "value": 4}])
    save_trait_review(other, astro_analysis="Separate local review")
    # A stale caller snapshot must not overwrite a rating saved by another action.
    save_trait_review(first, astro_analysis="A blind analysis")
    assert catalog.read_bytes() == original
    first, other = traits.list_traits()
    assert first["perceived_accuracy"] == 4.0
    assert first["astro_analysis"] == "A blind analysis"
    assert other["perceived_accuracy"] is None
    assert other["astro_analysis"] == "Separate local review"
    assert "astro_analysis" not in first["profile"]


def test_review_fields_do_not_change_norms_or_score_fingerprints(catalog):
    trait = traits.list_traits()[0]
    profile = trait["profile"]
    reviewed = {**profile, "chart_accuracy_rankings": [{"chart_uid": "A", "value": 3}],
                "perceived_accuracy": 3.0, "astro_analysis": "Prose"}
    assert without_trait_reviews(reviewed) == profile
    assert analytical_mapping_signature(reviewed) == analytical_mapping_signature(profile)
    base = norms._trait_payload(trait)
    snapshot = {"trait_baselines": {base["key"]: {**base, "db_average": 55.0}}}
    updated = {**trait, "profile": reviewed}
    assert norms._trait_payload(updated)["profile_hash"] == base["profile_hash"]
    assert norms.trait_snapshot_averages([updated], snapshot) == {trait["name"]: 55.0}
    assert traits._trait_possible_score_signature([trait]) == traits._trait_possible_score_signature([updated])


def test_review_save_rejects_scoring_edits(catalog):
    with pytest.raises(ValueError, match="Only Trait review"):
        save_trait_review(traits.list_traits()[0], signs={"Aries": 9})
    with pytest.raises(ValueError, match="derived"):
        save_trait_review(traits.list_traits()[0], perceived_accuracy=5.0)


def test_ranking_query_reuses_panel_pipeline_and_full_database(monkeypatch):
    from ephemeraldaddy.gui import ranking_panel_core as rankings

    calls = []
    trait = {"name": "T", "archived": True, "profile": {}}
    monkeypatch.setattr(rankings, "trait_snapshot_averages", lambda items: {"T": 60.0})
    monkeypatch.setattr(rankings.RankingsPanelMixin, "_rankings_database_chart_uids", lambda self: {"A", "B"})
    monkeypatch.setattr(rankings.RankingsPanelMixin, "_rankings_trait_likelihood_cache_complete",
                        lambda self, **kwargs: calls.append(("freshness", kwargs)))
    owner = SimpleNamespace(
        _traits_distribution_chart_likelihood_cache={},
        _traits_distribution_signature=lambda items: (("T", "color", "profile"),),
        _traits_distribution_chart_uid_by_id=lambda: {1: "A", 2: "B"},
        _collect_traits_distribution_analytics_by_uids=lambda uids, **kwargs: calls.append(("collect", uids, kwargs)) or {},
        _rankings_traits_chart_rankings=lambda **kwargs: calls.append(("rank", kwargs)) or [
            {"chart_uid": str(i), "deviation": 50 - i} for i in range(60)
        ],
    )
    rows = rankings.RankingsPanelMixin.trait_accuracy_rankings(owner, trait, lambda value: None, lambda: False)
    assert len(rows) == 40
    assert rows[0]["chart_uid"] == "0"
    assert calls[0][0] == "freshness"
    assert calls[1][1] == ("A", "B")
    assert calls[1][2]["trait_items"] == [{**trait, "archived": False}]
    assert calls[1][2]["time_budget_seconds"] is None
    assert calls[2][1]["database_values"] == {"T": 0.6}
    assert trait["archived"] is True


def test_ranking_query_does_not_invent_missing_db_norm(monkeypatch):
    from ephemeraldaddy.gui import ranking_panel_core as rankings

    monkeypatch.setattr(rankings, "trait_snapshot_averages", lambda items: {})
    with pytest.raises(ValueError, match="Stored DB norm unavailable"):
        rankings.RankingsPanelMixin.trait_accuracy_rankings(
            SimpleNamespace(), {"name": "T"}, lambda value: None, lambda: False,
        )
