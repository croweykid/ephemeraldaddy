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
