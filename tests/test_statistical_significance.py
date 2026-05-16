import math

from ephemeraldaddy.gui.features.charts.statistical_significance import (
    SIGNIFICANCE_CORRECTION_BH,
    SIGNIFICANCE_CORRECTION_BONFERRONI,
    compute_proportion_significance_results,
    normalize_significance_correction,
    typical_standard_error,
)
from ephemeraldaddy.gui.features.charts.similarity_norms import similarity_z_score


def test_proportion_z_test_flags_large_category_shift():
    results = compute_proportion_significance_results(
        selection_counts=[80, 20],
        database_counts=[500, 500],
        loaded_charts=100,
        correction=SIGNIFICANCE_CORRECTION_BH,
    )

    assert results[0].z_score is not None
    assert results[0].z_score > 5.0
    assert results[0].adjusted_p_value is not None
    assert results[0].adjusted_p_value < 0.001
    assert results[0].band == "extreme"
    assert results[0].model == "category proportion z-test"
    assert typical_standard_error(results) is not None


def test_multiple_comparison_correction_aliases_and_bonferroni():
    assert normalize_significance_correction("Benjamini-Hochberg FDR") == SIGNIFICANCE_CORRECTION_BH
    results = compute_proportion_significance_results(
        selection_counts=[60, 40, 0],
        database_counts=[500, 450, 50],
        loaded_charts=100,
        correction=SIGNIFICANCE_CORRECTION_BONFERRONI,
    )

    for result in results:
        if result.p_value is not None:
            assert result.adjusted_p_value is not None
            assert result.adjusted_p_value >= result.p_value


def test_similarity_z_score_uses_saved_norm_units():
    z_score = similarity_z_score(82.0, average=70.0, standard_deviation=6.0)

    assert z_score is not None
    assert math.isclose(z_score, 2.0)
    assert similarity_z_score(82.0, average=70.0, standard_deviation=0.0) is None


def test_proportion_z_test_accepts_explicit_totals_for_multilabel_categories():
    results = compute_proportion_significance_results(
        selection_counts=[10],
        database_counts=[10],
        loaded_charts=20,
        selection_total=20,
        database_total=100,
    )

    assert results[0].z_score is not None
    assert results[0].z_score > 4.0
