import json

from ephemeraldaddy.gui.features.charts.chart_similarity_relationships import (
    save_chart_similarity_relationship,
)
from ephemeraldaddy.gui.features.charts.similarities_algorithm_log import (
    aggregate_similarity_algorithm_accuracy,
    format_similarity_algorithm_accuracy_ranking,
)


def test_algorithm_accuracy_aggregates_and_ranks_recorded_predictions(tmp_path):
    path = tmp_path / "relationships.json"
    path.write_text(json.dumps({"relationships": {
        "uid:A|uid:B": {
            "user_reported_accuracy": 80,
            "not_applicable": False,
            "algorithm_observations": {
                "default": {"predicted_percent": 75},
                "big_3": {"predicted_percent": 50},
            },
        },
        "uid:A|uid:C": {
            "user_reported_accuracy": 40,
            "not_applicable": False,
            "algorithm_observations": {
                "default": {"predicted_percent": 50},
                "big_3": {"predicted_percent": 80},
            },
        },
    }}), encoding="utf-8")

    rows = aggregate_similarity_algorithm_accuracy(path)

    assert rows == [
        {"algorithm_mode": "default", "average_accuracy": 92.5, "sample_count": 2},
        {"algorithm_mode": "big_3", "average_accuracy": 65.0, "sample_count": 2},
    ]
    assert "1. Default — 92.5% average (n=2)" in format_similarity_algorithm_accuracy_ranking(rows)


def test_algorithm_accuracy_skips_na_and_unscored_records(tmp_path):
    path = tmp_path / "relationships.json"
    path.write_text(json.dumps({"relationships": {
        "uid:A|uid:B": {
            "user_reported_accuracy": None,
            "not_applicable": True,
            "algorithm_observations": {"default": {"predicted_percent": 90}},
        }
    }}), encoding="utf-8")

    assert aggregate_similarity_algorithm_accuracy(path) == []
    assert "No algorithm-linked accuracy scores" in format_similarity_algorithm_accuracy_ranking([])


def test_relationship_save_retains_observations_for_multiple_algorithms(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.charts.chart_similarity_relationships.get_alternate_chart_uid_groups",
        lambda: {},
    )
    path = tmp_path / "relationships.json"
    common = {
        "chart_1_id": 1,
        "chart_1_name": "A",
        "chart_1_uid": "AAAAAAAAAAAAAA",
        "chart_2_id": 2,
        "chart_2_name": "B",
        "chart_2_uid": "BBBBBBBBBBBBBB",
        "user_reported_accuracy": 80,
        "not_applicable": False,
        "path": path,
    }
    save_chart_similarity_relationship(
        **common, algorithm_mode="default", predicted_percent=75, ranking_position=1
    )
    save_chart_similarity_relationship(
        **common, algorithm_mode="big 3", predicted_percent=60, ranking_position=4
    )

    observations = next(iter(json.loads(path.read_text())["relationships"].values()))[
        "algorithm_observations"
    ]
    assert observations["default"]["ranking_position"] == 1
    assert observations["big_3"]["predicted_percent"] == 60
