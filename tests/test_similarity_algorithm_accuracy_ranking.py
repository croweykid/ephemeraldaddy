import datetime as dt
import json

from ephemeraldaddy.gui.features.charts.similarities_algorithm_log import (
    aggregate_similarity_algorithm_accuracy,
    append_similarity_accuracy_observation,
    format_similarity_algorithm_accuracy_ranking,
)


def _append(path, mode, predicted, perceived, *, not_applicable=False, pair="AB"):
    append_similarity_accuracy_observation(
        algorithm_mode=mode,
        predicted_percent=predicted,
        user_reported_accuracy=perceived,
        not_applicable=not_applicable,
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


def test_accuracy_observation_is_appended_to_shared_algorithm_log(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    _append(path, "big 3", 61.5, 70)

    content = path.read_text(encoding="utf-8")
    assert "Perceived accuracy payload:" in content
    assert '"algorithm_mode": "big_3"' in content
    assert '"predicted_percent": 61.5' in content
    assert '"chart_uids"' in content


def test_algorithm_accuracy_empty_state():
    assert "No algorithm-linked accuracy scores" in format_similarity_algorithm_accuracy_ranking([])


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
