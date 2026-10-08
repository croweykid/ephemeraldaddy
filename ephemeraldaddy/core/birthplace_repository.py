"""Non-destructive, UID-owned locality metadata for legacy birthplaces."""

from __future__ import annotations

from dataclasses import dataclass
import math
import sqlite3

from ephemeraldaddy.analysis.birthplace import BirthplaceLocality, locality_from_text


@dataclass(frozen=True)
class BirthplaceSource:
    chart_uid: str
    raw: str
    latitude: float | None
    longitude: float | None

    @property
    def key(self):
        return self.chart_uid, self.raw, self.latitude, self.longitude

    @property
    def has_coordinates(self):
        return (
            self.latitude is not None and self.longitude is not None
            and math.isfinite(self.latitude) and math.isfinite(self.longitude)
            and -90 <= self.latitude <= 90 and -180 <= self.longitude <= 180
        )


def create_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chart_birthplace_localities (
            chart_uid TEXT PRIMARY KEY,
            source_text TEXT NOT NULL,
            source_lat REAL,
            source_lon REAL,
            city TEXT NOT NULL,
            region TEXT NOT NULL,
            country TEXT NOT NULL
        )
    """)


def load_cached(conn: sqlite3.Connection, chart_uids=None) -> dict[tuple, BirthplaceLocality]:
    query = ("SELECT chart_uid, source_text, source_lat, source_lon, city, region, country "
             "FROM chart_birthplace_localities")
    params = ()
    if chart_uids is not None:
        params = tuple(dict.fromkeys(chart_uids))
        if not params:
            return {}
        if len(params) > 500:
            combined = {}
            for offset in range(0, len(params), 500):
                combined.update(load_cached(conn, params[offset:offset + 500]))
            return combined
        query += " WHERE chart_uid IN (" + ",".join("?" for _ in params) + ")"
    return {
        (uid, raw, lat, lon): BirthplaceLocality(city, region, country)
        for uid, raw, lat, lon, city, region, country in conn.execute(query, params)
    }


def cached_or_parsed(source: BirthplaceSource, cache: dict) -> BirthplaceLocality:
    return cache.get(source.key, locality_from_text(source.raw))


def store_if_current(conn, source: BirthplaceSource, locality: BirthplaceLocality) -> bool:
    """Reject deleted or edited charts; never UPDATE the factual charts row."""
    if not locality.city or not locality.country:
        return False
    current = conn.execute(
        "SELECT 1 FROM charts WHERE chart_uid = ? AND COALESCE(birth_place, '') = ? "
        "AND lat IS ? AND lon IS ?", source.key,
    ).fetchone()
    if current is None:
        return False
    conn.execute(
        "INSERT INTO chart_birthplace_localities VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(chart_uid) DO UPDATE SET source_text=excluded.source_text, "
        "source_lat=excluded.source_lat, source_lon=excluded.source_lon, "
        "city=excluded.city, region=excluded.region, country=excluded.country",
        (*source.key, locality.city, locality.region, locality.country),
    )
    return True
