from ephemeraldaddy.gui.features.charts.similarity_pairing import (
    SimilarityInputState,
    build_chart_lookup,
    resolve_similarity_pair_targets,
    similarity_breakdown_chart_uids,
)


def test_checked_chart_inputs_drive_similarity_breakdown_uids():
    chart_lookup = {"Alice": "UIDALICE000001", "Bob": "UIDBOB0000002"}
    input_state = SimilarityInputState(
        selected_chart_uids=[],
        first_checked=True,
        second_checked=True,
        first_input_value="Alice",
        second_input_value="Bob",
    )

    resolution = resolve_similarity_pair_targets(input_state, chart_lookup)

    assert resolution.first_chart_uid == "UIDALICE000001"
    assert resolution.second_chart_uid == "UIDBOB0000002"
    assert resolution.allow_click is True
    assert similarity_breakdown_chart_uids(resolution) == [
        "UIDALICE000001",
        "UIDBOB0000002",
    ]


def test_unresolved_pair_has_no_breakdown_uids():
    input_state = SimilarityInputState(
        selected_chart_uids=[],
        first_checked=True,
        second_checked=True,
        first_input_value="Alice",
        second_input_value="Missing",
    )

    resolution = resolve_similarity_pair_targets(
        input_state, {"Alice": "UIDALICE000001"}
    )

    assert resolution.second_chart_uid is None
    assert similarity_breakdown_chart_uids(resolution) is None


def test_chart_lookup_maps_labels_to_uid_without_displaying_uid():
    row = (101, "Alice", "Al", "Wonderland")

    chart_lookup, choices = build_chart_lookup([row], {101: "UIDALICE000001"})

    assert choices == ["Alice (Al) (Wonderland)"]
    assert chart_lookup[choices[0]] == "UIDALICE000001"
    assert "UID" not in choices[0]


def test_chart_lookup_omits_rows_without_persisted_uid():
    chart_lookup, choices = build_chart_lookup([(101, "Alice", None, None)], {})

    assert chart_lookup == {}
    assert choices == []
