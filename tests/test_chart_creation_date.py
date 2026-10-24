"""Regression coverage for Chart View's persisted creation-date label."""

from datetime import timedelta, timezone
from pathlib import Path

from ephemeraldaddy.gui.features.charts.chart_creation_date import format_chart_created_at


ROOT = Path(__file__).resolve().parents[1]


def test_creation_date_display_converts_utc_to_local_date():
    eastern = timezone(timedelta(hours=-4))
    assert format_chart_created_at(
        "2026-10-25T02:30:00+00:00", display_tz=eastern
    ) == "Created Oct 24, 2026"


def test_creation_date_accepts_naive_legacy_utc_and_z_suffix():
    utc = timezone.utc
    assert format_chart_created_at("2026-01-03T12:00:00", display_tz=utc) == "Created Jan 3, 2026"
    assert format_chart_created_at("2026-01-03T12:00:00Z", display_tz=utc) == "Created Jan 3, 2026"


def test_creation_date_is_hidden_when_timestamp_missing_or_invalid():
    for timestamp in (None, "", "garbled"):
        assert format_chart_created_at(timestamp) == ""


def test_chart_header_is_bound_to_uid_lifecycle_not_chart_name():
    app = (ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
    header = (ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text(encoding="utf-8")
    setter = app.split("    def _set_current_chart_uid(", 1)[1].split("    def _clear_current_chart_uid(", 1)[0]
    clearer = app.split("    def _clear_current_chart_uid(", 1)[1].split("    def _current_chart_uid_for_navigation(", 1)[0]
    assert "update_chart_creation_date_label(self, normalized_uid)" in setter
    assert "update_chart_creation_date_label(self, None)" in clearer
    assert "addWidget(owner.database_view_button" in header
    assert "addWidget(owner.chart_creation_date_label" in header
    assert "get_chart_created_at_by_uid(chart_uid)" in header
