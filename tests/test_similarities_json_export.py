from ephemeraldaddy.analysis.weighted_chart_predictor import (
    parse_position_spec,
    weighted_gate_entries,
    weighted_house_entries,
)
from ephemeraldaddy.gui.features.charts.similarities_export import (
    build_similarities_json_export_payload,
    similarities_json_payload_has_factors,
)


def test_similarities_json_export_routes_positive_and_negative_deltas():
    payload = build_similarities_json_export_payload(
        "Test Selection",
        [
            (
                "Top 3 Dominant Signs in common",
                [
                    ("Aries", 6, 10, 20, 100, "A, B"),
                    ("Taurus", 1, 10, 20, 100, "C"),
                ],
            ),
            (
                "Gates in common",
                [
                    ("Gate 1", 5, 10, 46, 100, "A"),
                    ("Gate 2", 5, 10, 47, 100, "A"),
                ],
            ),
        ],
    )

    profile = payload["Test Selection"]
    assert profile["name"] == "Test Selection"
    assert profile["signs"] == {"Aries": 40}
    assert profile["antisigns"] == {"Taurus": 10}
    assert profile["gates"] == {"1": 4}
    assert profile["antigates"] == {}
    assert similarities_json_payload_has_factors(payload, "Test Selection")


def test_similarities_json_export_omits_deltas_at_or_under_three_percent():
    payload = build_similarities_json_export_payload(
        "Tiny Delta",
        [
            (
                "Aspects in common",
                [
                    ("Sun conjunct Moon", 50, 100, 47, 100, "A"),
                    ("Mars trine Venus", 50, 100, 48, 100, "B"),
                ],
            )
        ],
    )

    profile = payload["Tiny Delta"]
    assert profile["aspects"] == {}
    assert not similarities_json_payload_has_factors(payload, "Tiny Delta")


def test_similarities_json_export_normalizes_position_and_house_labels():
    payload = build_similarities_json_export_payload(
        "Normalized",
        [
            (
                "Houses in positions in common",
                [
                    ("Sun: House 1", 5, 10, 20, 100, "A"),
                    ("Moon: House 12", 1, 10, 20, 100, "B"),
                ],
            ),
            (
                "Signs in houses in common",
                [
                    ("House 1: Aries", 5, 10, 20, 100, "A"),
                    ("House 12: Pisces", 1, 10, 20, 100, "B"),
                ],
            ),
            (
                "Top 3 Dominant Houses in common",
                [
                    ("House 1", 5, 10, 20, 100, "A"),
                    ("House 12", 1, 10, 20, 100, "B"),
                ],
            ),
        ],
    )

    profile = payload["Normalized"]
    assert profile["positions"] == {
        "Sun in H1": 30,
        "Aries in H1": 30,
    }
    assert profile["antipositions"] == {
        "Moon in H12": 10,
        "Pisces in H12": 10,
    }
    assert profile["houses"] == {"1": 30}
    assert profile["antihouses"] == {"12": 10}


def test_normalized_similarities_json_criteria_are_accepted_by_profile_consumers():
    payload = build_similarities_json_export_payload(
        "Reusable",
        [
            ("Houses in positions in common", [("Sun: House 1", 5, 10, 20, 100, "A")]),
            ("Signs in houses in common", [("House 12: Pisces", 1, 10, 20, 100, "B")]),
            ("Top 3 Dominant Houses in common", [("House 12", 1, 10, 20, 100, "B")]),
            ("Gates in common", [("Gate 1", 5, 10, 20, 100, "A")]),
        ],
    )

    profile = payload["Reusable"]
    assert parse_position_spec(next(iter(profile["positions"]))) == (
        "body_in_house",
        1,
        "Sun",
    )
    assert parse_position_spec(next(iter(profile["antipositions"]))) == (
        "sign_in_house",
        12,
        "Pisces",
    )
    assert weighted_house_entries(profile["antihouses"]) == {12: 10.0}
    assert weighted_gate_entries(profile["gates"]) == {1: 30.0}
