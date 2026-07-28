import datetime as dt
import json

from ephemeraldaddy.gui.features.charts.similarities_algorithm_log import (
    aggregate_similarity_algorithm_accuracy,
    append_similarity_accuracy_observation,
    format_similarity_algorithm_accuracy_ranking,
)


def _append(path, mode, predicted, perceived, *, not_applicable=False):
    append_similarity_accuracy_observation(
        algorithm_mode=mode,
        predicted_percent=predicted,
        user_reported_accuracy=perceived,
        not_applicable=not_applicable,
        chart_1_uid="AAAAAAAAAAAAAA",
        chart_2_uid="BBBBBBBBBBBBBB",
        path=path,
        timestamp=dt.datetime(2026, 7, 28, tzinfo=dt.timezone.utc),
    )


def test_algorithm_accuracy_aggregates_existing_algorithm_log(tmp_path):
    path = tmp_path / "similarities_algorithm_log.txt"
    _append(path, "default", 75, 90)
    _append(path, "big_3", 50, 70)
    _append(path, "default", 50, 80)
    _append(path, "big 3", 80, 60)

    rows = aggregate_similarity_algorithm_accuracy(path)

    assert rows == [
        {"algorithm_mode": "default", "average_accuracy": 85.0, "sample_count": 2},
        {"algorithm_mode": "big_3", "average_accuracy": 65.0, "sample_count": 2},
    ]
    assert "1. Default — 85.0% average (n=2)" in format_similarity_algorithm_accuracy_ranking(rows)


def test_algorithm_accuracy_reads_mixed_historical_log_and_skips_old_unlinked_payloads(tmp_path):
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
        {"algorithm_mode": "comprehensive", "average_accuracy": 90.0, "sample_count": 1}
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
