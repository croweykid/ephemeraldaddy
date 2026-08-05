import pytest

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)
ocean = pytest.importorskip("ephemeraldaddy.gui.features.predictions.ocean", exc_type=ImportError)


def _scores(neuroticism):
    return {"E": 4, "O": 4, "A": 4, "C": -4, "N": neuroticism}


def test_mbti_neuroticism_prefix_for_high_neuroticism():
    assert ocean.ocean_scores_to_mbti_with_neuroticism_prefix(_scores(12)) == "neurotic ENFP"


def test_mbti_neuroticism_prefix_for_low_neuroticism():
    assert ocean.ocean_scores_to_mbti_with_neuroticism_prefix(_scores(-3)) == "stable ENFP"


def test_mbti_neuroticism_prefix_exact_threshold_is_unprefixed():
    assert ocean.ocean_scores_to_mbti_with_neuroticism_prefix(_scores(2)) == "ENFP"
