from ephemeraldaddy.gui.features.charts.similarity_pairing import (
    SimilarityInputState,
    build_chart_lookup,
    resolve_similarity_pair_targets,
    similarity_breakdown_chart_ids,
)


def test_checked_chart_inputs_drive_similarity_breakdown_ids():
    chart_lookup = {
        "Alice  [UID: UIDALICE000001]": 101,
        "Bob  [UID: UIDBOB0000002]": 202,
    }
    input_state = SimilarityInputState(
        selected_chart_ids=[],
        first_checked=True,
        second_checked=True,
        first_input_value="Alice  [UID: UIDALICE000001]",
        second_input_value="Bob  [UID: UIDBOB0000002]",
    )

    resolution = resolve_similarity_pair_targets(input_state, chart_lookup)

    assert resolution.first_chart_id == 101
    assert resolution.second_chart_id == 202
    assert resolution.allow_click is True
    assert similarity_breakdown_chart_ids(resolution) == [101, 202]


def test_unresolved_pair_has_no_breakdown_ids():
    chart_lookup = {"Alice  [UID: UIDALICE000001]": 101}
    input_state = SimilarityInputState(
        selected_chart_ids=[],
        first_checked=True,
        second_checked=True,
        first_input_value="Alice  [UID: UIDALICE000001]",
        second_input_value="Missing",
    )

    resolution = resolve_similarity_pair_targets(input_state, chart_lookup)

    assert resolution.second_chart_id is None
    assert similarity_breakdown_chart_ids(resolution) is None


def test_chart_lookup_labels_expose_chart_uid_instead_of_legacy_id():
    row = (101, "Alice", "Al", None, "", None, "", 0, 0, 0, None, 0, None, 0, "natal", 0, 0, None, None, None, None, None, None, "blank", None, None, None, None, None, None, "UIDALICE000001")

    chart_lookup, choices = build_chart_lookup([row])

    assert choices == ["Alice (Al)  [UID: UIDALICE000001]"]
    assert chart_lookup[choices[0]] == 101
    assert "#101" not in choices[0]
