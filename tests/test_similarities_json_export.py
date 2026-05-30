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
        "Sun in H1": 30,
        "Moon in H12": -40,
        "Aries in H1": 30,
        "Pisces in H12": -40,
    }
    assert profile["antipositions"] == {}
    assert profile["houses"] == {"1": 30, "12": -40}
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
        "Sun in Capricorn",
        "Mercury in H5",
        "Venus in Capricorn",
        "Ceres in Pisces",
        "Ceres in H4",
        "Lilith in H6",
        "Rahu in H2",
        "Ketu in H1",
        "Aries in H1",
    ]


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
    assert parse_position_spec(next(iter(profile["positions"]))) == (
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


def test_dissimilarities_json_export_uses_antifactor_buckets():
    payload = build_similarities_json_export_payload(
        "Contrasts",
        [
            ("Signs in positions in contrast", [("Sun in Aries", 1, 2, 0, 100, "A")]),
            ("Houses in positions in contrast", [("Moon: House 7", 1, 2, 0, 100, "B")]),
            ("Top 3 Dominant Signs in contrast", [("Libra", 1, 2, 0, 100, "A")]),
            ("Gates in contrast", [("Gate 44", 1, 2, 0, 100, "B")]),
            ("Channels in contrast", [("57-20", 1, 2, 0, 100, "B")]),
        ],
    )

    profile = payload["Contrasts"]
    assert profile["positions"] == {}
    assert profile["antipositions"] == {"Sun in Aries": 50, "Moon in H7": 50}
    assert profile["signs"] == {}
    assert profile["antisigns"] == {"Libra": 50}
    assert profile["gates"] == {}
    assert profile["antigates"] == {44: 50}
    assert profile["channels"] == {}
    assert profile["antichannels"] == {(20, 57): 50}
    assert similarities_json_payload_has_factors(payload, "Contrasts")


def test_dissimilarities_json_export_bundles_chart_unique_factors_by_owner():
    payload = build_similarities_json_export_payload(
        "Contrasts",
        [
            (
                "Signs in positions in contrast",
                [
                    ("Sun in Aries", 1, 2, 0, 100, "A", "chart_1"),
                    ("Sun in Taurus", 1, 2, 0, 100, "B", "chart_2"),
                ],
            ),
            ("Gates in contrast", [("Gate 44", 1, 2, 0, 100, "A", "chart_1")]),
        ],
    )

    bundle = payload["Contrasts"]
    chart_1 = bundle["chart 1 unique factors"]
    chart_2 = bundle["chart 2 unique factors"]
    assert chart_1["positions"] == {"Sun in Aries": 50}
    assert chart_1["gates"] == {44: 50}
    assert chart_1["antipositions"] == {}
    assert chart_2["positions"] == {"Sun in Taurus": 50}
    assert chart_2["gates"] == {}
    assert similarities_json_payload_has_factors(payload, "Contrasts")


def test_dissimilarities_json_export_keeps_all_owner_buckets_without_significance_filter():
    payload = build_similarities_json_export_payload(
        "Contrasts",
        [
            ("Top 3 Dominant Signs in contrast", [("Libra", 1, 2, 45, 100, "A", "chart_1")]),
            ("Top 3 Dominant Bodies in contrast", [("Venus", 1, 2, 45, 100, "A", "chart_1")]),
            ("Top 3 Dominant Houses in contrast", [("House 7", 1, 2, 45, 100, "A", "chart_1")]),
            ("Dominant nakshatras in contrast", [("Rohini", 1, 2, 45, 100, "A", "chart_1")]),
            ("Gates in contrast", [("Gate 44", 1, 2, 45, 100, "A", "chart_1")]),
            ("Channels in contrast", [("57-20", 1, 2, 45, 100, "A", "chart_1")]),
            ("Defined Centers in contrast", [("Throat", 1, 2, 45, 100, "A", "chart_1")]),
            ("Authorities in contrast", [("Emotional", 1, 2, 45, 100, "A", "chart_1")]),
            ("Profiles in contrast", [("3/5", 1, 2, 45, 100, "A", "chart_1")]),
            ("BaZi signs in contrast", [("Snake", 1, 2, 45, 100, "A", "chart_1")]),
        ],
    )

    chart_1 = payload["Contrasts"]["chart 1 unique factors"]
    assert chart_1["signs"] == {"Libra": 5}
    assert chart_1["bodies"] == {"Venus": 5}
    assert chart_1["houses"] == {"7": 5}
    assert chart_1["nakshatras"] == {"Rohini": 5}
    assert chart_1["gates"] == {44: 5}
    assert chart_1["channels"] == {(20, 57): 5}
    assert chart_1["centers"] == {"Throat": 5}
    assert chart_1["authorities"] == {"Emotional": 5}
    assert chart_1["profiles"] == {"3/5": 5}
    assert chart_1["bazisigns"] == {"Snake": 5}
