from threading import Event
from types import SimpleNamespace
import sqlite3

import pytest

from ephemeraldaddy.analysis.birthplace import BirthplaceLocality, chart_locality
from ephemeraldaddy.core import db, birthplace_repository as repository


RAW = "United States Post Office, 12 Main Street, Atlanta, Fulton County, Georgia, 30303, United States"
UID = "ABCDEF0123456789"


@pytest.fixture
def saved_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "charts.db")
    db.init_db_once(force=True)
    with sqlite3.connect(db.DB_PATH) as conn:
        conn.execute(
            "INSERT INTO charts(chart_uid, name, birth_place, datetime_iso, lat, lon, "
            "created_at, is_placeholder, tz_name, birthtime_unknown, retcon_hour, retcon_minute) "
            "VALUES (?, 'Chart', ?, '2000-01-02T03:04:00+00:00', 33.7491, -84.3882, "
            "'2026-10-08T00:00:00+00:00', 1, 'America/New_York', 1, 12, 30)",
            (UID, RAW),
        )
    return db.DB_PATH


def test_retroactive_repair_changes_display_and_analytics_without_touching_birth_record(saved_db):
    with sqlite3.connect(saved_db) as conn:
        before = conn.execute("SELECT * FROM charts").fetchall()
        changes_before = conn.execute("SELECT * FROM chart_change_log").fetchall()
    assert "Post Office" not in db.list_charts()[0][5]
    calls = []
    def resolver(lat, lon):
        calls.append((lat, lon))
        return BirthplaceLocality("Atlanta", "Georgia", "USA")
    changed = db.repair_birthplace_localities(
        resolver, cancel_event=Event(), attempted=set(),
    )
    assert changed == {UID}
    assert calls == [(33.7491, -84.3882)]
    assert db.list_charts()[0][5] == "Atlanta, Georgia, USA"
    chart = db.load_chart_by_uid(UID)
    assert chart.birth_place == RAW
    assert chart_locality(chart).components == ("Atlanta", "Georgia", "USA")
    with sqlite3.connect(saved_db) as conn:
        assert conn.execute("SELECT * FROM charts").fetchall() == before
        assert conn.execute("SELECT * FROM chart_change_log").fetchall() == changes_before
        assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
    # Restart/repeat uses durable locality metadata, without another request.
    assert db.repair_birthplace_localities(
        lambda *args: pytest.fail("Re-resolved a cached locality"),
        cancel_event=Event(), attempted=set(),
    ) == set()


@pytest.mark.parametrize("edit", [
    "UPDATE charts SET birth_place='Paris, France'",
    "UPDATE charts SET lat=48.8566",
    "DELETE FROM charts",
])
def test_inflight_result_is_discarded_after_edit_or_deletion(saved_db, edit):
    def resolver(lat, lon):
        with sqlite3.connect(saved_db) as conn:
            conn.execute(edit)
        return BirthplaceLocality("Atlanta", "Georgia", "USA")
    assert not db.repair_birthplace_localities(
        resolver, cancel_event=Event(), attempted=set(),
    )
    with sqlite3.connect(saved_db) as conn:
        assert conn.execute("SELECT count(*) FROM chart_birthplace_localities").fetchone() == (0,)


def test_failed_lookup_retains_original_data_and_is_attempted_once_per_session(saved_db):
    calls, attempted = [], set()
    def unavailable(lat, lon):
        calls.append((lat, lon))
        raise ValueError("No administrative result")
    for _ in range(2):
        assert not db.repair_birthplace_localities(
            unavailable, cancel_event=Event(), attempted=attempted,
        )
    assert len(calls) == 1
    assert "Post Office" not in db.list_charts()[0][5]
    with sqlite3.connect(saved_db) as conn:
        assert conn.execute("SELECT birth_place FROM charts").fetchone() == (RAW,)


def test_cancellation_prevents_writing_inflight_response(saved_db):
    event = Event()
    def resolver(lat, lon):
        event.set()
        return BirthplaceLocality("Atlanta", "Georgia", "USA")
    assert not db.repair_birthplace_localities(resolver, cancel_event=event, attempted=set())


def test_roster_and_birth_analytics_use_the_same_corrected_city(saved_db):
    from ephemeraldaddy.gui.features.charts.database_analytics import DatabaseAnalyticsChartsMixin
    db.repair_birthplace_localities(
        lambda *args: BirthplaceLocality("Atlanta", "Georgia", "USA"),
        cancel_event=Event(), attempted=set(),
    )
    chart = db.load_chart_by_uid(UID)
    class Analytics(DatabaseAnalyticsChartsMixin):
        def _get_chart_for_filter(self, chart_id):
            return chart
        def _is_placeholder_chart(self, chart):
            return True
    counts = Analytics()._collect_birth_analytics([1])
    assert counts["city_counts"] == {"Atlanta": 1}
    assert counts["country_counts"] == {"USA": 1}
    assert counts["us_state_counts"] == {"GA": 1}
    assert db.list_charts()[0][5] == "Atlanta, Georgia, USA"


def test_identical_coordinate_points_reuse_metadata_without_another_request(saved_db):
    with sqlite3.connect(saved_db) as conn:
        conn.execute(
            "INSERT INTO charts(chart_uid, name, birth_place, datetime_iso, lat, lon, created_at) "
            "SELECT '0123456789ABCDEF', name, birth_place, datetime_iso, lat, lon, created_at FROM charts"
        )
    calls = []
    def resolver(lat, lon):
        calls.append((lat, lon))
        return BirthplaceLocality("Atlanta", "Georgia", "USA")
    assert len(db.repair_birthplace_localities(
        resolver, cancel_event=Event(), attempted=set(),
    )) == 2
    assert calls == [(33.7491, -84.3882)]
