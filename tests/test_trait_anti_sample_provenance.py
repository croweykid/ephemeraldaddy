from __future__ import annotations

from pathlib import Path

from ephemeraldaddy.gui.features.similarities.cohort_metadata import (
    antisample_uids_for_profile,
    chart_uid_is_anti_ascribed,
    sample_uids_for_profile,
)
from ephemeraldaddy.gui.features.charts.trait_sample_markers import (
    _marked_name,
    _rankings_rows_with_sample_markers,
)
from ephemeraldaddy.gui.features.settings import trait_anti_import


def test_cohort_metadata_supports_legacy_positive_and_canonical_anti_samples():
    profile = {
        "chartUIDs": [" abc ", "DEF"],
        "antisample_uids": [" ghi "],
    }

    assert sample_uids_for_profile(profile) == (" abc ", "DEF")
    assert antisample_uids_for_profile(profile) == (" ghi ",)
    assert chart_uid_is_anti_ascribed(profile, "GHI")


def test_trait_sample_marker_combinations():
    assert _marked_name("Trait", {"Trait"}) == "🧚 Trait"
    assert _marked_name("Trait", set(), {"Trait"}) == "👹 Trait"
    assert _marked_name("Trait", {"Trait"}, {"Trait"}) == "🧚👹 Trait"


def test_rankings_chart_names_show_sample_provenance_without_mutating_rows():
    traits = [
        {
            "name": "Trait",
            "profile": {
                "sample_uids": ["POSITIVE", "BOTH"],
                "antisample_uids": ["ANTI", "BOTH"],
            },
        }
    ]
    rows = [
        {"chart_uid": "positive", "name": "Positive", "likelihood": 90.0},
        {"chart_uid": "anti", "name": "Anti", "likelihood": 80.0},
        {"chart_uid": "both", "name": "Both", "likelihood": 70.0},
        {"chart_uid": "neither", "name": "Neither", "likelihood": 60.0},
    ]

    displayed = _rankings_rows_with_sample_markers("Trait", rows, traits)

    assert [row["name"] for row in displayed] == [
        "🧚 Positive",
        "👹 Anti",
        "🧚👹 Both",
        "Neither",
    ]
    assert [row["chart_uid"] for row in displayed] == [
        "positive",
        "anti",
        "both",
        "neither",
    ]
    assert [row["name"] for row in rows] == ["Positive", "Anti", "Both", "Neither"]


def test_rankings_chart_name_marker_accepts_legacy_positive_chart_uids():
    traits = [{"name": "Legacy", "chartUIDs": [" legacy-uid "]}]
    rows = [{"chart_uid": "LEGACY-UID", "name": "Legacy Chart"}]

    displayed = _rankings_rows_with_sample_markers("Legacy", rows, traits)

    assert displayed[0]["name"] == "🧚 Legacy Chart"
    assert rows[0]["name"] == "Legacy Chart"


def test_load_anti_trait_uses_only_source_positive_samples(monkeypatch, tmp_path):
    source = {
        "Source": {
            "signs": {"aries": 1.0},
            "chartUIDs": [" a ", "B", "A"],
            "antisample_uids": ["SHOULD-NOT-COPY"],
        }
    }
    monkeypatch.setattr(
        trait_anti_import.trait_store,
        "parse_trait_file",
        lambda _path: source,
    )

    anti_properties, source_uids = trait_anti_import.load_anti_trait_from_file(
        tmp_path / "source.json"
    )

    assert anti_properties == {"antisigns": {"aries": 1.0}}
    assert source_uids == ("A", "B")


def test_apply_anti_properties_appends_provenance_without_touching_positive_samples(
    monkeypatch,
    tmp_path,
):
    target_path = tmp_path / "target.json"
    target_profile = {
        "Target": {
            "sample_uids": ["POSITIVE"],
            "antisample_uids": ["old", " DUP "],
            "antisigns": {"taurus": 0.5},
        }
    }
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        trait_anti_import.trait_store,
        "parse_trait_file",
        lambda _path: target_profile,
    )

    def fake_rewrite(path, updates):
        captured.update(updates)
        return Path(path)

    monkeypatch.setattr(
        trait_anti_import.trait_store,
        "_rewrite_single_trait",
        fake_rewrite,
    )

    trait_anti_import.apply_anti_properties_to_trait(
        target_path,
        {"antisigns": {"aries": 1.0}},
        replace=False,
        source_sample_uids=["dup", " NEW ", "new"],
    )

    assert captured["antisample_uids"] == ["OLD", "DUP", "NEW"]
    assert "sample_uids" not in captured
    assert captured["antisigns"] == {"taurus": 0.5, "aries": 1.0}


def test_apply_anti_properties_replaces_provenance(monkeypatch, tmp_path):
    target_path = tmp_path / "target.json"
    target_profile = {
        "Target": {
            "sample_uids": ["POSITIVE"],
            "antisample_uids": ["OLD"],
            "antisigns": {"taurus": 0.5},
        }
    }
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        trait_anti_import.trait_store,
        "parse_trait_file",
        lambda _path: target_profile,
    )

    def fake_rewrite(path, updates):
        captured.update(updates)
        return Path(path)

    monkeypatch.setattr(
        trait_anti_import.trait_store,
        "_rewrite_single_trait",
        fake_rewrite,
    )

    trait_anti_import.apply_anti_properties_to_trait(
        target_path,
        {"antisigns": {"aries": 1.0}},
        replace=True,
        source_sample_uids=[" new ", "NEW", "OTHER"],
    )

    assert captured["antisample_uids"] == ["NEW", "OTHER"]
    assert "sample_uids" not in captured
