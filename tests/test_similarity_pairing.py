from ephemeraldaddy.gui.features.charts.similarity_pairing import (
    SimilarityInputState,
    resolve_similarity_pair_targets,
    similarity_breakdown_chart_ids,
)


def test_checked_chart_inputs_drive_similarity_breakdown_ids():
    chart_lookup = {
        "Alice  [#101]": 101,
        "Bob  [#202]": 202,
    }
    input_state = SimilarityInputState(
        selected_chart_ids=[],
        first_checked=True,
        second_checked=True,
        first_input_value="Alice  [#101]",
        second_input_value="Bob  [#202]",
    )

    resolution = resolve_similarity_pair_targets(input_state, chart_lookup)

    assert resolution.first_chart_id == 101
    assert resolution.second_chart_id == 202
    assert resolution.allow_click is True
    assert similarity_breakdown_chart_ids(resolution) == [101, 202]


def test_unresolved_pair_has_no_breakdown_ids():
    chart_lookup = {"Alice  [#101]": 101}
    input_state = SimilarityInputState(
        selected_chart_ids=[],
        first_checked=True,
        second_checked=True,
        first_input_value="Alice  [#101]",
        second_input_value="Missing",
    )

    resolution = resolve_similarity_pair_targets(input_state, chart_lookup)

    assert resolution.second_chart_id is None
    assert similarity_breakdown_chart_ids(resolution) is None
