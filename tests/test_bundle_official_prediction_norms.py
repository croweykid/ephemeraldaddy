import json
from pathlib import Path

import pytest

from tools.bundle_official_prediction_norms import bundle_snapshot


def test_official_norm_catalog_is_packaged_with_analysis_assets():
    root = Path(__file__).resolve().parents[1]
    assert (root / "ephemeraldaddy/analysis/default_prediction_norms.json").is_file()
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert '"default_prediction_norms.json"' in pyproject


def test_bundle_official_snapshot_requires_real_cohort_and_complete_rows(tmp_path):
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
            }
        ),
        encoding="utf-8",
    )

    bundled = bundle_snapshot(source, destination)

    assert bundled["source"] == "bundled_official"
    assert bundled["read_only"] is True
    assert bundled["complete"] is True
    assert json.loads(destination.read_text(encoding="utf-8")) == bundled


def test_bundle_official_snapshot_rejects_empty_placeholder(tmp_path):
    source = tmp_path / "snapshot.json"
    source.write_text(
        json.dumps({"version": 1, "chart_count": 0, "trait_baselines": {}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="non-empty developer cohort"):
        bundle_snapshot(source, tmp_path / "official.json")
