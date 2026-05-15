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
    assert profile["gates"] == {"Gate 1": 4}
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
