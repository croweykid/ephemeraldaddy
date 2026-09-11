import json
from pathlib import Path

import pytest
import tools.bundle_official_prediction_norms as bundler

from ephemeraldaddy.analysis.theme_prominence import theme_definition_signature
from ephemeraldaddy.analysis.theme_norms import (
    THEME_CHART_SHARE_SCHEMA_FIELD,
    THEME_CHART_SHARE_SCHEMA_VERSION,
    THEME_FACTOR_ACTIVATION_VALUES_FIELD,
    THEME_FAMILY_AVAILABILITY_ROWS_FIELD,
    THEME_FAMILY_SHARE_AVERAGES_FIELD,
    THEME_FAMILY_SHARE_VALUES_FIELD,
    THEME_NORMS_AVAILABILITY_SCHEMA_FIELD,
    THEME_NORMS_AVAILABILITY_SCHEMA_VERSION,
    THEME_SUBTHEME_SHARE_AVERAGES_FIELD,
    THEME_SUBTHEME_SHARE_VALUES_FIELD,
)
from ephemeraldaddy.core.theme_reference import THEMES, THEME_FAMILIES
from tools.bundle_official_prediction_norms import bundle_snapshot


_AVAILABILITY = "houses:1|hd:1|bazi:1"


@pytest.fixture(autouse=True)
def _isolate_theme_validation(monkeypatch):
    """Trait-definition coverage has dedicated tests in the companion module."""
    monkeypatch.setattr(
        bundler,
        "validate_default_trait_coverage",
        lambda _payload: {"active_default_trait_count": 1},
    )


def _legacy_theme_snapshot_fields() -> dict[str, object]:
    return {
        "theme_family_definition_signature": theme_definition_signature(),
        "theme_family_raw_averages": {
            family_key: 50.0 for family_key in THEME_FAMILIES
        },
        THEME_NORMS_AVAILABILITY_SCHEMA_FIELD: THEME_NORMS_AVAILABILITY_SCHEMA_VERSION,
        THEME_FAMILY_AVAILABILITY_ROWS_FIELD: {
            _AVAILABILITY: {
                family_key: 50.0 for family_key in THEME_FAMILIES
            }
        },
    }


def _theme_snapshot_fields() -> dict[str, object]:
    payload = _legacy_theme_snapshot_fields()
    payload.update(
        {
            THEME_CHART_SHARE_SCHEMA_FIELD: THEME_CHART_SHARE_SCHEMA_VERSION,
            THEME_FAMILY_SHARE_AVERAGES_FIELD: {
                _AVAILABILITY: {family_key: 10.0 for family_key in THEME_FAMILIES}
            },
            THEME_FAMILY_SHARE_VALUES_FIELD: {
                _AVAILABILITY: {
                    family_key: [9.0, 10.0, 11.0]
                    for family_key in THEME_FAMILIES
                }
            },
            THEME_SUBTHEME_SHARE_AVERAGES_FIELD: {
                _AVAILABILITY: {theme_key: 1.0 for theme_key in THEMES}
            },
            THEME_SUBTHEME_SHARE_VALUES_FIELD: {
                _AVAILABILITY: {
                    theme_key: [0.5, 1.0, 1.5] for theme_key in THEMES
                }
            },
            THEME_FACTOR_ACTIVATION_VALUES_FIELD: {
                _AVAILABILITY: {"signs:\"Aries\"": [0.0, 0.5, 1.0]}
            },
        }
    )
    return payload


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


def test_bundle_official_snapshot_rejects_missing_availability_strata(tmp_path):
    payload = {
        "version": 1,
        "chart_count": 1,
        "trait_baselines": {"row": {"profile_hash": "x", "db_average": 1.0}},
        **_theme_snapshot_fields(),
    }
    payload.pop(THEME_FAMILY_AVAILABILITY_ROWS_FIELD)
    source = tmp_path / "snapshot.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="raw_averages_by_availability"):
        bundle_snapshot(source, tmp_path / "official.json")


def test_bundle_official_snapshot_rejects_incomplete_availability_stratum(tmp_path):
    payload = {
        "version": 1,
        "chart_count": 1,
        "trait_baselines": {"row": {"profile_hash": "x", "db_average": 1.0}},
        **_theme_snapshot_fields(),
    }
    first_family = next(iter(THEME_FAMILIES))
    del payload[THEME_FAMILY_AVAILABILITY_ROWS_FIELD][_AVAILABILITY][first_family]
    source = tmp_path / "snapshot.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="availability stratum"):
        bundle_snapshot(source, tmp_path / "official.json")


def test_bundle_official_snapshot_rejects_pre_chart_share_theme_snapshot():
    with pytest.raises(ValueError, match="chart-share schema"):
        bundler.validate_theme_family_coverage(_legacy_theme_snapshot_fields())


def test_bundle_official_snapshot_rejects_incomplete_chart_share_distribution():
    payload = _theme_snapshot_fields()
    first_theme = next(iter(THEMES))
    del payload[THEME_SUBTHEME_SHARE_VALUES_FIELD][_AVAILABILITY][first_theme]

    with pytest.raises(ValueError, match="distribution"):
        bundler.validate_theme_family_coverage(payload)
