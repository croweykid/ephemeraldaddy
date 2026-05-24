from ephemeraldaddy.analysis.weighted_chart_predictor import (
    parse_position_spec,
    weighted_gate_entries,
    weighted_house_entries,
)
from ephemeraldaddy.gui.features.charts.similarities_export import (
    build_similarities_json_export_payload,
    format_similarities_json_export_payload,
    similarities_json_payload_has_factors,
)


def test_similarities_json_export_keeps_beyond_second_std_tier_deltas_signed():
    payload = build_similarities_json_export_payload(
        "Test Selection",
        [
            (
                "Top 3 Dominant Signs in common",
                [
                    ("Aries", 6, 10, 20, 100, "A, B"),
                    ("Taurus", 1, 10, 50, 100, "C"),
                ],
            ),
            (
                "Gates in common",
                [
                    ("Gate 1", 5, 10, 15, 100, "A"),
                    ("Gate 2", 5, 10, 47, 100, "A"),
                ],
            ),
        ],
    )

    profile = payload["Test Selection"]
    assert profile["name"] == "Test Selection"
    assert profile["signs"] == {"Aries": 40, "Taurus": -40}
    assert profile["antisigns"] == {}
    assert profile["gates"] == {1: 35}
    assert profile["antigates"] == {}
    assert similarities_json_payload_has_factors(payload, "Test Selection")


def test_similarities_json_export_omits_deltas_inside_second_std_tier():
    payload = build_similarities_json_export_payload(
        "Tiny Delta",
        [
            (
                "Aspects in common",
                [
                    ("Sun conjunct Moon", 52, 100, 47, 100, "A"),
                    ("Mars trine Venus", 50, 100, 48, 100, "B"),
                ],
            )
        ],
    )

    profile = payload["Tiny Delta"]
    assert profile["aspects"] == {}
    assert not similarities_json_payload_has_factors(payload, "Tiny Delta")


def test_similarities_json_export_normalizes_underrepresented_factors_as_negative_weights():
    payload = build_similarities_json_export_payload(
        "Normalized",
        [
            (
                "Houses in positions in common",
                [
                    ("Sun: House 1", 5, 10, 20, 100, "A"),
                    ("Moon: House 12", 1, 10, 50, 100, "B"),
                ],
            ),
            (
                "Signs in houses in common",
                [
                    ("House 1: Aries", 5, 10, 20, 100, "A"),
                    ("House 12: Pisces", 1, 10, 50, 100, "B"),
                ],
            ),
            (
                "Top 3 Dominant Houses in common",
                [
                    ("House 1", 5, 10, 20, 100, "A"),
                    ("House 12", 1, 10, 50, 100, "B"),
                ],
            ),
        ],
    )

    profile = payload["Normalized"]
    assert profile["positions"] == {
        "Sun": {"signs": {}, "houses": {1: 30}},
        "Moon": {"signs": {}, "houses": {12: -40}},
        "Aries": {"signs": {}, "houses": {1: 30}},
        "Pisces": {"signs": {}, "houses": {12: -40}},
    }
    assert profile["antipositions"] == {}
    assert profile["houses"] == {1: 30, 12: -40}
    assert profile["antihouses"] == {}


def test_similarities_json_export_sorts_positions_by_body_order():
    payload = build_similarities_json_export_payload(
        "Sorted",
        [
            (
                "Signs in houses in common",
                [("House 1: Aries", 2, 10, 0, 100, "A")],
            ),
            (
                "Houses in positions in common",
                [
                    ("Rahu: House 2", 2, 10, 0, 100, "A"),
                    ("Mercury: House 5", 2, 10, 0, 100, "A"),
                    ("Ceres: House 4", 2, 10, 0, 100, "A"),
                    ("Lilith: House 6", 2, 10, 0, 100, "A"),
                    ("Ketu: House 1", 2, 10, 0, 100, "A"),
                ],
            ),
            (
                "Signs in positions in common",
                [
                    ("Ceres in Pisces", 2, 10, 0, 100, "A"),
                    ("Sun in Capricorn", 2, 10, 0, 100, "A"),
                    ("Venus in Capricorn", 2, 10, 0, 100, "A"),
                ],
            ),
        ],
    )

    assert list(payload["Sorted"]["positions"]) == [
        "Sun",
        "Mercury",
        "Venus",
        "Ceres",
        "Lilith",
        "Rahu",
        "Ketu",
        "Aries",
    ]
    assert payload["Sorted"]["positions"]["Sun"] == {"signs": {"Capricorn": 20}, "houses": {}}
    assert payload["Sorted"]["positions"]["Ceres"] == {"signs": {"Pisces": 20}, "houses": {4: 20}}


def test_normalized_similarities_json_criteria_are_accepted_by_profile_consumers():
    payload = build_similarities_json_export_payload(
        "Reusable",
        [
            ("Houses in positions in common", [("Sun: House 1", 5, 10, 20, 100, "A")]),
            ("Signs in houses in common", [("House 12: Pisces", 1, 10, 50, 100, "B")]),
            ("Top 3 Dominant Houses in common", [("House 12", 1, 10, 50, 100, "B")]),
            ("Gates in common", [("Gate 1", 5, 10, 20, 100, "A")]),
        ],
    )

    profile = payload["Reusable"]
    first_body = next(iter(profile["positions"]))
    first_house_key = next(iter(profile["positions"][first_body]["houses"]))
    assert parse_position_spec(f"{first_body} in H{first_house_key}") == (
        "body_in_house",
        1,
        "Sun",
    )
    assert parse_position_spec("Pisces in H12") == (
        "sign_in_house",
        12,
        "Pisces",
    )
    assert weighted_house_entries(profile["houses"]) == {12: -40.0}
    assert weighted_gate_entries(profile["gates"]) == {1: 30.0}


def test_similarities_json_export_formats_gate_and_channel_keys_for_profiles():
    payload = build_similarities_json_export_payload(
        "Profile Ready",
        [
            ("Gates in common", [("Gate 44", 5, 10, 0, 100, "A")]),
            ("Channels in common", [("57-20", 5, 10, 0, 100, "A")]),
        ],
    )

    profile = payload["Profile Ready"]
    assert profile["gates"] == {44: 50}
    assert profile["channels"] == {(20, 57): 50}

    formatted = format_similarities_json_export_payload(payload)
    assert '"gates": {\n            44: 50,' in formatted
    assert '"channels": {\n            (20, 57): 50,' in formatted
    assert '"44": 50' not in formatted
    assert '"20-57": 50' not in formatted


def test_similarities_json_export_sorts_aspects_by_primary_body_order():
    payload = build_similarities_json_export_payload(
        "Aspects Sorted",
        [
            (
                "Aspects in common",
                [
                    ("Chiron sextile Mercury", 5, 10, 0, 100, "A"),
                    ("Mercury opposition Pluto", 5, 10, 0, 100, "A"),
                    ("Venus trine Mars", 5, 10, 0, 100, "A"),
                    ("Moon square Saturn", 5, 10, 0, 100, "A"),
                    ("AS trine Moon", 5, 10, 0, 100, "A"),
                    ("Chiron square Pluto", 5, 10, 0, 100, "A"),
                    ("Saturn quincunx Chiron", 5, 10, 0, 100, "A"),
                    ("Venus opposition Moon", 5, 10, 0, 100, "A"),
                ],
            ),
        ],
    )

    assert list(payload["Aspects Sorted"]["aspects"]) == [
        "Moon square Saturn",
        "Mercury opposition Pluto",
        "Venus opposition Moon",
        "Venus trine Mars",
        "Saturn quincunx Chiron",
        "Chiron sextile Mercury",
        "Chiron square Pluto",
        "AS trine Moon",
    ]
