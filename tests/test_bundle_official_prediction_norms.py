import json
from pathlib import Path

import pytest

from ephemeraldaddy.analysis.theme_prominence import theme_definition_signature
from ephemeraldaddy.core.theme_reference import THEME_FAMILIES
from tools.bundle_official_prediction_norms import bundle_snapshot


def _theme_snapshot_fields() -> dict[str, object]:
    return {
        "theme_family_definition_signature": theme_definition_signature(),
        "theme_family_raw_averages": {
            family_key: 50.0 for family_key in THEME_FAMILIES
        },
    }


def test_official_norm_catalog_is_packaged_with_analysis_assets():
    root = Path(__file__).resolve().parents[1]
    assert (root / "ephemeraldaddy/analysis/default_prediction_norms.json").is_file()
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert '"default_prediction_norms.json"' in pyproject


def test_bundle_official_snapshot_requires_real_cohort_complete_traits_and_themes(tmp_path):
    source = tmp_path / "snapshot.json"
    destination = tmp_path / "official.json"
    source.write_text(
        json.dumps(
            {
                "version": 1,
                "snapshot_id": "developer-snapshot",
                "chart_count": 2001,
                "trait_baselines": {
                    "uid:doctor": {
                        "uid": "doctor",
                        "name": "Doctor",
                        "profile_hash": "profile-hash",
                        "db_average": 53.25,
                    }
                },
                **_theme_snapshot_fields(),
            }
        ),
        encoding="utf-8",
    )

    bundled = bundle_snapshot(source, destination)

    assert bundled["source"] == "bundled_official"
    assert bundled["read_only"] is True
    assert bundled["complete"] is True
    assert bundled["validated_theme_family_count"] == len(THEME_FAMILIES)
    assert json.loads(destination.read_text(encoding="utf-8")) == bundled


def test_bundle_official_snapshot_rejects_empty_placeholder(tmp_path):
    source = tmp_path / "snapshot.json"
    source.write_text(
        json.dumps({"version": 1, "chart_count": 0, "trait_baselines": {}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="non-empty developer cohort"):
        bundle_snapshot(source, tmp_path / "official.json")


def test_bundle_official_snapshot_rejects_missing_theme_baselines(tmp_path):
    source = tmp_path / "snapshot.json"
    source.write_text(
        json.dumps(
            {
                "version": 1,
                "snapshot_id": "developer-snapshot",
                "chart_count": 2001,
                "trait_baselines": {
                    "uid:doctor": {
                        "uid": "doctor",
                        "name": "Doctor",
                        "profile_hash": "profile-hash",
                        "db_average": 53.25,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="current Theme definitions"):
        bundle_snapshot(source, tmp_path / "official.json")
