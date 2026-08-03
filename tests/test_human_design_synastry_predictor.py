from ephemeraldaddy.analysis.human_design_synastry import (
    HumanDesignSynastryCandidate,
    normalize_gates,
    rank_human_design_synastry,
)


def candidate(uid, gates, name="Candidate"):
    return HumanDesignSynastryCandidate(uid, name, None, frozenset(gates))


def test_rank_prioritizes_new_completed_channels_then_center_bonus():
    # Gate 64 can be completed by 47; gate 61 can be completed by 24.
    results = rank_human_design_synastry(
        "SOURCE",
        {64, 61},
        [
            candidate("ONE", {47}, "One channel"),
            candidate("TWO", {47, 24}, "Two channels"),
        ],
    )

    assert [match.chart_uid for match in results] == ["TWO", "ONE"]
    assert results[0].completed_channels == 2
    assert results[0].defined_centers == 2


def test_rank_excludes_source_and_is_deterministic_for_ties():
    results = rank_human_design_synastry(
        "source",
        {64},
        [
            candidate("SOURCE", {47}, "Self"),
            candidate("B", {47}, "Zed"),
            candidate("A", {47}, "Alpha"),
        ],
    )

    assert [match.chart_uid for match in results] == ["A", "B"]


def test_candidate_natal_channels_are_not_counted_as_synastry_completions():
    results = rank_human_design_synastry(
        "SOURCE",
        {64},
        [
            candidate("NATAL", {61, 24, 17, 62}, "Unrelated natal channels"),
            candidate("CROSS", {47}, "Cross-chart completion"),
        ],
    )

    assert [match.chart_uid for match in results] == ["CROSS", "NATAL"]
    assert results[0].completed_channels == 1
    assert results[1].completed_channels == 0


def test_normalize_gates_ignores_invalid_cache_values():
    assert normalize_gates(["1", 64, 0, 65, "oops", None]) == frozenset({1, 64})
