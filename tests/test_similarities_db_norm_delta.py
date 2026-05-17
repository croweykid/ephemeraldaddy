import math

from ephemeraldaddy.gui.features.charts.similarities_db_norm import (
    SIMILARITY_DELTA_NEGATIVE_RGB,
    SIMILARITY_DELTA_NEUTRAL_RGB,
    SIMILARITY_DELTA_POSITIVE_RGB,
    similarity_delta_points,
    similarity_delta_rgb,
    similarity_deviation_z_score,
)


def test_similarity_delta_points_preserves_below_db_norm_direction():
    assert similarity_delta_points(20, 70) == -50.0
    assert similarity_delta_points(90, 70) == 20.0


def test_similarity_delta_rgb_uses_signed_db_norm_direction():
    assert similarity_delta_rgb(70, 70) == SIMILARITY_DELTA_NEUTRAL_RGB
    assert similarity_delta_rgb(90, 70) == SIMILARITY_DELTA_POSITIVE_RGB
    assert similarity_delta_rgb(20, 70) == SIMILARITY_DELTA_NEGATIVE_RGB


def test_similarity_deviation_z_score_is_signed_standard_error_distance():
    z_score = similarity_deviation_z_score(20, 70, 10)
    expected_standard_error_percent = math.sqrt(0.7 * 0.3 / 10) * 100.0

    assert z_score == (20.0 - 70.0) / expected_standard_error_percent
    assert z_score < 0
    assert similarity_deviation_z_score(70, 70, 10) == 0.0


def test_similarity_delta_rgb_deemphasizes_tiny_selection_samples():
    tiny_sample_color = similarity_delta_rgb(100, 20, total_count=2)

    assert tiny_sample_color != SIMILARITY_DELTA_POSITIVE_RGB
    assert tiny_sample_color[1] > SIMILARITY_DELTA_NEUTRAL_RGB[1]
