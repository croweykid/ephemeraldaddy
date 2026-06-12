import datetime as dt
import json

from ephemeraldaddy.gui.features.charts.chart_similarity_relationships import (
    chart_similarity_relationship_key,
    load_chart_similarity_relationship_states,
    save_chart_similarity_relationship,
)


def test_chart_similarity_relationship_file_round_trips_latest_state(tmp_path):
    relationship_path = tmp_path / "chart_similarity_relationships.json"
    returned = save_chart_similarity_relationship(
        chart_1_id=1,
        chart_1_name="Chart One",
        chart_2_id=2,
        chart_2_name="Chart Two",
        user_reported_accuracy=82,
        not_applicable=False,
        path=relationship_path,
        timestamp=dt.datetime(2026, 6, 11, 10, 0, tzinfo=dt.timezone.utc),
    )
    save_chart_similarity_relationship(
        chart_1_id=2,
        chart_1_name="Chart Two",
        chart_2_id=1,
        chart_2_name="Chart One",
        user_reported_accuracy=None,
        not_applicable=True,
        path=relationship_path,
        timestamp=dt.datetime(2026, 6, 11, 10, 1, tzinfo=dt.timezone.utc),
    )

    content = json.loads(relationship_path.read_text(encoding="utf-8"))
    state_key = chart_similarity_relationship_key(chart_1_id=1, chart_2_id=2)
    states = load_chart_similarity_relationship_states(
        relationship_path,
        include_legacy_algorithm_log=False,
    )

    assert returned == relationship_path
    assert set(content["relationships"]) == {"1|2"}
    assert content["relationships"][state_key]["user_knows_similarity"] is False
    assert states[state_key]["not_applicable"] is True
    assert states[state_key]["user_reported_accuracy"] is None
    assert states[state_key]["user_perceived_similarity_score"] is None


def test_chart_similarity_relationship_key_is_pair_stable_and_algorithm_independent():
    forward = chart_similarity_relationship_key(chart_1_id=12, chart_2_id=4)
    reverse = chart_similarity_relationship_key(chart_1_id=4, chart_2_id=12)

    assert forward == reverse == "4|12"


def test_relationship_loader_normalizes_legacy_algorithm_log_entries(tmp_path):
    relationship_path = tmp_path / "chart_similarity_relationships.json"
    legacy_log_path = tmp_path / "similarities_algorithm_log.txt"
    legacy_log_path.write_text(
        "\n".join(
            [
                "=== Similarity Perceived Accuracy #1 ===",
                "Perceived accuracy payload:",
                json.dumps(
                    {
                        "state_key": "12|4|similarities",
                        "chart_1_compared_with_chart_2": {
                            "chart_1": {"id": 12, "name": "A"},
                            "chart_2": {"id": 4, "name": "B"},
                        },
                        "analysis_context": "similarities",
                        "user_reported_accuracy": 77,
                        "not_applicable": False,
                    }
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    normalized_key = chart_similarity_relationship_key(chart_1_id=4, chart_2_id=12)
    states = load_chart_similarity_relationship_states(
        relationship_path,
        legacy_algorithm_log_path=legacy_log_path,
    )

    assert states[normalized_key]["source"] == "legacy_similarities_algorithm_log"
    assert states[normalized_key]["user_reported_accuracy"] == 77
    assert states[normalized_key]["user_knows_similarity"] is True


def test_relationship_file_overrides_legacy_algorithm_log_for_same_pair(tmp_path):
    relationship_path = tmp_path / "chart_similarity_relationships.json"
    legacy_log_path = tmp_path / "similarities_algorithm_log.txt"
    legacy_log_path.write_text(
        "\n".join(
            [
                "=== Similarity Perceived Accuracy #1 ===",
                "Perceived accuracy payload:",
                json.dumps(
                    {
                        "chart_1_compared_with_chart_2": {
                            "chart_1": {"id": 12, "name": "A"},
                            "chart_2": {"id": 4, "name": "B"},
                        },
                        "user_reported_accuracy": 77,
                        "not_applicable": False,
                    }
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    save_chart_similarity_relationship(
        chart_1_id=4,
        chart_1_name="B",
        chart_2_id=12,
        chart_2_name="A",
        user_reported_accuracy=20,
        not_applicable=False,
        path=relationship_path,
    )

    states = load_chart_similarity_relationship_states(
        relationship_path,
        legacy_algorithm_log_path=legacy_log_path,
    )

    assert states["4|12"]["user_reported_accuracy"] == 20
    assert "source" not in states["4|12"]


def test_chart_similarity_relationship_uses_uid_key_when_available(tmp_path):
    relationship_path = tmp_path / "chart_similarity_relationships.json"
    save_chart_similarity_relationship(
        chart_1_id=1,
        chart_1_uid="ABC12345ZZZZ9999",
        chart_1_name="Chart One",
        chart_2_id=2,
        chart_2_uid="DEF67890YYYY8888",
        chart_2_name="Chart Two",
        user_reported_accuracy=82,
        not_applicable=False,
        path=relationship_path,
    )

    content = json.loads(relationship_path.read_text(encoding="utf-8"))
    uid_key = chart_similarity_relationship_key(
        chart_1_id=1,
        chart_2_id=2,
        chart_1_uid="ABC12345ZZZZ9999",
        chart_2_uid="DEF67890YYYY8888",
    )
    states = load_chart_similarity_relationship_states(
        relationship_path,
        include_legacy_algorithm_log=False,
    )

    assert set(content["relationships"]) == {uid_key}
    assert content["relationships"][uid_key]["chart_uids"] == [
        "ABC12345ZZZZ9999",
        "DEF67890YYYY8888",
    ]
    assert states[uid_key]["user_reported_accuracy"] == 82
    assert states["1|2"] == states[uid_key]


def test_relationship_migration_rekeys_existing_integer_relationships(tmp_path):
    from ephemeraldaddy.gui.features.charts.chart_similarity_relationships import (
        migrate_chart_similarity_relationship_file_to_chart_uids,
    )

    relationship_path = tmp_path / "chart_similarity_relationships.json"
    relationship_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "relationships": {
                    "1|2": {
                        "relationship_key": "1|2",
                        "chart_ids": [1, 2],
                        "user_reported_accuracy": 55,
                        "user_perceived_similarity_score": 55,
                        "not_applicable": False,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    migrate_chart_similarity_relationship_file_to_chart_uids(
        chart_id_to_uid={1: "ABC12345ZZZZ9999", 2: "DEF67890YYYY8888"},
        path=relationship_path,
    )

    content = json.loads(relationship_path.read_text(encoding="utf-8"))
    uid_key = "uid:ABC12345ZZZZ9999|uid:DEF67890YYYY8888"
    assert content["schema_version"] == 2
    assert set(content["relationships"]) == {uid_key}
    assert content["relationships"][uid_key]["chart_ids"] == [1, 2]
    assert content["relationships"][uid_key]["chart_uids"] == [
        "ABC12345ZZZZ9999",
        "DEF67890YYYY8888",
    ]
