from __future__ import annotations

from tools.audit_prediction_norms import audit_trait_norm_coverage
from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import _stable_hash


def _trait(name: str, uid: str, *, value: int = 1) -> dict:
    profile = {
        "name": name,
        "uid": uid,
        "signs": {"Aries": value},
        "archived": False,
    }
    return {
        "name": name,
        "uid": uid,
        "trait_uid": uid,
        "profile": profile,
        "archived": False,
    }


def _row(trait: dict, *, row_name: str | None = None, db_average: float = 50.0) -> dict:
    return {
        "uid": trait["uid"],
        "name": row_name or trait["name"],
        "profile_hash": _stable_hash(trait["profile"]),
        "db_average": db_average,
    }


def test_audit_accepts_complete_trait_coverage():
    trait = _trait("comedian", "default_comedian")
    report = audit_trait_norm_coverage(
        [trait],
        {"trait_baselines": {"uid:default_comedian": _row(trait)}},
    )

    assert report["covered_count"] == 1
    assert report["issues"] == []


def test_audit_reports_duplicate_uid_before_snapshot_lookup():
    comedian = _trait("comedian", "default_comedian")
    cowboy = _trait("cowboy", "default_comedian")
    report = audit_trait_norm_coverage(
        [comedian, cowboy],
        {"trait_baselines": {"uid:default_comedian": _row(cowboy)}},
    )

    assert report["covered_count"] == 0
    assert [issue["reason"] for issue in report["issues"]] == [
        "duplicate_trait_key",
        "duplicate_trait_key",
    ]
    assert report["duplicate_keys"]["uid:default_comedian"] == ["comedian", "cowboy"]


def test_audit_distinguishes_wrong_row_owner_from_hash_mismatch():
    comedian = _trait("comedian", "default_comedian")
    wrong_owner = audit_trait_norm_coverage(
        [comedian],
        {
            "trait_baselines": {
                "uid:default_comedian": _row(comedian, row_name="cowboy")
            }
        },
    )
    assert wrong_owner["issues"][0]["reason"] == "row_owned_by_other_trait"

    changed = _trait("comedian", "default_comedian", value=2)
    stale = audit_trait_norm_coverage(
        [changed],
        {"trait_baselines": {"uid:default_comedian": _row(comedian)}},
    )
    assert stale["issues"][0]["reason"] == "profile_hash_mismatch"


def test_audit_reports_missing_and_orphan_rows():
    trait = _trait("treacherous", "custom_treacherous")
    report = audit_trait_norm_coverage(
        [trait],
        {
            "trait_baselines": {
                "uid:custom_other": {
                    "uid": "custom_other",
                    "name": "other",
                    "profile_hash": "x",
                    "db_average": 50.0,
                }
            }
        },
    )

    assert report["issues"][0]["reason"] == "missing_row"
    assert report["orphan_rows"] == ["uid:custom_other"]
