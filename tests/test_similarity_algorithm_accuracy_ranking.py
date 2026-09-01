import datetime as dt
import json

from ephemeraldaddy.gui.features.charts.similarities_algorithm_log import (
    aggregate_similarity_algorithm_accuracy,
    append_similarity_accuracy_observation,
    format_similarity_algorithm_accuracy_ranking,
    format_similarity_algorithm_accuracy_ranking_html,
    build_similarity_algorithm_snapshot,
)


def _append(path, mode, predicted, perceived, *, not_applicable=False, pair="AB"):
    append_similarity_accuracy_observation(
        algorithm_mode=mode,
        predicted_percent=predicted,
        perceived_similarity_score=perceived,
        perceived_similarity_not_applicable=not_applicable,
        chart_1_uid=pair[0] * 14,
        chart_2_uid=pair[1] * 14,
        path=path,
        timestamp=dt.datetime(2026, 7, 28, tzinfo=dt.timezone.utc),
    )


def test_algorithm_accuracy_aggregates_existing_algorithm_log(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    _append(path, "default", 75, 90)
    _append(path, "big_3", 50, 70)
    _append(path, "default", 50, 80, pair="AC")
    _append(path, "big 3", 80, 60, pair="AC")

    rows = aggregate_similarity_algorithm_accuracy(path)

    assert rows == [
        {"algorithm_mode": "big_3", "average_accuracy": 80.0, "sample_count": 2},
        {"algorithm_mode": "default", "average_accuracy": 77.5, "sample_count": 2},
    ]
    assert "1. Big 3 — 80.0% average (n=2)" in format_similarity_algorithm_accuracy_ranking(rows)


def test_algorithm_accuracy_reads_mixed_historical_log(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    path.write_text(
        "=== Similarities Algorithm Change #1 ===\nAlgorithm mode: default\n\n"
        "Perceived accuracy payload:\n"
        + json.dumps({"user_reported_accuracy": 70, "not_applicable": False})
        + "\n",
        encoding="utf-8",
    )
    _append(path, "comprehensive", 88, 90)
    _append(path, "default", 50, None, not_applicable=True)

    assert aggregate_similarity_algorithm_accuracy(path) == [
        {"algorithm_mode": "comprehensive", "average_accuracy": 98.0, "sample_count": 1}
    ]


def test_algorithm_accuracy_v2_averages_ranked_top_and_bottom_user_scores(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    for rank, perceived in enumerate([90, 80, 70, 60, 50, None], start=1):
        append_similarity_accuracy_observation(
            algorithm_mode="default",
            predicted_percent=100 - rank,
            perceived_similarity_score=perceived,
            perceived_similarity_not_applicable=perceived is None,
            ranking_position=rank,
            chart_1_uid="A" * 14,
            chart_2_uid=chr(65 + rank) * 14,
            path=path,
        )
    for rank, perceived in enumerate([50, 60, 70, 80, 90], start=1):
        append_similarity_accuracy_observation(
            algorithm_mode="big_3",
            predicted_percent=100 - rank,
            perceived_similarity_score=perceived,
            perceived_similarity_not_applicable=False,
            ranking_position=rank,
            chart_1_uid="A" * 14,
            chart_2_uid=chr(75 + rank) * 14,
            path=path,
        )

    rows = aggregate_similarity_algorithm_accuracy(path, include_v2=True)
    by_mode = {row["algorithm_mode"]: row for row in rows}

    assert by_mode["default"]["v2_top_25_average"] == 70.0
    assert by_mode["default"]["v2_bottom_25_average"] == 70.0
    assert by_mode["default"]["v2_top_25_chart_count"] == 1
    assert by_mode["big_3"]["v2_top_25_average"] == 70.0
    assert "Accuracy Scorer v2" in format_similarity_algorithm_accuracy_ranking_html(
        rows, expanded_rows=set(), highlight_color="#abcdef"
    )
    assert "v1 legacy" in format_similarity_algorithm_accuracy_ranking_html(
        rows, expanded_rows=set(), highlight_color="#abcdef"
    )


def test_accuracy_observation_is_appended_to_shared_algorithm_log(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    _append(path, "big 3", 61.5, 70)

    content = path.read_text(encoding="utf-8")
    assert "Perceived accuracy payload:" in content
    assert '"algorithm_mode": "big_3"' in content
    assert '"predicted_percent": 61.5' in content
    assert '"perceived_similarity_score": 70' in content
    assert '"perceived_similarity_not_applicable": false' in content
    assert '"user_reported_accuracy"' not in content
    assert '"chart_uids"' in content


def test_algorithm_accuracy_empty_state():
    assert "No algorithm-linked accuracy scores" in format_similarity_algorithm_accuracy_ranking([])


def test_custom_settings_are_ranked_as_numbered_distinct_algorithms(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    first = build_similarity_algorithm_snapshot("custom", {"use_placement": True, "weight_placement": 0.7})
    second = build_similarity_algorithm_snapshot("custom", {"use_placement": True, "weight_placement": 0.4})
    for pair, snapshot in (("AB", first), ("AC", second)):
        append_similarity_accuracy_observation(
            algorithm_mode="custom",
            algorithm_snapshot=snapshot,
            predicted_percent=80,
            user_reported_accuracy=80,
            not_applicable=False,
            chart_1_uid=pair[0] * 14,
            chart_2_uid=pair[1] * 14,
            path=path,
        )

    rows = aggregate_similarity_algorithm_accuracy(path)

    assert {row["display_name"] for row in rows} == {"Custom 1", "Custom 2"}
    assert all(row["sample_count"] == 1 for row in rows)


def test_relationship_override_updates_perception_for_every_prediction_of_pair(tmp_path):
    algorithm_path = tmp_path / "similarities_algorithm_log.txt"
    relationship_path = tmp_path / "chart_similarity_relationships.json"
    first = build_similarity_algorithm_snapshot("custom", {"use_placement": True, "weight_placement": 0.7})
    second = build_similarity_algorithm_snapshot("custom", {"use_placement": True, "weight_placement": 0.4})
    for snapshot, predicted, perceived in ((first, 90, 90), (second, 20, 20)):
        append_similarity_accuracy_observation(
            algorithm_mode="custom",
            algorithm_snapshot=snapshot,
            predicted_percent=predicted,
            user_reported_accuracy=perceived,
            not_applicable=False,
            chart_1_uid="A" * 14,
            chart_2_uid="B" * 14,
            path=algorithm_path,
        )
    relationship_path.write_text(
        json.dumps({
            "relationships": {
                "pair": {
                    "chart_uids": ["A" * 14, "B" * 14],
                    "user_reported_accuracy": 20,
                    "not_applicable": False,
                }
            }
        }),
        encoding="utf-8",
    )

    rows = aggregate_similarity_algorithm_accuracy(
        algorithm_path,
        relationship_path=relationship_path,
    )

    assert len(rows) == 2
    assert sorted(row["average_accuracy"] for row in rows) == [30.0, 100.0]


def test_custom_variant_identity_excludes_unrelated_all_or_nothing_setting(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    base = build_similarity_algorithm_snapshot(
        "custom",
        {
            "use_placement": True,
            "weight_placement": 1.0,
            "all_or_nothing_component": "aspect",
        },
    )
    changed_unrelated = build_similarity_algorithm_snapshot(
        "custom",
        {
            "use_placement": True,
            "weight_placement": 1.0,
            "all_or_nothing_component": "big_3",
        },
    )
    for pair, snapshot in (("AB", base), ("AC", changed_unrelated)):
        append_similarity_accuracy_observation(
            algorithm_mode="custom",
            algorithm_snapshot=snapshot,
            predicted_percent=80,
            user_reported_accuracy=80,
            not_applicable=False,
            chart_1_uid=pair[0] * 14,
            chart_2_uid=pair[1] * 14,
            path=path,
        )

    rows = aggregate_similarity_algorithm_accuracy(path)

    assert len(rows) == 1
    assert rows[0]["display_name"] == "Custom 1"
    assert rows[0]["sample_count"] == 2


def test_all_or_nothing_criteria_are_ranked_as_distinct_algorithms(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    for pair, criterion in (("AB", "aspect"), ("AC", "big_3")):
        snapshot = build_similarity_algorithm_snapshot(
            "all_or_nothing",
            {"all_or_nothing_component": criterion},
        )
        append_similarity_accuracy_observation(
            algorithm_mode="all_or_nothing",
            algorithm_snapshot=snapshot,
            predicted_percent=80,
            user_reported_accuracy=80,
            not_applicable=False,
            chart_1_uid=pair[0] * 14,
            chart_2_uid=pair[1] * 14,
            path=path,
        )

    rows = aggregate_similarity_algorithm_accuracy(path)

    assert len(rows) == 2
    assert {row["display_name"] for row in rows} == {
        "All Or Nothing — Aspect",
        "All Or Nothing — Big 3",
    }
    assert all(row["sample_count"] == 1 for row in rows)


def test_effective_default_comprehensive_and_all_or_nothing_settings_split_rankings(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    observations = (
        ("default", "AB", {"use_placement": True, "weight_placement": 0.7}),
        ("default", "AC", {"use_placement": True, "weight_placement": 0.4}),
        ("comprehensive", "AD", {"placement_weighting_mode": "generic"}),
        ("comprehensive", "AE", {"placement_weighting_mode": "hybrid"}),
        (
            "all_or_nothing",
            "AF",
            {"all_or_nothing_component": "inner_planet_placement", "placement_weighting_mode": "generic"},
        ),
        (
            "all_or_nothing",
            "AG",
            {"all_or_nothing_component": "inner_planet_placement", "placement_weighting_mode": "hybrid"},
        ),
    )
    for mode, pair, settings in observations:
        append_similarity_accuracy_observation(
            algorithm_mode=mode,
            algorithm_snapshot=build_similarity_algorithm_snapshot(mode, settings),
            predicted_percent=80,
            user_reported_accuracy=80,
            not_applicable=False,
            chart_1_uid=pair[0] * 14,
            chart_2_uid=pair[1] * 14,
            path=path,
        )

    rows = aggregate_similarity_algorithm_accuracy(path)

    assert len(rows) == 6
    assert {row["display_name"] for row in rows} == {
        "Default 1",
        "Default 2",
        "Comprehensive — Generic",
        "Comprehensive — Hybrid",
        "All Or Nothing — Inner Planet Placement (Generic)",
        "All Or Nothing — Inner Planet Placement (Hybrid)",
    }


def test_demographic_filter_splits_variants_but_irrelevant_all_or_nothing_placement_does_not(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    for pair, demographic in (("AB", "none"), ("AC", "sex")):
        settings = {
            "use_placement": True,
            "weight_placement": 0.7,
            "demographic_match_mode": demographic,
        }
        append_similarity_accuracy_observation(
            algorithm_mode="default",
            algorithm_snapshot=build_similarity_algorithm_snapshot("default", settings),
            predicted_percent=80,
            user_reported_accuracy=80,
            not_applicable=False,
            chart_1_uid=pair[0] * 14,
            chart_2_uid=pair[1] * 14,
            path=path,
        )
    for pair, placement_mode in (("AD", "generic"), ("AE", "hybrid")):
        settings = {
            "all_or_nothing_component": "aspect",
            "placement_weighting_mode": placement_mode,
            "demographic_match_mode": "none",
        }
        append_similarity_accuracy_observation(
            algorithm_mode="all_or_nothing",
            algorithm_snapshot=build_similarity_algorithm_snapshot("all_or_nothing", settings),
            predicted_percent=80,
            user_reported_accuracy=80,
            not_applicable=False,
            chart_1_uid=pair[0] * 14,
            chart_2_uid=pair[1] * 14,
            path=path,
        )

    rows = aggregate_similarity_algorithm_accuracy(path)
    default_rows = [row for row in rows if row["algorithm_mode"] == "default"]
    all_or_nothing_rows = [row for row in rows if row["algorithm_mode"] == "all_or_nothing"]

    assert len(default_rows) == 2
    assert len(all_or_nothing_rows) == 1
    assert all_or_nothing_rows[0]["sample_count"] == 2
    assert all_or_nothing_rows[0]["display_name"] == "All Or Nothing — Aspect"


def test_accuracy_ranking_html_has_highlight_header_links_and_expanded_weights():
    snapshot = build_similarity_algorithm_snapshot(
        "big_3", {"use_big_3": True, "weight_big_3": 1.0}
    )
    html = format_similarity_algorithm_accuracy_ranking_html(
        [{
            "algorithm_mode": "big_3",
            "average_accuracy": 91.0,
            "sample_count": 3,
            "algorithm_snapshot": snapshot,
        }],
        expanded_rows={0},
        highlight_color="#abcdef",
    )

    assert "font-weight:600; color:#abcdef" in html
    assert 'href="algorithm:0">Big 3</a>' in html
    assert "Big 3: 1 (on)" in html


def test_accuracy_ranking_html_marks_fixed_scorer_details_unavailable():
    html = format_similarity_algorithm_accuracy_ranking_html(
        [{
            "algorithm_mode": "generic_astro",
            "average_accuracy": 90.0,
            "sample_count": 2,
            "algorithm_snapshot": {
                "details_available": False,
                "details_unavailable_reason": "Generic Astro uses fixed weights.",
            },
        }],
        expanded_rows={0},
        highlight_color="#abcdef",
    )

    assert "Generic Astro uses fixed weights." in html
    assert "Placement: " not in html


def test_accuracy_ranking_html_disables_use_action_for_unrecoverable_custom_snapshot():
    html = format_similarity_algorithm_accuracy_ranking_html(
        [{
            "algorithm_mode": "custom",
            "display_name": "Custom 1",
            "average_accuracy": 88.0,
            "sample_count": 2,
            "algorithm_snapshot": {
                "details_available": False,
                "details_unavailable_reason": "Legacy custom weights were not logged.",
            },
        }],
        highlight_color="#abcdef",
    )

    assert 'href="use:0"' not in html
    assert ">unavailable</span>" in html
    assert 'title="Legacy custom weights were not logged."' in html


def test_accuracy_ranking_html_disables_legacy_all_or_nothing_without_criterion():
    html = format_similarity_algorithm_accuracy_ranking_html(
        [{
            "algorithm_mode": "all_or_nothing",
            "average_accuracy": 84.0,
            "sample_count": 3,
        }],
        highlight_color="#abcdef",
    )

    assert 'href="use:0"' not in html
    assert ">unavailable</span>" in html
    assert "selected criterion is unavailable" in html


def test_accuracy_ranking_html_disables_default_and_comprehensive_without_snapshots():
    for mode in ("default", "comprehensive"):
        html = format_similarity_algorithm_accuracy_ranking_html(
            [{
                "algorithm_mode": mode,
                "average_accuracy": 82.0,
                "sample_count": 2,
            }],
            highlight_color="#abcdef",
        )

        assert 'href="use:0"' not in html
        assert ">unavailable</span>" in html
        assert "Exact scorer settings are unavailable" in html


def test_accuracy_ranking_html_disables_fixed_modes_without_restorable_placement():
    for mode in ("generic_astro", "database_distinction"):
        html = format_similarity_algorithm_accuracy_ranking_html(
            [{
                "algorithm_mode": mode,
                "average_accuracy": 81.0,
                "sample_count": 2,
                "algorithm_snapshot": {
                    "details_available": False,
                    "placement_weighting_mode": "not_applicable",
                },
            }],
            highlight_color="#abcdef",
        )

        assert 'href="use:0"' not in html
        assert ">unavailable</span>" in html


def test_algorithm_accuracy_uses_prediction_error_not_raw_perceived_score(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    _append(path, "default", 90, 90)
    _append(path, "big_3", 10, 90)

    assert aggregate_similarity_algorithm_accuracy(path) == [
        {"algorithm_mode": "default", "average_accuracy": 100.0, "sample_count": 1},
        {"algorithm_mode": "big_3", "average_accuracy": 20.0, "sample_count": 1},
    ]


def test_legacy_payload_inherits_preceding_algorithm_mode(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    legacy_payload = {
        "chart_1_compared_with_chart_2": {
            "chart_1": {"id": 12},
            "chart_2": {"id": 4},
        },
        "predicted_percent": 75,
        "user_reported_accuracy": 77,
        "not_applicable": False,
    }
    path.write_text(
        "=== Similarities Algorithm Change #1 ===\nAlgorithm mode: comprehensive\n\n"
        "Perceived accuracy payload:\n" + json.dumps(legacy_payload) + "\n",
        encoding="utf-8",
    )

    assert aggregate_similarity_algorithm_accuracy(path) == [
        {"algorithm_mode": "comprehensive", "average_accuracy": 98.0, "sample_count": 1}
    ]


def test_legacy_observation_recovers_exact_settings_from_change_log(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    snapshot = build_similarity_algorithm_snapshot(
        "custom", {"use_placement": True, "weight_placement": 0.73}
    )
    legacy_payload = {
        "algorithm_mode": "custom",
        "chart_uids": ["A" * 14, "B" * 14],
        "predicted_percent": 75,
        "user_reported_accuracy": 77,
        "not_applicable": False,
    }
    path.write_text(
        "=== Similarities Algorithm Change #1 ===\n"
        "Algorithm mode: custom\n"
        "Opening snapshot:\n" + json.dumps(snapshot) + "\n"
        "Current settings upon close:\n" + json.dumps(snapshot) + "\n\n"
        "=== Similarity Perceived Accuracy ===\n"
        "Perceived accuracy payload:\n" + json.dumps(legacy_payload) + "\n",
        encoding="utf-8",
    )

    rows = aggregate_similarity_algorithm_accuracy(path)

    assert rows[0]["algorithm_snapshot"] == snapshot
    expanded = format_similarity_algorithm_accuracy_ranking_html(
        rows, expanded_rows={0}, highlight_color="#abcdef"
    )
    assert "Placement: 0.73 (on)" in expanded
    assert "Exact settings unavailable" not in expanded


def test_legacy_observation_uses_preceding_not_future_custom_snapshot(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    first = build_similarity_algorithm_snapshot(
        "custom", {"use_placement": True, "weight_placement": 0.73}
    )
    later = build_similarity_algorithm_snapshot(
        "custom", {"use_placement": True, "weight_placement": 0.21}
    )
    observation = {
        "algorithm_mode": "custom",
        "chart_uids": ["A" * 14, "B" * 14],
        "predicted_percent": 75,
        "user_reported_accuracy": 77,
        "not_applicable": False,
    }
    path.write_text(
        "Current settings upon close:\n" + json.dumps(first) + "\n"
        "Perceived accuracy payload:\n" + json.dumps(observation) + "\n"
        "Current settings upon close:\n" + json.dumps(later) + "\n",
        encoding="utf-8",
    )

    rows = aggregate_similarity_algorithm_accuracy(path)

    assert rows[0]["algorithm_snapshot"] == first


def test_legacy_fixed_mode_recovers_the_actual_scorer_not_custom_sliders(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    sliders = build_similarity_algorithm_snapshot(
        "big_3", {"use_placement": True, "weight_placement": 0.73}
    )
    observation = {
        "algorithm_mode": "big_3",
        "chart_uids": ["A" * 14, "B" * 14],
        "predicted_percent": 75,
        "perceived_similarity_score": 77,
        "perceived_similarity_not_applicable": False,
    }
    path.write_text(
        "Current settings upon close:\n" + json.dumps(sliders) + "\n"
        "Perceived accuracy payload:\n" + json.dumps(observation) + "\n",
        encoding="utf-8",
    )

    rows = aggregate_similarity_algorithm_accuracy(path)
    recovered = rows[0]["algorithm_snapshot"]

    factors = {row["factor"]: row for row in recovered["selected_factors"]}
    assert factors["big_3"] == {"factor": "big_3", "enabled": True, "weight": 1.0}
    assert factors["placement"] == {"factor": "placement", "enabled": False, "weight": 0.0}


def test_legacy_fixed_scorer_does_not_claim_custom_weights(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    sliders = build_similarity_algorithm_snapshot(
        "generic_astro", {"use_placement": True, "weight_placement": 0.73}
    )
    observation = {
        "algorithm_mode": "generic_astro",
        "chart_uids": ["A" * 14, "B" * 14],
        "predicted_percent": 75,
        "perceived_similarity_score": 77,
        "perceived_similarity_not_applicable": False,
    }
    path.write_text(
        "Current settings upon close:\n" + json.dumps(sliders) + "\n"
        "Perceived accuracy payload:\n" + json.dumps(observation) + "\n",
        encoding="utf-8",
    )

    recovered = aggregate_similarity_algorithm_accuracy(path)[0]["algorithm_snapshot"]

    assert recovered["details_available"] is False
    assert "fixed scorer" in recovered["details_unavailable_reason"]


def test_relationship_log_supplies_latest_score_without_recalculation(tmp_path):
    algorithm_path = tmp_path / "similarities_algorithm_log.txt"
    relationship_path = tmp_path / "chart_similarity_relationships.json"
    legacy_payload = {
        "chart_1_compared_with_chart_2": {
            "chart_1": {"id": 12},
            "chart_2": {"id": 4},
        },
        "algorithm_mode": "default",
        "predicted_percent": 70,
        "user_reported_accuracy": 40,
        "not_applicable": False,
    }
    algorithm_path.write_text(
        "Perceived accuracy payload:\n" + json.dumps(legacy_payload) + "\n",
        encoding="utf-8",
    )
    relationship_path.write_text(
        json.dumps({
            "relationships": {
                "4|12": {
                    "chart_ids": [4, 12],
                    "user_reported_accuracy": 88,
                    "not_applicable": False,
                }
            }
        }),
        encoding="utf-8",
    )

    assert aggregate_similarity_algorithm_accuracy(
        algorithm_path, relationship_path=relationship_path
    ) == [{"algorithm_mode": "default", "average_accuracy": 82.0, "sample_count": 1}]
