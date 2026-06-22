import datetime as dt
import json

from ephemeraldaddy.gui.features.charts.chart_similarity_relationships import (
    chart_similarity_relationship_key,
    load_chart_similarity_relationship_states,
    migrate_perceived_similarity_scores_to_alternate_chart,
    save_chart_similarity_relationship,
)


def test_chart_similarity_relationship_file_round_trips_latest_state(tmp_path):
    relationship_path = tmp_path / "chart_similarity_relationships.json"
    returned = save_chart_similarity_relationship(
        chart_1_id=1,
        chart_1_name="Chart One",
        chart_1_uid="ONEUID0000000001",
        chart_2_id=2,
        chart_2_name="Chart Two",
        chart_2_uid="TWOUID0000000002",
        user_reported_accuracy=82,
        not_applicable=False,
        path=relationship_path,
        timestamp=dt.datetime(2026, 6, 11, 10, 0, tzinfo=dt.timezone.utc),
    )
    save_chart_similarity_relationship(
        chart_1_id=2,
        chart_1_name="Chart Two",
        chart_1_uid="TWOUID0000000002",
        chart_2_id=1,
        chart_2_name="Chart One",
        chart_2_uid="ONEUID0000000001",
        user_reported_accuracy=None,
        not_applicable=True,
        path=relationship_path,
        timestamp=dt.datetime(2026, 6, 11, 10, 1, tzinfo=dt.timezone.utc),
    )

    content = json.loads(relationship_path.read_text(encoding="utf-8"))
    state_key = chart_similarity_relationship_key(
        chart_1_id=1,
        chart_2_id=2,
        chart_1_uid="ONEUID0000000001",
        chart_2_uid="TWOUID0000000002",
    )
    states = load_chart_similarity_relationship_states(
        relationship_path,
        include_legacy_algorithm_log=False,
    )

    assert returned == relationship_path
    assert set(content["relationships"]) == {state_key}
    assert content["relationships"][state_key]["user_knows_similarity"] is False
    assert states[state_key]["not_applicable"] is True
    assert states[state_key]["user_reported_accuracy"] is None
    assert states[state_key]["user_perceived_similarity_score"] is None


def test_chart_similarity_relationship_key_is_pair_stable_and_algorithm_independent():
    forward = chart_similarity_relationship_key(chart_1_id=12, chart_2_id=4)
    reverse = chart_similarity_relationship_key(chart_1_id=4, chart_2_id=12)

    assert forward == reverse == "4|12"


def test_linked_hypothetical_migrates_existing_scores_without_overwrite(tmp_path):
    relationship_path = tmp_path / "chart_similarity_relationships.json"
    real_uid = "REALUID00000001"
    hypo_uid = "HYPOUID00000001"
    other_uid = "OTHERUID0000001"

    save_chart_similarity_relationship(
        chart_1_id=1,
        chart_1_name="Real",
        chart_1_uid=real_uid,
        chart_2_id=2,
        chart_2_name="Other",
        chart_2_uid=other_uid,
        user_reported_accuracy=80,
        not_applicable=False,
        path=relationship_path,
    )
    save_chart_similarity_relationship(
        chart_1_id=3,
        chart_1_name="Hypo",
        chart_1_uid=hypo_uid,
        chart_2_id=2,
        chart_2_name="Other",
        chart_2_uid=other_uid,
        user_reported_accuracy=55,
        not_applicable=False,
        path=relationship_path,
    )

    migrated = migrate_perceived_similarity_scores_to_alternate_chart(
        source_chart_uid=real_uid,
        hypothetical_chart_uid=hypo_uid,
        path=relationship_path,
    )
    hypo_key = chart_similarity_relationship_key(
        chart_1_id=None,
        chart_2_id=None,
        chart_1_uid=hypo_uid,
        chart_2_uid=other_uid,
    )
    states = load_chart_similarity_relationship_states(relationship_path, include_legacy_algorithm_log=False)

    assert migrated == 0
    assert states[hypo_key]["user_reported_accuracy"] == 55


def test_linked_hypothetical_scores_update_in_unison(monkeypatch, tmp_path):
    relationship_path = tmp_path / "chart_similarity_relationships.json"
    real_uid = "REALUID00000001"
    hypo_uid = "HYPOUID00000001"
    other_uid = "OTHERUID0000001"
    monkeypatch.setattr(
        "ephemeraldaddy.gui.features.charts.chart_similarity_relationships.get_alternate_chart_uid_groups",
        lambda: {real_uid: [real_uid, hypo_uid]},
    )

    save_chart_similarity_relationship(
        chart_1_id=1,
        chart_1_name="Real",
        chart_1_uid=real_uid,
        chart_2_id=2,
        chart_2_name="Other",
        chart_2_uid=other_uid,
        user_reported_accuracy=91,
        not_applicable=False,
        path=relationship_path,
    )
    hypo_key = chart_similarity_relationship_key(
        chart_1_id=None,
        chart_2_id=None,
        chart_1_uid=hypo_uid,
        chart_2_uid=other_uid,
    )
    states = load_chart_similarity_relationship_states(relationship_path, include_legacy_algorithm_log=False)

    assert states[hypo_key]["user_reported_accuracy"] == 91


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
        chart_1_uid="FOURUID00000001",
        chart_2_id=12,
        chart_2_name="A",
        chart_2_uid="TWELVEUID000001",
        user_reported_accuracy=20,
        not_applicable=False,
        path=relationship_path,
    )

    states = load_chart_similarity_relationship_states(
        relationship_path,
        legacy_algorithm_log_path=legacy_log_path,
    )

    uid_key = "uid:FOURUID00000001|uid:TWELVEUID000001"
    assert states[uid_key]["user_reported_accuracy"] == 20
    assert states["4|12"] == states[uid_key]
    assert "source" not in states[uid_key]


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
    backup_path = relationship_path.with_name("chart_similarity_relationships.pre_uid_migration.json")
    backup_content = json.loads(backup_path.read_text(encoding="utf-8"))

    assert backup_path.exists()
    assert backup_content["relationships"]["1|2"]["relationship_key"] == "1|2"
    assert content["schema_version"] == 2
    assert content["uid_migration"]["migrated_relationships"] == 1
    assert set(content["relationships"]) == {uid_key}
    assert content["relationships"][uid_key]["chart_ids"] == [1, 2]
    assert content["relationships"][uid_key]["legacy_relationship_key"] == "1|2"
    assert content["relationships"][uid_key]["legacy_chart_ids"] == [1, 2]
    assert content["relationships"][uid_key]["chart_uids"] == [
        "ABC12345ZZZZ9999",
        "DEF67890YYYY8888",
    ]


def test_relationship_migration_can_resolve_ids_from_legacy_key_without_chart_ids(tmp_path):
    from ephemeraldaddy.gui.features.charts.chart_similarity_relationships import (
        migrate_chart_similarity_relationship_file_to_chart_uids,
    )

    relationship_path = tmp_path / "chart_similarity_relationships.json"
    relationship_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "relationships": {
                    "12|4": {
                        "relationship_key": "12|4",
                        "user_reported_accuracy": 60,
                        "user_perceived_similarity_score": 60,
                        "not_applicable": False,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    migrate_chart_similarity_relationship_file_to_chart_uids(
        chart_id_to_uid={4: "FOURUID00000001", 12: "TWELVEUID000001"},
        path=relationship_path,
    )

    content = json.loads(relationship_path.read_text(encoding="utf-8"))
    uid_key = "uid:FOURUID00000001|uid:TWELVEUID000001"
    assert set(content["relationships"]) == {uid_key}
    assert content["relationships"][uid_key]["chart_ids"] == [12, 4]
    assert content["relationships"][uid_key]["chart_uids"] == [
        "TWELVEUID000001",
        "FOURUID00000001",
    ]
    assert content["relationships"][uid_key]["legacy_relationship_key"] == "12|4"


def test_relationship_migration_leaves_unmapped_relationships_unchanged(tmp_path):
    from ephemeraldaddy.gui.features.charts.chart_similarity_relationships import (
        migrate_chart_similarity_relationship_file_to_chart_uids,
    )

    relationship_path = tmp_path / "chart_similarity_relationships.json"
    original_payload = {
        "schema_version": 1,
        "relationships": {
            "1|999": {
                "relationship_key": "1|999",
                "chart_ids": [1, 999],
                "user_reported_accuracy": 45,
                "not_applicable": False,
            }
        },
    }
    relationship_path.write_text(json.dumps(original_payload), encoding="utf-8")

    migrate_chart_similarity_relationship_file_to_chart_uids(
        chart_id_to_uid={1: "ONEUID000000001"},
        path=relationship_path,
    )

    assert json.loads(relationship_path.read_text(encoding="utf-8")) == original_payload
    assert not relationship_path.with_name("chart_similarity_relationships.pre_uid_migration.json").exists()


def test_translator_maps_former_relationship_ids_to_uid_keys(tmp_path):
    from ephemeraldaddy.gui.features.charts.chart_similarity_relationships import (
        translate_former_chart_similarity_relationship_ids,
    )

    relationship_path = tmp_path / "chart_similarity_relationships.json"
    relationship_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "relationships": {
                    "12|4": {
                        "relationship_key": "12|4",
                        "user_reported_accuracy": 60,
                        "not_applicable": False,
                    },
                    "7|999": {
                        "relationship_key": "7|999",
                        "chart_ids": [7, 999],
                        "user_reported_accuracy": 10,
                        "not_applicable": False,
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    translations = translate_former_chart_similarity_relationship_ids(
        chart_id_to_uid={4: "FOURUID00000001", 12: "TWELVEUID000001", 7: "SEVENUID0000001"},
        path=relationship_path,
    )

    assert translations == {
        "12|4": "uid:FOURUID00000001|uid:TWELVEUID000001",
        "4|12": "uid:FOURUID00000001|uid:TWELVEUID000001",
    }


def test_save_relationship_requires_both_chart_uids(tmp_path):
    relationship_path = tmp_path / "chart_similarity_relationships.json"

    try:
        save_chart_similarity_relationship(
            chart_1_id=1,
            chart_1_name="Chart One",
            chart_2_id=2,
            chart_2_name="Chart Two",
            chart_1_uid="ONEUID0000000001",
            chart_2_uid=None,
            user_reported_accuracy=70,
            not_applicable=False,
            path=relationship_path,
        )
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected missing chart UID to fail")

    assert "Refusing to save chart similarity relationship without stable chart UIDs" in message
    assert "Chart Two (id=2)" in message
    assert not relationship_path.exists()


def test_relationship_migration_strict_invalid_json_fails_loudly(tmp_path):
    from ephemeraldaddy.gui.features.charts.chart_similarity_relationships import (
        migrate_chart_similarity_relationship_file_to_chart_uids,
    )

    relationship_path = tmp_path / "chart_similarity_relationships.json"
    relationship_path.write_text('{"relationships": ', encoding="utf-8")

    try:
        migrate_chart_similarity_relationship_file_to_chart_uids(
            chart_id_to_uid={1: "ONEUID0000000001"},
            path=relationship_path,
            fail_on_invalid_json=True,
        )
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected invalid JSON to fail")

    assert "Could not parse" in message
    assert "line 1" in message
    assert "relationship log was left unchanged" in message
    assert relationship_path.read_text(encoding="utf-8") == '{"relationships": '


def test_conversion_report_formatter_lists_unresolved_chart_names():
    from ephemeraldaddy.gui.features.charts.chart_similarity_relationships import (
        ChartSimilarityRelationshipConversionIssue,
        ChartSimilarityRelationshipConversionReport,
        format_chart_similarity_relationship_conversion_report,
    )

    report = ChartSimilarityRelationshipConversionReport(
        relationship_path="/tmp/chart_similarity_relationships.json",
        report_path="/tmp/chart_similarity_relationships.uid_conversion_report.json",
        backup_path="/tmp/chart_similarity_relationships.pre_uid_migration.json",
        uid_backed_relationships=3,
        legacy_key_relationships=1,
        issue_count=1,
        issues=[
            ChartSimilarityRelationshipConversionIssue(
                relationship_key="7|999",
                chart_ids=[7, 999],
                chart_names=["Alice Example (id=7)", "Chart #999"],
                reason="missing UID for Chart #999",
            )
        ],
    )

    message = format_chart_similarity_relationship_conversion_report(report)

    assert "Alice Example (id=7), Chart #999" in message
    assert "missing UID for Chart #999" in message
    assert "Conversion report:" in message
