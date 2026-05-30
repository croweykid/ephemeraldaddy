from types import SimpleNamespace

from ephemeraldaddy.analysis.get_astro_twin import (
    chart_body_dominance_weights,
    chart_house_dominance_weights,
    chart_sign_dominance_weights,
)


def test_public_similarity_dominance_profiles_use_similarity_source_shapes():
    chart = SimpleNamespace(
        birthtime_unknown=False,
        positions={"Sun": 5.0, "Moon": 35.0, "Mercury": 65.0},
        houses=[0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
    )

    sign_weights = chart_sign_dominance_weights(chart)
    body_weights = chart_body_dominance_weights(chart)
    house_weights = chart_house_dominance_weights(chart)

    assert sign_weights["Aries"] > 0
    assert sign_weights["Taurus"] > 0
    assert body_weights["Sun"] > 0
    assert body_weights["Moon"] > 0
    assert house_weights[1] > 0
    assert house_weights[2] > 0
