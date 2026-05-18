from types import SimpleNamespace

from ephemeraldaddy.analysis.get_astro_twin import (
    SimilarityCalculatorSettings,
    chart_dissimilarity_score_comprehensive,
    chart_similarity_score_custom,
)


def test_comprehensive_similarity_defaults_match_requested_weights():
    settings = SimilarityCalculatorSettings.defaults_from_comprehensive()

    assert settings.weights_by_component() == {
        "placement": 0.33,
        "aspect": 0.07,
        "distribution": 0.10,
        "combined_dominance": 0.15,
        "nakshatra_placement": 0.07,
        "nakshatra_dominance": 0.0,
        "defined_centers": 0.0,
        "human_design_gates": 0.18,
        "human_design_channels": 0.0,
        "inner_planet_placement": 0.0,
        "outer_planet_placement": 0.0,
    }
    assert settings.enabled_components()["human_design_gates"] is True
    assert settings.enabled_components()["defined_centers"] is False


def test_custom_similarity_can_score_human_design_channels_only():
    first = SimpleNamespace(
        positions={"Sun": 0.0},
        human_design_channels=["20-34", "6-59"],
        is_placeholder=False,
    )
    second = SimpleNamespace(
        positions={"Sun": 0.0},
        human_design_channels=["34-20"],
        is_placeholder=False,
    )
    settings = SimilarityCalculatorSettings(
        use_placement=False,
        weight_placement=0.0,
        use_aspect=False,
        weight_aspect=0.0,
        use_distribution=False,
        weight_distribution=0.0,
        use_combined_dominance=False,
        weight_combined_dominance=0.0,
        use_nakshatra_placement=False,
        weight_nakshatra_placement=0.0,
        use_human_design_gates=False,
        weight_human_design_gates=0.0,
        use_human_design_channels=True,
        weight_human_design_channels=1.0,
    )

    final_score, components = chart_similarity_score_custom(first, second, settings)

    assert components["human_design_channels"] == 0.5
    assert final_score == 0.5


def test_custom_similarity_can_score_inner_and_outer_placements_separately():
    first = SimpleNamespace(
        positions={
            "Sun": 0.0,
            "Moon": 30.0,
            "Mercury": 60.0,
            "Venus": 90.0,
            "Mars": 120.0,
            "Jupiter": 150.0,
            "Saturn": 180.0,
            "Uranus": 210.0,
            "Neptune": 240.0,
            "Pluto": 270.0,
        },
        is_placeholder=False,
    )
    second = SimpleNamespace(
        positions={
            "Sun": 0.0,
            "Moon": 30.0,
            "Mercury": 60.0,
            "Venus": 90.0,
            "Mars": 120.0,
            "Jupiter": 150.0,
            "Saturn": 180.0,
            "Uranus": 0.0,
            "Neptune": 0.0,
            "Pluto": 0.0,
        },
        is_placeholder=False,
    )
    settings = SimilarityCalculatorSettings()

    _final_score, components = chart_similarity_score_custom(first, second, settings)

    assert components["inner_planet_placement"] == 1.0
    assert components["outer_planet_placement"] < 1.0


def test_comprehensive_dissimilarity_ranking_includes_human_design_gates():
    positions = {
        "Sun": 0.0,
        "Moon": 30.0,
        "Mercury": 60.0,
        "Venus": 90.0,
        "Mars": 120.0,
        "Jupiter": 150.0,
        "Saturn": 180.0,
        "Uranus": 210.0,
        "Neptune": 240.0,
        "Pluto": 270.0,
    }
    subject = SimpleNamespace(
        positions=positions,
        human_design_gates=[1, 2, 3],
        birthtime_unknown=True,
        is_placeholder=False,
    )
    same_gates = SimpleNamespace(
        positions=dict(positions),
        human_design_gates=[1, 2, 3],
        birthtime_unknown=True,
        is_placeholder=False,
    )
    different_gates = SimpleNamespace(
        positions=dict(positions),
        human_design_gates=[61, 62, 63],
        birthtime_unknown=True,
        is_placeholder=False,
    )

    same_rank_score = chart_dissimilarity_score_comprehensive(subject, same_gates)[0]
    different_rank_score = chart_dissimilarity_score_comprehensive(subject, different_gates)[0]

    assert different_rank_score > same_rank_score
