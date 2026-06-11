from types import SimpleNamespace

from ephemeraldaddy.analysis import get_astro_twin
from ephemeraldaddy.analysis.get_astro_twin import (
    SimilarityCalculatorSettings,
    all_or_nothing_similarity_settings,
    chart_dissimilarity_score_comprehensive,
    chart_similarity_score_all_or_nothing,
    chart_similarity_score_custom,
    find_astro_twins,
    normalize_similar_charts_algorithm_mode,
)


def test_default_similarity_settings_match_requested_weights():
    settings = SimilarityCalculatorSettings.defaults_for_default_mode()

    assert settings.normalized_placement_weighting_mode() == "hybrid"
    assert settings.weights_by_component() == {
        "placement": 0.17,
        "aspect": 0.08,
        "distribution": 0.07,
        "combined_dominance": 0.17,
        "nakshatra_placement": 0.06,
        "nakshatra_dominance": 0.09,
        "defined_centers": 0.03,
        "human_design_gates": 0.30,
        "human_design_channels": 0.04,
        "inner_planet_placement": 0.13,
        "outer_planet_placement": 0.0,
    }
    assert settings.enabled_components() == {
        "placement": True,
        "aspect": True,
        "distribution": False,
        "combined_dominance": True,
        "nakshatra_placement": True,
        "nakshatra_dominance": True,
        "defined_centers": False,
        "human_design_gates": True,
        "human_design_channels": False,
        "inner_planet_placement": True,
        "outer_planet_placement": False,
    }
    assert sum(
        weight
        for key, weight in settings.weights_by_component().items()
        if settings.enabled_components()[key]
    ) == 1.0


def test_generic_astro_algorithm_mode_is_supported():
    assert normalize_similar_charts_algorithm_mode("generic astro") == "generic_astro"
    assert normalize_similar_charts_algorithm_mode("generic_astro") == "generic_astro"


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


def test_default_algorithm_mode_uses_new_default_custom_settings(monkeypatch):
    def fake_custom(_query, _candidate, settings):
        assert settings.normalized_placement_weighting_mode() == "hybrid"
        assert settings.enabled_components()["human_design_gates"] is True
        assert settings.weights_by_component()["human_design_gates"] == 0.30
        return 0.73, {"placement": 0.73}

    monkeypatch.setattr(get_astro_twin, "chart_similarity_score_custom", fake_custom)
    query = SimpleNamespace(name="Query", positions={"Sun": 0.0}, is_placeholder=False)
    candidate = SimpleNamespace(name="Candidate", positions={"Sun": 0.0}, is_placeholder=False)

    matches = find_astro_twins(query, [(1, candidate)], top_k=1, algorithm_mode="default", custom_settings=None)

    assert matches[0].score == 0.73
    assert matches[0].algorithm_mode == "default"


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
        use_inner_planet_placement=True,
        weight_inner_planet_placement=0.5,
        use_outer_planet_placement=True,
        weight_outer_planet_placement=0.5,
    )

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


def test_all_or_nothing_similarity_uses_only_selected_human_design_gates():
    positions = {"Sun": 0.0, "Moon": 30.0, "Mercury": 60.0, "Venus": 90.0, "Mars": 120.0}
    query = SimpleNamespace(
        name="Query",
        positions=positions,
        human_design_gates=[1, 2, 3],
        birthtime_unknown=True,
        is_placeholder=False,
    )
    same_gates_different_positions = SimpleNamespace(
        name="Same Gates",
        positions={"Sun": 180.0, "Moon": 210.0, "Mercury": 240.0, "Venus": 270.0, "Mars": 300.0},
        human_design_gates=[1, 2, 3],
        birthtime_unknown=True,
        is_placeholder=False,
    )
    different_gates_same_positions = SimpleNamespace(
        name="Different Gates",
        positions=dict(positions),
        human_design_gates=[61, 62, 63],
        birthtime_unknown=True,
        is_placeholder=False,
    )
    settings = SimilarityCalculatorSettings(all_or_nothing_component="human_design_gates")

    matches = find_astro_twins(
        query,
        [(1, same_gates_different_positions), (2, different_gates_same_positions)],
        top_k=2,
        algorithm_mode="all_or_nothing",
        custom_settings=settings,
    )

    assert [match.chart_name for match in matches] == ["Same Gates", "Different Gates"]
    assert matches[0].score == 1.0
    assert matches[1].score == 0.0
    assert matches[0].algorithm_mode == "all_or_nothing"


def test_all_or_nothing_settings_exclude_broad_criteria_and_normalize_to_one_weight():
    settings = SimilarityCalculatorSettings(all_or_nothing_component="outer_planet_placement")

    effective = all_or_nothing_similarity_settings(settings)

    assert effective.all_or_nothing_component == "inner_planet_placement"
    assert effective.enabled_components()["inner_planet_placement"] is True
    assert sum(effective.weights_by_component().values()) == 1.0


def test_all_or_nothing_default_criterion_is_inner_planet_placement():
    settings = SimilarityCalculatorSettings()

    effective = all_or_nothing_similarity_settings(settings)

    assert settings.all_or_nothing_component == "inner_planet_placement"
    assert effective.all_or_nothing_component == "inner_planet_placement"
    assert effective.enabled_components()["inner_planet_placement"] is True
    assert effective.weights_by_component()["inner_planet_placement"] == 1.0


def test_all_or_nothing_only_calculates_the_selected_component(monkeypatch):
    def fail_unneeded_component(*_args, **_kwargs):
        raise AssertionError("unneeded component was calculated")

    for function_name in (
        "_placement_similarity",
        "_aspect_similarity",
        "_distribution_similarity",
        "_combined_dominance_similarity",
        "_nakshatra_similarity",
        "_nakshatra_dominance_similarity",
        "_defined_centers_similarity",
        "_human_design_channels_similarity",
    ):
        monkeypatch.setattr(get_astro_twin, function_name, fail_unneeded_component)

    first = SimpleNamespace(
        positions={"Sun": 0.0},
        human_design_gates=[1, 2, 3],
        birthtime_unknown=True,
        is_placeholder=False,
    )
    second = SimpleNamespace(
        positions={"Sun": 0.0},
        human_design_gates=[1, 3, 5],
        birthtime_unknown=True,
        is_placeholder=False,
    )
    settings = SimilarityCalculatorSettings(all_or_nothing_component="human_design_gates")

    final_score, component_scores = chart_similarity_score_all_or_nothing(first, second, settings)

    assert component_scores == {"human_design_gates": 0.5}
    assert final_score == 0.5


def test_custom_similarity_only_calculates_enabled_weighted_components(monkeypatch):
    def fail_unneeded_component(*_args, **_kwargs):
        raise AssertionError("unneeded component was calculated")

    for function_name in (
        "_placement_similarity",
        "_aspect_similarity",
        "_distribution_similarity",
        "_combined_dominance_similarity",
        "_nakshatra_similarity",
        "_nakshatra_dominance_similarity",
        "_defined_centers_similarity",
        "_human_design_gates_similarity",
    ):
        monkeypatch.setattr(get_astro_twin, function_name, fail_unneeded_component)

    first = SimpleNamespace(
        positions={"Sun": 0.0},
        human_design_channels=["20-34", "6-59"],
        birthtime_unknown=True,
        is_placeholder=False,
    )
    second = SimpleNamespace(
        positions={"Sun": 0.0},
        human_design_channels=["34-20"],
        birthtime_unknown=True,
        is_placeholder=False,
    )
    settings = SimilarityCalculatorSettings(
        use_placement=True,
        weight_placement=0.0,
        use_aspect=False,
        weight_aspect=1.0,
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

    final_score, component_scores = chart_similarity_score_custom(first, second, settings)

    assert component_scores == {"human_design_channels": 0.5}
    assert final_score == 0.5


def test_all_or_nothing_least_similar_skips_dominance_guardrail(monkeypatch):
    def fail_unneeded_guardrail(*_args, **_kwargs):
        raise AssertionError("least-similar dominance guardrail should not run for all-or-nothing")

    monkeypatch.setattr(get_astro_twin, "_sign_weight_profile", fail_unneeded_guardrail)
    query = SimpleNamespace(
        name="Query",
        positions={"Sun": 0.0},
        human_design_gates=[1, 2, 3],
        birthtime_unknown=True,
        is_placeholder=False,
    )
    candidate = SimpleNamespace(
        name="Candidate",
        positions={"Sun": 0.0},
        human_design_gates=[4, 5, 6],
        birthtime_unknown=True,
        is_placeholder=False,
    )

    matches = find_astro_twins(
        query,
        [(1, candidate)],
        top_k=1,
        least_similar=True,
        algorithm_mode="all_or_nothing",
        custom_settings=SimilarityCalculatorSettings(all_or_nothing_component="human_design_gates"),
    )

    assert [match.chart_name for match in matches] == ["Candidate"]
    assert matches[0].score == 0.0
