from dataclasses import replace
import sqlite3
from types import MappingProxyType

import pytest

from ephemeraldaddy.core import db
from ephemeraldaddy.core.sidereal import NakshatraPosition, SiderealChartData
from ephemeraldaddy.core.sidereal_repository import SiderealChartDataRepository


def _database():
    connection = sqlite3.connect(":memory:")
    db._ensure_schema(connection)
    connection.execute(
        """INSERT INTO charts
        (chart_uid, name, datetime_iso, lat, lon, created_at)
        VALUES ('PARENT01', 'Parent', '2000-01-01T12:00:00+00:00', 0, 0, 'now')"""
    )
    return connection


def _snapshot(token="token-1"):
    return SiderealChartData(
        chart_uid="PARENT01", ayanamsha="lahiri", ayanamsha_degrees=23.8,
        calculation_version=1, source_recalculation_token=token,
        positions=MappingProxyType({"Sun": 256.2}),
        retrogrades=MappingProxyType({"Sun": False}),
        ascendant=None, mc=None, house_cusps=None, aspects=(),
        nakshatras=MappingProxyType({"Sun": NakshatraPosition(19, "Purva Ashadha", 4, 9.5)}),
    )


def test_schema_and_repository_are_uid_first_idempotent_and_stale_aware():
    connection = _database()
    db._ensure_schema(connection)
    repository = SiderealChartDataRepository(connection)
    repository.upsert(_snapshot())
    repository.upsert(_snapshot())

    assert connection.execute("SELECT count(*) FROM sidereal_chart_data").fetchone()[0] == 1
    assert repository.get("parent01", source_token="token-1").positions["Sun"] == 256.2
    assert repository.get("parent01", source_token="stale-token") is None


def test_repository_rejects_orphans_and_parent_delete_cleans_snapshot():
    connection = _database()
    repository = SiderealChartDataRepository(connection)
    orphan = replace(_snapshot(), chart_uid="MISSING01")
    with pytest.raises(ValueError):
        repository.upsert(orphan)

    repository.upsert(_snapshot())
    connection.execute("DELETE FROM charts WHERE chart_uid = 'PARENT01'")
    assert connection.execute("SELECT count(*) FROM sidereal_chart_data").fetchone()[0] == 0


def test_schema_rejects_orphans_even_when_repository_is_bypassed():
    connection = _database()

    with pytest.raises(
        sqlite3.IntegrityError,
        match="requires an existing parent chart_uid",
    ):
        connection.execute(
            """
            INSERT INTO sidereal_chart_data (
                chart_uid, ayanamsha, ayanamsha_degrees, calculation_version,
                source_recalculation_token, positions, retrogrades,
                aspects, nakshatras, updated_at
            ) VALUES ('MISSING01', 'lahiri', 23.8, 1, 'token', '{}', '{}', '[]', '{}', 'now')
            """
        )


def test_person_data_edit_does_not_delete_or_stale_snapshot():
    connection = _database()
    repository = SiderealChartDataRepository(connection)
    repository.upsert(_snapshot())
    connection.execute("UPDATE charts SET biography = 'shared edit' WHERE chart_uid = 'PARENT01'")

    assert repository.get("PARENT01", source_token="token-1") is not None
