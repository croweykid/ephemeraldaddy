from __future__ import annotations

from pathlib import Path

from ephemeraldaddy.gui.features.charts.similarities.cohort_metadata import (
    antisample_uids_for_profile,
    chart_uid_is_anti_ascribed,
    sample_uids_for_profile,
)
from ephemeraldaddy.gui.features.charts.trait_sample_markers import _marked_name
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
