from threading import Event
from types import SimpleNamespace
import sqlite3

import pytest

from ephemeraldaddy.analysis.birthplace import BirthplaceLocality, chart_locality
from ephemeraldaddy.core import backups, db, birthplace_repository as repository
from ephemeraldaddy.io import geocode, local_gazetteer


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


@pytest.mark.parametrize("selection", ["one", "none", "all"])
def test_database_export_only_keeps_localities_owned_by_exported_charts(saved_db, tmp_path, selection):
    other_uid = "0123456789ABCDEF"
    with sqlite3.connect(saved_db) as conn:
        conn.execute(
            "INSERT INTO charts(chart_uid, name, birth_place, datetime_iso, lat, lon, created_at) "
            "SELECT ?, 'Excluded', birth_place, datetime_iso, lat, lon, created_at FROM charts",
            (other_uid,),
        )
        for uid in (UID, other_uid):
            assert repository.store_if_current(
                conn, repository.BirthplaceSource(uid, RAW, 33.7491, -84.3882),
                BirthplaceLocality("Atlanta", "Georgia", "USA"),
            )
        # Previously deleted charts can also leave cached metadata behind.
        conn.execute(
            "INSERT INTO chart_birthplace_localities VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("DELETED0123456789", "Private building", 1, 2, "Private city", "Region", "Country"),
        )
        chart_rows = conn.execute("SELECT * FROM charts").fetchall()
        locality_rows = conn.execute("SELECT * FROM chart_birthplace_localities").fetchall()
        selected_id = conn.execute("SELECT id FROM charts WHERE chart_uid = ?", (UID,)).fetchone()[0]

    selected_ids = {"one": [selected_id], "none": [], "all": None}[selection]
    exported = db.export_database_with_chart_property_selection(
        tmp_path / "export.db", [], included_chart_ids=selected_ids,
    )
    expected_uids = {"one": {UID}, "none": set(), "all": {UID, other_uid}}[selection]
    with sqlite3.connect(exported) as conn:
        assert {row[0] for row in conn.execute("SELECT chart_uid FROM charts")} == expected_uids
        exported_localities = conn.execute("SELECT * FROM chart_birthplace_localities").fetchall()
        assert exported_localities == [row for row in locality_rows if row[0] in expected_uids]
    with sqlite3.connect(saved_db) as conn:
        assert conn.execute("SELECT * FROM charts").fetchall() == chart_rows
        assert conn.execute("SELECT * FROM chart_birthplace_localities").fetchall() == locality_rows


@pytest.mark.parametrize("source_kind", ["db", "edbackup"])
@pytest.mark.parametrize("collision", [False, True])
def test_append_preserves_localities_and_remaps_colliding_uids(saved_db, tmp_path, source_kind, collision):
    with sqlite3.connect(saved_db) as conn:
        assert repository.store_if_current(
            conn, repository.BirthplaceSource(UID, RAW, 33.7491, -84.3882),
            BirthplaceLocality("Atlanta", "Georgia", "USA"),
        )
        target_locality = conn.execute("SELECT * FROM chart_birthplace_localities").fetchone()

    source_path = tmp_path / "source.db"
    source_uid = UID if collision else "0123456789ABCDEF"
    source_raw = "Courthouse, 1 Main Street, Georgia, United States"
    with sqlite3.connect(source_path) as conn:
        db._ensure_schema(conn)
        conn.execute(
            "INSERT INTO charts(chart_uid, name, birth_place, datetime_iso, lat, lon, created_at, is_placeholder) "
            "VALUES (?, 'Appended', ?, '2000-01-02T03:04:00+00:00', 32.0809, -81.0912, '2026-10-08', 1)",
            (source_uid, source_raw),
        )
        assert repository.store_if_current(
            conn, repository.BirthplaceSource(source_uid, source_raw, 32.0809, -81.0912),
            BirthplaceLocality("Savannah", "Georgia", "USA"),
        )
        source_locality = conn.execute("SELECT * FROM chart_birthplace_localities").fetchone()
    source = source_path
    if source_kind == "edbackup":
        source = backups.create_backup_package(
            tmp_path / "source.edbackup",
            component_source_overrides={"charts": source_path}, included_component_keys={"charts"},
        )

    result = db.append_database(source)
    assert result["imported"] == 1
    imported_uid, = result["imported_uids"]
    assert (imported_uid != source_uid) is collision
    with sqlite3.connect(saved_db) as conn:
        assert conn.execute(
            "SELECT * FROM chart_birthplace_localities WHERE chart_uid = ?", (UID,),
        ).fetchone() == target_locality
        assert conn.execute(
            "SELECT * FROM chart_birthplace_localities WHERE chart_uid = ?", (imported_uid,),
        ).fetchone() == (imported_uid, *source_locality[1:])
        assert conn.execute(
            "SELECT birth_place, lat, lon FROM charts WHERE chart_uid = ?", (imported_uid,),
        ).fetchone() == (source_raw, 32.0809, -81.0912)
    # Confirmed locality must remain available without another online lookup.
    assert chart_locality(db.load_chart_by_uid(imported_uid)).components == ("Savannah", "Georgia", "USA")
    assert db.list_charts()[1][5] == "Savannah, Georgia, USA"
    assert db.repair_birthplace_localities(
        lambda *args: pytest.fail("Appended locality requested another lookup"),
        cancel_event=Event(), attempted=set(),
    ) == set()
    with sqlite3.connect(source_path) as conn:
        assert conn.execute("SELECT * FROM chart_birthplace_localities").fetchone() == source_locality


@pytest.mark.parametrize("stale_field", ["source_text", "source_lat", "source_lon"])
def test_append_rejects_stale_orphaned_and_skipped_chart_localities(saved_db, tmp_path, stale_field):
    with sqlite3.connect(saved_db) as conn:
        assert repository.store_if_current(
            conn, repository.BirthplaceSource(UID, RAW, 33.7491, -84.3882),
            BirthplaceLocality("Atlanta", "Georgia", "USA"),
        )
        before = conn.execute("SELECT * FROM chart_birthplace_localities").fetchall()
    source_path = tmp_path / "stale.db"
    with sqlite3.connect(source_path) as conn:
        db._ensure_schema(conn)
        for uid, name, clock in (("0123456789ABCDEF", "Stale", "2000-01-02T03:04:00+00:00"),
                                 ("FEDCBA9876543210", "Skipped", "")):
            conn.execute(
                "INSERT INTO charts(chart_uid, name, birth_place, datetime_iso, lat, lon, created_at, is_placeholder) "
                "VALUES (?, ?, ?, ?, 33.7491, -84.3882, '2026-10-08', 1)",
                (uid, name, RAW, clock),
            )
        for uid in ("0123456789ABCDEF", "FEDCBA9876543210", UID):
            conn.execute(
                "INSERT INTO chart_birthplace_localities VALUES (?, ?, ?, ?, ?, ?, ?)",
                (uid, RAW, 33.7491, -84.3882, "Wrong city", "Georgia", "USA"),
            )
        stale_value = "Old building" if stale_field == "source_text" else 1.0
        conn.execute(
            f"UPDATE chart_birthplace_localities SET {stale_field} = ? WHERE chart_uid = ?",
            (stale_value, "0123456789ABCDEF"),
        )
    result = db.append_database(source_path)
    assert result["imported"] == 1 and result["skipped"] == 1
    with sqlite3.connect(saved_db) as conn:
        assert conn.execute("SELECT * FROM chart_birthplace_localities").fetchall() == before
    assert chart_locality(db.load_chart_by_uid(result["imported_uids"][0])).city == ""


def test_legacy_database_without_locality_table_can_be_exported_and_appended(saved_db, tmp_path, monkeypatch):
    with sqlite3.connect(saved_db) as conn:
        conn.execute("DROP TABLE chart_birthplace_localities")
        conn.execute("PRAGMA user_version = 23")
    exported = db.export_database_with_chart_property_selection(tmp_path / "legacy-export.db", [])
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "target.db")
    result = db.append_database(exported)
    assert result["imported"] == 1
    with sqlite3.connect(db.DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM chart_birthplace_localities").fetchone() == (0,)


def test_append_locality_failure_rolls_back_chart_rows_and_completion_log(saved_db, tmp_path, monkeypatch):
    with sqlite3.connect(saved_db) as conn:
        assert repository.store_if_current(
            conn, repository.BirthplaceSource(UID, RAW, 33.7491, -84.3882),
            BirthplaceLocality("Atlanta", "Georgia", "USA"),
        )
        before = conn.execute("SELECT * FROM charts").fetchall()
        before_localities = conn.execute("SELECT * FROM chart_birthplace_localities").fetchall()
    source = db.backup_database(tmp_path / "source.db")

    def fail(*args):
        raise sqlite3.OperationalError("Locality write failed")

    monkeypatch.setattr(repository, "store_if_current", fail)
    with pytest.raises(sqlite3.OperationalError, match="Locality write failed"):
        db.append_database(source, import_key="failed-locality-append")
    with sqlite3.connect(saved_db) as conn:
        assert conn.execute("SELECT * FROM charts").fetchall() == before
        assert conn.execute("SELECT * FROM chart_birthplace_localities").fetchall() == before_localities
        assert conn.execute("SELECT COUNT(*) FROM backup_append_log").fetchone() == (0,)


@pytest.mark.parametrize("api", ["uids", "legacy"])
def test_chart_deletion_removes_owned_localities_and_preserves_other_charts(saved_db, tmp_path, api):
    other_uid = "0123456789ABCDEF"
    with sqlite3.connect(saved_db) as conn:
        conn.execute(
            "INSERT INTO charts(chart_uid, name, birth_place, datetime_iso, lat, lon, created_at) "
            "SELECT ?, 'Retained', birth_place, datetime_iso, lat, lon, created_at FROM charts",
            (other_uid,),
        )
        for uid in (UID, other_uid):
            assert repository.store_if_current(
                conn, repository.BirthplaceSource(uid, RAW, 33.7491, -84.3882),
                BirthplaceLocality("Atlanta", "Georgia", "USA"),
            )
        selected_id = conn.execute("SELECT id FROM charts WHERE chart_uid = ?", (UID,)).fetchone()[0]
    deleted = db.delete_charts_by_uids([UID, "missing"]) if api == "uids" else db.delete_charts([selected_id])
    assert deleted == 1
    with sqlite3.connect(saved_db) as conn:
        assert conn.execute("SELECT chart_uid FROM charts").fetchall() == [(other_uid,)]
        assert conn.execute("SELECT chart_uid FROM chart_birthplace_localities").fetchall() == [(other_uid,)]
        assert not repository.store_if_current(
            conn, repository.BirthplaceSource(UID, RAW, 33.7491, -84.3882),
            BirthplaceLocality("Atlanta", "Georgia", "USA"),
        )
    backup = db.backup_database(tmp_path / "after-delete.db")
    with sqlite3.connect(backup) as conn:
        assert conn.execute("SELECT chart_uid FROM chart_birthplace_localities").fetchall() == [(other_uid,)]


def test_failed_chart_deletion_rolls_back_locality_cleanup(saved_db):
    with sqlite3.connect(saved_db) as conn:
        assert repository.store_if_current(
            conn, repository.BirthplaceSource(UID, RAW, 33.7491, -84.3882),
            BirthplaceLocality("Atlanta", "Georgia", "USA"),
        )
        before = conn.execute("SELECT * FROM chart_birthplace_localities").fetchall()
        conn.execute("CREATE TRIGGER prevent_delete BEFORE DELETE ON charts "
                     "BEGIN SELECT RAISE(ABORT, 'Deletion failed'); END")
    with pytest.raises(sqlite3.IntegrityError, match="Deletion failed"):
        db.delete_charts_by_uids([UID])
    with sqlite3.connect(saved_db) as conn:
        assert conn.execute("SELECT chart_uid FROM charts").fetchall() == [(UID,)]
        assert conn.execute("SELECT * FROM chart_birthplace_localities").fetchall() == before


def test_database_initialization_purges_localities_from_earlier_deletions(saved_db, tmp_path):
    with sqlite3.connect(saved_db) as conn:
        assert repository.store_if_current(
            conn, repository.BirthplaceSource(UID, RAW, 33.7491, -84.3882),
            BirthplaceLocality("Atlanta", "Georgia", "USA"),
        )
        before = conn.execute("SELECT * FROM chart_birthplace_localities").fetchall()
        conn.execute("INSERT INTO chart_birthplace_localities VALUES (?, ?, ?, ?, ?, ?, ?)",
                     ("DELETED0123456789", "Private building", 1, 2, "Private city", "Region", "Country"))
    db.init_db_once(force=True)
    backup = db.backup_database(tmp_path / "initialized.db")
    for path in (saved_db, backup):
        with sqlite3.connect(path) as conn:
            assert conn.execute("SELECT * FROM chart_birthplace_localities").fetchall() == before


@pytest.fixture
def populated_places(tmp_path, monkeypatch):
    path = tmp_path / "gazetteer.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE places(id INTEGER PRIMARY KEY, label TEXT, latitude REAL, "
                     "longitude REAL, population INTEGER, search_text TEXT)")
        conn.executemany("INSERT INTO places VALUES (?, ?, ?, ?, ?, ?)", [
            (1, "Washington, DC, US", 38.89511, -77.03637, 689545, "washington dc us"),
            (2, "Hospital, 02, CR", 9.934, -84.084, 10000, "hospital 02 cr"),
        ])
    gazetteer = local_gazetteer.LocalGazetteer(path)
    monkeypatch.setenv("EPHEMERALDADDY_GAZETTEER_DB", str(path))
    monkeypatch.setenv("EPHEMERALDADDY_GAZETTEER_ONLY", "1")
    monkeypatch.setattr(local_gazetteer, "_LOCAL_GAZETTEER", gazetteer)
    monkeypatch.setattr(local_gazetteer, "_LOCAL_GAZETTEER_ERROR", None)
    monkeypatch.setattr(local_gazetteer, "_download_and_build", lambda *args: pytest.fail("Downloaded while reading a birthplace"))
    monkeypatch.setattr(geocode, "_get_geolocator", lambda: pytest.fail("Requested online geocoding"))
    yield path
    current = local_gazetteer._LOCAL_GAZETTEER
    if current is not None and current is not gazetteer:
        current.close()
    gazetteer.close()


@pytest.mark.parametrize("query,expected", [
    ("Washington", ("Washington", "District of Columbia", "USA")),
    ("Hospital", ("Hospital", "", "Costa Rica")),
])
@pytest.mark.parametrize("operation", ["save", "update", "existing"])
def test_gazetteer_cities_survive_saved_chart_round_trip_and_offline_backfill(
    saved_db, populated_places, monkeypatch, tmp_path, query, expected, operation,
):
    lat, lon, label = geocode.geocode_location(query)
    assert geocode.search_locations(query) == [(label, lat, lon)]
    assert label == ", ".join(part for part in expected if part)
    chart = db.load_chart_by_uid(UID)
    chart.lat, chart.lon, chart.birth_place = lat, lon, str(label)
    uid = UID
    if operation == "save":
        db.save_chart(chart, birth_place=str(label), is_placeholder=True)
        uid = chart.chart_uid
    elif operation == "update":
        db.update_chart_by_uid(uid, chart, birth_place=str(label))
    else:
        with sqlite3.connect(saved_db) as conn:
            conn.execute("UPDATE charts SET birth_place = ?, lat = ?, lon = ? WHERE chart_uid = ?",
                         (str(label), lat, lon, uid))

    assert chart_locality(db.load_chart_by_uid(uid)).components == tuple(part or None for part in expected)
    assert label in [row[5] for row in db.list_charts()]
    from ephemeraldaddy.gui.features.charts.database_analytics import DatabaseAnalyticsChartsMixin
    loaded = db.load_chart_by_uid(uid)
    class Analytics(DatabaseAnalyticsChartsMixin):
        def _get_chart_for_filter(self, chart_id):
            return loaded
        def _is_placeholder_chart(self, chart):
            return True
    counts = Analytics()._collect_birth_analytics([1])
    assert counts["city_counts"] == {expected[0]: 1}
    assert counts["country_counts"] == {expected[2]: 1}
    if operation == "existing":
        # A restarted app can verify an old saved result using the existing file.
        monkeypatch.setattr(local_gazetteer, "_LOCAL_GAZETTEER", None)
        changed = db.repair_birthplace_localities(
            lambda *args: None, cancel_event=Event(), attempted=set(),
        )
        assert uid in changed
    with sqlite3.connect(saved_db) as conn:
        assert conn.execute(
            "SELECT city, region, country FROM chart_birthplace_localities WHERE chart_uid = ?", (uid,),
        ).fetchone() == expected
    # Persisted provenance survives even if the gazetteer later becomes unavailable.
    current = local_gazetteer._LOCAL_GAZETTEER
    if current is not None and operation == "existing":
        current.close()
    monkeypatch.setattr(local_gazetteer, "_LOCAL_GAZETTEER", None)
    monkeypatch.setenv("EPHEMERALDADDY_GAZETTEER_DB", str(tmp_path / "missing-gazetteer.sqlite"))
    assert chart_locality(db.load_chart_by_uid(uid)).components == tuple(part or None for part in expected)


@pytest.mark.parametrize("raw,lat,lon", [
    ("Hospital, Costa Rica", 9.935, -84.084),
    ("Hospital, Costa Rica", 9.934, -84.085),
    ("Government Building, Costa Rica", 9.934, -84.084),
])
def test_gazetteer_does_not_confirm_a_nearby_city_or_a_different_label(populated_places, raw, lat, lon):
    chart = SimpleNamespace(birth_place=raw, lat=lat, lon=lon)
    assert chart_locality(chart).city == ""


def test_reading_saved_birthplace_does_not_build_or_download_a_missing_gazetteer(tmp_path, monkeypatch):
    path = tmp_path / "missing-gazetteer.sqlite"
    monkeypatch.setenv("EPHEMERALDADDY_GAZETTEER_DB", str(path))
    monkeypatch.setattr(local_gazetteer, "_LOCAL_GAZETTEER", None)
    monkeypatch.setattr(local_gazetteer, "_LOCAL_GAZETTEER_ERROR", None)
    monkeypatch.setattr(local_gazetteer, "build_db", lambda *args: pytest.fail("Built a gazetteer during display"))
    monkeypatch.setattr(local_gazetteer, "_download_and_build", lambda *args: pytest.fail("Downloaded during display"))
    chart = SimpleNamespace(birth_place="Hospital, Costa Rica", lat=9.934, lon=-84.084)
    assert chart_locality(chart).city == ""
    assert not path.exists()
