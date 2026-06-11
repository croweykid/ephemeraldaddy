import datetime as dt

from ephemeraldaddy.analysis.get_astro_twin import SimilarityCalculatorSettings
from ephemeraldaddy.gui.features.charts.similarities_algorithm_log import (
    append_similarity_algorithm_change_log,
    build_similarity_algorithm_snapshot,
    similarity_algorithm_snapshots_changed,
)


def test_similarity_algorithm_snapshot_detects_scoring_changes():
    opening = build_similarity_algorithm_snapshot("custom", SimilarityCalculatorSettings())
    changed_settings = SimilarityCalculatorSettings(
        use_placement=True,
        weight_placement=0.5,
        use_aspect=True,
        weight_aspect=0.5,
        use_distribution=False,
        weight_distribution=0.0,
        use_combined_dominance=False,
        weight_combined_dominance=0.0,
        use_nakshatra_placement=False,
        weight_nakshatra_placement=0.0,
        use_nakshatra_dominance=False,
        weight_nakshatra_dominance=0.0,
        use_defined_centers=False,
        weight_defined_centers=0.0,
        use_human_design_gates=False,
        weight_human_design_gates=0.0,
        use_human_design_channels=False,
        weight_human_design_channels=0.0,
        use_inner_planet_placement=False,
        weight_inner_planet_placement=0.0,
        use_outer_planet_placement=False,
        weight_outer_planet_placement=0.0,
    )
    current = build_similarity_algorithm_snapshot("custom", changed_settings)

    assert similarity_algorithm_snapshots_changed(opening, current) is True
    assert current["selected_total"] == 1.0
    assert {row["factor"]: row["weight"] for row in current["selected_factors"]}["placement"] == 0.5


def test_append_similarity_algorithm_change_log_writes_running_txt_log(tmp_path):
    log_path = tmp_path / "similarities_algorithm_log.txt"
    opening = build_similarity_algorithm_snapshot("custom", SimilarityCalculatorSettings())
    current = build_similarity_algorithm_snapshot(
        "custom",
        SimilarityCalculatorSettings(weight_placement=0.4, weight_human_design_gates=0.11),
    )

    returned = append_similarity_algorithm_change_log(
        opening_snapshot=opening,
        current_snapshot=current,
        path=log_path,
        timestamp=dt.datetime(2026, 6, 5, 12, 30, tzinfo=dt.timezone.utc),
    )
    append_similarity_algorithm_change_log(
        opening_snapshot=opening,
        current_snapshot=current,
        path=log_path,
        timestamp=dt.datetime(2026, 6, 5, 12, 31, tzinfo=dt.timezone.utc),
    )

    content = log_path.read_text(encoding="utf-8")
    assert returned == log_path
    assert "=== Similarities Algorithm Change #1 ===" in content
    assert "=== Similarities Algorithm Change #2 ===" in content
    assert "Timestamp (UTC): 2026-06-05T12:30:00+00:00" in content
    assert "Current settings upon close:" in content
    assert '"weight_placement": 0.4' in content


def test_perceived_accuracy_log_round_trips_latest_state(tmp_path):
    from ephemeraldaddy.gui.features.charts.similarities_algorithm_log import (
        append_similarity_perceived_accuracy_log,
        load_similarity_perceived_accuracy_states,
        perceived_accuracy_state_key,
    )

    log_path = tmp_path / "similarities_algorithm_log.txt"
    snapshot = build_similarity_algorithm_snapshot("custom", SimilarityCalculatorSettings())
    append_similarity_perceived_accuracy_log(
        chart_1_id=1,
        chart_1_name="Chart One",
        chart_2_id=2,
        chart_2_name="Chart Two",
        analysis_context="similarities",
        user_reported_accuracy=82,
        not_applicable=False,
        similarities_analysis="similarities analysis text",
        dissimilarities_analysis="dissimilarities analysis text",
        algorithm_snapshot=snapshot,
        path=log_path,
        timestamp=dt.datetime(2026, 6, 11, 10, 0, tzinfo=dt.timezone.utc),
    )
    append_similarity_perceived_accuracy_log(
        chart_1_id=1,
        chart_1_name="Chart One",
        chart_2_id=2,
        chart_2_name="Chart Two",
        analysis_context="similarities",
        user_reported_accuracy=None,
        not_applicable=True,
        similarities_analysis="new similarities analysis text",
        dissimilarities_analysis="new dissimilarities analysis text",
        algorithm_snapshot=snapshot,
        path=log_path,
        timestamp=dt.datetime(2026, 6, 11, 10, 1, tzinfo=dt.timezone.utc),
    )

    content = log_path.read_text(encoding="utf-8")
    assert "=== Similarity Perceived Accuracy #1 ===" in content
    assert "=== Similarity Perceived Accuracy #2 ===" in content
    assert "Chart 1 compared with chart 2: Chart One (#1) ↔ Chart Two (#2)" in content
    assert '"similarities_analysis": "new similarities analysis text"' in content
    state_key = perceived_accuracy_state_key(
        chart_1_id=1,
        chart_2_id=2,
        analysis_context="similarities",
    )
    states = load_similarity_perceived_accuracy_states(log_path)
    assert states[state_key]["not_applicable"] is True
    assert states[state_key]["user_reported_accuracy"] is None
