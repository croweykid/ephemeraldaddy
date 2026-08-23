from __future__ import annotations

import json

import pytest

from tools.bundle_official_prediction_norms import (
    _stable_hash,
    prepare_local_source,
    validate_default_trait_coverage,
)


def _write_traits(path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _row(name: str, uid: str, profile: dict, average: float = 50.0) -> dict:
    return {
        "name": name,
        "uid": uid,
        "profile_hash": _stable_hash(profile),
        "db_average": average,
    }


def test_validate_default_trait_coverage_accepts_complete_snapshot(tmp_path):
    traits_path = _write_traits(
        tmp_path / "default_traits.json",
        {
            "comedian": {
                "name": "comedian",
                "uid": "default_comedian",
                "signs": {"Gemini": 2},
                "archived": False,
            },
            "archived": {
                "name": "archived",
                "uid": "default_archived",
                "signs": {},
                "archived": True,
            },
        },
    )
    comedian_profile = json.loads(traits_path.read_text(encoding="utf-8"))["comedian"]
    payload = {
        "trait_baselines": {
            "uid:default_comedian": _row(
                "comedian", "default_comedian", comedian_profile
            )
        }
    }

    result = validate_default_trait_coverage(payload, default_traits_path=traits_path)

    assert result["active_default_trait_count"] == 1


def test_validate_default_trait_coverage_rejects_duplicate_effective_uid(tmp_path):
    traits_path = _write_traits(
        tmp_path / "default_traits.json",
        {
            "comedian": {
                "name": "comedian",
                "signs": {"Gemini": 2},
                "archived": False,
            },
            "cowboy": {
                "name": "cowboy",
                "uid": "default_comedian",
                "signs": {},
                "archived": False,
            },
        },
    )

    with pytest.raises(ValueError, match="duplicate effective UIDs") as exc_info:
        validate_default_trait_coverage(
            {"trait_baselines": {}}, default_traits_path=traits_path
        )

    assert "comedian" in str(exc_info.value)
    assert "cowboy" in str(exc_info.value)
    assert "uid:default_comedian" in str(exc_info.value)


def test_validate_default_trait_coverage_rejects_missing_default(tmp_path):
    traits_path = _write_traits(
        tmp_path / "default_traits.json",
        {
            "famous scientist": {
                "name": "famous scientist",
                "uid": "default_famous_scientist",
                "signs": {"Aries": 25},
                "archived": False,
            }
        },
    )

    with pytest.raises(ValueError, match="missing row") as exc_info:
        validate_default_trait_coverage(
            {"trait_baselines": {}}, default_traits_path=traits_path
        )

    assert "famous scientist" in str(exc_info.value)


def test_validate_default_trait_coverage_rejects_wrong_row_owner(tmp_path):
    profile = {
        "name": "comedian",
        "uid": "default_comedian",
        "signs": {"Gemini": 2},
        "archived": False,
    }
    traits_path = _write_traits(tmp_path / "default_traits.json", {"comedian": profile})
    payload = {
        "trait_baselines": {
            "uid:default_comedian": _row(
                "cowboy", "default_comedian", profile
            )
        }
    }

    with pytest.raises(ValueError, match="belongs to snapshot row 'cowboy'"):
        validate_default_trait_coverage(payload, default_traits_path=traits_path)


def test_prepare_local_source_is_explicit_and_atomic(tmp_path):
    target = tmp_path / ".prediction_norms_source.json"

    result = prepare_local_source(target)

    assert result == target
    assert json.loads(target.read_text(encoding="utf-8")) == {"source": "my_database"}
