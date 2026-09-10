from __future__ import annotations

from collections import OrderedDict
from types import SimpleNamespace

from ephemeraldaddy.gui.features.charts.similarities.cohort_metadata import (
    build_gender_distribution,
    chart_uid_is_ascribed,
    chart_uids_from_mapping,
    inject_trait_cohort_metadata,
)


def _charts(gender: str, count: int):
    return [SimpleNamespace(gender=gender) for _ in range(count)]


def test_chart_uids_are_canonical_unique_and_name_independent() -> None:
    assert chart_uids_from_mapping(
        {
            1: " abc-123 ",
            2: "ABC-123",
            3: "def-456",
            4: "",
        }
    ) == ["ABC-123", "DEF-456"]


def test_gender_distribution_uses_chart_counts_and_flags_significance() -> None:
    selected = [*_charts("Female", 19), *_charts("Male", 1)]
    database = [*_charts("Female", 50), *_charts("Male", 50)]

    distribution = build_gender_distribution(selected, database)

    assert distribution is not None
    assert distribution["counts"] == {"Female": 19, "Male": 1}
    assert distribution["total"] == 20
    assert distribution["percentages"] == {"Female": 95.0, "Male": 5.0}
    assert distribution["databasePercentages"] == {"Female": 50.0, "Male": 50.0}
    assert distribution["statisticallySignificant"] is True
    assert set(distribution["significantCategories"]) == {"Female", "Male"}


def test_gender_distribution_omits_missing_gender_from_denominator() -> None:
    selected = [SimpleNamespace(gender="Female"), SimpleNamespace(gender=None)]
    database = [SimpleNamespace(gender="Female"), SimpleNamespace(gender="Male")]

    distribution = build_gender_distribution(selected, database)

    assert distribution is not None
    assert distribution["counts"] == {"Female": 1, "Male": 0}
    assert distribution["total"] == 1
    assert distribution["percentages"] == {"Female": 100.0, "Male": 0.0}
    assert distribution["statisticallySignificant"] is False


def test_trait_export_receives_original_source_sample_metadata() -> None:
    payload = OrderedDict(
        [
            (
                "sample trait",
                OrderedDict(
                    [
                        ("name", "sample trait"),
                        ("samples", [3, 0]),
                        ("model", ""),
                        ("signs", {}),
                    ]
                ),
            )
        ]
    )
    gender_distribution = OrderedDict(
        [
            ("counts", OrderedDict([("Female", 2), ("Male", 1)])),
            ("total", 3),
            ("statisticallySignificant", False),
        ]
    )

    inject_trait_cohort_metadata(
        payload,
        "sample trait",
        sample_uids=["uid-b", "UID-A", "uid-a"],
        gender_distribution=gender_distribution,
    )

    profile = payload["sample trait"]
    assert profile["sample_uids"] == ["UID-A", "UID-B"]
    assert "chartUIDs" not in profile
    assert profile["genderDistribution"] == gender_distribution


def test_dissimilarity_bundle_is_not_misidentified_as_trait_profile() -> None:
    payload = OrderedDict(
        [
            (
                "pair",
                OrderedDict(
                    [
                        ("name", "pair"),
                        ("samples", [2, 0]),
                        ("chart 1 unique factors", {"model": ""}),
                        ("chart 2 unique factors", {"model": ""}),
                    ]
                ),
            )
        ]
    )

    inject_trait_cohort_metadata(
        payload,
        "pair",
        sample_uids=["UID-A", "UID-B"],
        gender_distribution={"counts": {"Female": 1, "Male": 1}},
    )

    assert "sample_uids" not in payload["pair"]
    assert "chartUIDs" not in payload["pair"]
    assert "genderDistribution" not in payload["pair"]


def test_ascribed_lookup_prefers_sample_uids() -> None:
    profile = {
        "sample_uids": ["ABC-123", "DEF-456"],
        "name": "mutable display name",
    }

    assert chart_uid_is_ascribed(profile, " abc-123 ") is True
    assert chart_uid_is_ascribed(profile, "XYZ-999") is False


def test_ascribed_lookup_accepts_legacy_chart_uids() -> None:
    profile = {"chartUIDs": ["ABC-123", "DEF-456"]}

    assert chart_uid_is_ascribed(profile, "def-456") is True


def test_sample_uids_take_precedence_when_both_keys_exist() -> None:
    profile = {
        "sample_uids": [],
        "chartUIDs": ["LEGACY-UID"],
    }

    assert chart_uid_is_ascribed(profile, "LEGACY-UID") is False
