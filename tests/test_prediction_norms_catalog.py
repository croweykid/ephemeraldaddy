from ephemeraldaddy.analysis.prediction_norms_catalog import (
    PREDICTION_NORMS_CATALOG_VERSION,
    PREDICTION_NORMS_SECTION_TRAITS,
    TRAIT_DISTRIBUTION_WITHOUT_HOUSES,
    TRAIT_DISTRIBUTION_WITH_HOUSES,
    build_trait_norm_row,
    empty_prediction_norms_catalog,
    legacy_prediction_snapshot_to_catalog,
    summarize_trait_distribution,
    trait_distribution_for_chart,
    trait_empirical_percentile,
    trait_z_score,
    validate_prediction_norms_catalog,
)


def test_trait_distribution_retains_tenth_point_histogram_and_midrank_percentile():
    summary = summarize_trait_distribution([40.0, 50.0, 50.0, 60.0])

    assert summary["sample_size"] == 4
    assert summary["mean"] == 50.0
    assert summary["median"] == 50.0
    assert sum(summary["histogram_tenths"]) == 4
    assert trait_empirical_percentile(40.0, summary) == 12.5
    assert trait_empirical_percentile(50.0, summary) == 50.0
    assert trait_empirical_percentile(60.0, summary) == 87.5
    assert trait_z_score(50.0, summary) == 0.0


def test_trait_norm_row_keeps_house_and_no_house_populations_distinct():
    row = build_trait_norm_row(
        key="uid:abc",
        uid="abc",
        name="Example",
        profile_hash="hash",
        source="official",
        with_houses_scores=[60.0, 70.0],
        without_houses_scores=[40.0, 50.0],
    )

    with_houses = trait_distribution_for_chart(row, uses_houses=True)
    without_houses = trait_distribution_for_chart(row, uses_houses=False)

    assert with_houses is not None
    assert without_houses is not None
    assert with_houses["mean"] == 65.0
    assert without_houses["mean"] == 45.0
    assert row["distributions"][TRAIT_DISTRIBUTION_WITH_HOUSES] is with_houses
    assert row["distributions"][TRAIT_DISTRIBUTION_WITHOUT_HOUSES] is without_houses


def test_empty_catalog_has_namespaced_predictor_sections_and_validates():
    catalog = empty_prediction_norms_catalog(source="official", chart_count=2000)

    assert catalog["catalog_version"] == PREDICTION_NORMS_CATALOG_VERSION
    assert PREDICTION_NORMS_SECTION_TRAITS in catalog["sections"]
    assert catalog["provenance"]["chart_count"] == 2000
    validation = validate_prediction_norms_catalog(catalog)
    assert validation.valid is True
    assert validation.errors == ()


def test_legacy_snapshot_adapter_preserves_mean_without_faking_distribution():
    catalog = legacy_prediction_snapshot_to_catalog(
        {
            "version": 1,
            "snapshot_id": "old",
            "chart_count": 100,
            "trait_baselines": {
                "uid:abc": {
                    "uid": "abc",
                    "name": "Example",
                    "profile_hash": "hash",
                    "db_average": 53.5,
                }
            },
            "retired_trait_keys": ["uid:def"],
            "dnd_stat_raw_averages": {"STR": 10.0},
        }
    )

    row = catalog["sections"][PREDICTION_NORMS_SECTION_TRAITS]["rows"]["uid:abc"]
    assert row["legacy_v1"] is True
    assert row["legacy_db_average"] == 53.5
    assert "distributions" not in row
