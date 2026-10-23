"""Regression coverage for Type 1 CSV preflight modes and retryable errors."""
from __future__ import annotations

import csv

import pytest

from ephemeraldaddy.gui.features.import_export.type1_csv import (
    build_placeholder,
    is_header,
    parse_record,
    partial_birth_date,
    validate_calculable_record,
    write_failures,
)


def test_simple_type1_rows_include_optional_subjective_notes():
    rec = parse_record(["Ada Lovelace", "1815-12-10", "London", "Notes", "Augusta"])
    assert (rec.name, rec.birth_place, rec.notes, rec.alias) == (
        "Ada Lovelace", "London", "Notes", "Augusta"
    )
    validate_calculable_record(rec, 1500, 2100)


def test_exported_csv_header_reorders_fields_and_preserves_coordinates():
    header = [
        "id", "name", "birth_place", "datetime_iso", "tz_name", "latitude",
        "longitude", "used_utc_fallback", "sentiments", "relationship_types",
        "positive_sentiment_intensity", "negative_sentiment_intensity",
        "familiarity", "dominant_planet_weights", "dominant_sign_weights",
        "chart_type", "source",
    ]
    assert is_header(header)
    row = [
        "17", "Test person", "New York", "2000-01-02T03:04:00",
        "America/New_York", "40.71", "-74.00", "0", "", "", "", "",
        "", "{}", "{}", "public_db", "public_db",
    ]
    rec = parse_record(row, header)
    assert rec.builder_row[0] == "0"
    assert rec.builder_row[1:4] == ["Test person", "New York", "2000-01-02T03:04:00"]
    assert rec.builder_row[5:7] == ["40.71", "-74.00"]
    validate_calculable_record(rec, 1500, 2100)


@pytest.mark.parametrize("row,issue", [
    (["", "2000-01-01", "Boston"], "name"),
    (["Name", "bad date", "Boston"], "birth date"),
    (["Name", "", "Boston"], "birth date"),
    (["Name", "2000-01-01", ""], "Birthplace"),
    (["Name", "1200-01-01", "Boston"], "outside"),
])
def test_standard_charts_reject_missing_or_bad_essentials(row, issue):
    with pytest.raises(ValueError, match=issue):
        validate_calculable_record(parse_record(row), 1500, 2100)


def test_placeholder_accepts_bad_date_and_missing_location_without_calculation():
    rec = parse_record(["Unnamed location", "1990-05", "", "Social context"])
    placeholder = build_placeholder(rec, "personal")
    assert placeholder.is_placeholder
    assert (placeholder.birth_month, placeholder.birth_day, placeholder.birth_year) == (
        5, None, 1990
    )
    assert placeholder.birth_place == ""
    assert "Social context" in placeholder.comments
    assert "1990-05" in placeholder.comments
    assert placeholder.positions == {}


def test_placeholder_retains_unparseable_date_as_subjective_text():
    placeholder = build_placeholder(parse_record(["Subject", "maybe April 1891"]), "public_db")
    assert placeholder.birth_year is None
    assert "maybe April 1891" in placeholder.comments


def test_partial_dates_remain_partial():
    assert partial_birth_date("1881") == (None, None, 1881)
    assert partial_birth_date("1881-06") == (6, None, 1881)


def test_failed_rows_csv_has_diagnostics_and_can_be_resubmitted(tmp_path):
    original = tmp_path / "input.csv"
    original.write_text("name,birth_date,birth_place,notes\n", encoding="utf-8")
    header = ["name", "birth_date", "birth_place", "notes"]
    report = write_failures(
        original,
        [(3, ["Person", "bad date", "London", "Context"], "Unrecognized date")],
        header,
    )
    assert report is not None
    with report.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == header + ["import_error", "source_row"]
    assert rows[1] == ["Person", "bad date", "London", "Context", "Unrecognized date", "3"]
    assert is_header(rows[0])
    record = parse_record(rows[1], rows[0])
    assert record.name == "Person"
    assert record.notes == "Context"
    assert record.date_text == "bad date"


def test_headerless_retry_report_is_recognized(tmp_path):
    source = tmp_path / "list.csv"
    report = write_failures(source, [(1, ["Person", "bad date", "London"], "Bad date")], None)
    with report.open(newline="", encoding="utf-8") as handle:
        header, row = list(csv.reader(handle))
    assert is_header(header)
    record = parse_record(row, header)
    assert record.builder_row == ["Person", "bad date", "London"]


def test_legacy_id_first_rows_preserve_export_fields():
    raw = ["12", "Name", "Earth", "2001-04-05", "UTC", "1", "2", "0", "", ""]
    rec = parse_record(raw)
    assert rec.builder_row == raw
    assert rec.name == "Name"
    assert rec.birth_place == "Earth"
