"""SQLite repository for rebuildable Sidereal D1 snapshots."""

from __future__ import annotations

from dataclasses import asdict
import json
import sqlite3
from types import MappingProxyType

from ephemeraldaddy.core.sidereal import NakshatraPosition, SiderealChartData


class SiderealChartDataRepository:
    """UID-first storage boundary; the supplied connection owns transactions."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def get(
        self, chart_uid: str, *, ayanamsha: str = "lahiri", source_token: str | None = None
    ) -> SiderealChartData | None:
        uid = _normalize_uid(chart_uid)
        row = self._connection.execute(
            """
            SELECT ayanamsha_degrees, calculation_version,
                   source_recalculation_token, positions, retrogrades,
                   ascendant, mc, house_cusps, aspects, nakshatras
            FROM sidereal_chart_data
            WHERE chart_uid = ? AND ayanamsha = ?
            """,
            (uid, ayanamsha.strip().lower()),
        ).fetchone()
        if row is None or (source_token is not None and row[2] != source_token):
            return None
        positions = json.loads(row[3])
        retrogrades = json.loads(row[4])
        houses = json.loads(row[7]) if row[7] is not None else None
        aspects = json.loads(row[8])
        raw_nakshatras = json.loads(row[9])
        return SiderealChartData(
            chart_uid=uid,
            ayanamsha=ayanamsha.strip().lower(),
            ayanamsha_degrees=float(row[0]),
            calculation_version=int(row[1]),
            source_recalculation_token=str(row[2]),
            positions=MappingProxyType({str(key): float(value) for key, value in positions.items()}),
            retrogrades=MappingProxyType({str(key): bool(value) for key, value in retrogrades.items()}),
            ascendant=None if row[5] is None else float(row[5]),
            mc=None if row[6] is None else float(row[6]),
            house_cusps=None if houses is None else tuple(float(value) for value in houses),
            aspects=tuple(MappingProxyType(dict(value)) for value in aspects),
            nakshatras=MappingProxyType({
                str(key): NakshatraPosition(**value) for key, value in raw_nakshatras.items()
            }),
        )

    def upsert(self, data: SiderealChartData) -> None:
        uid = _normalize_uid(data.chart_uid)
        parent = self._connection.execute(
            "SELECT 1 FROM charts WHERE chart_uid = ?", (uid,)
        ).fetchone()
        if parent is None:
            raise ValueError(f"Unknown parent chart UID {uid!r}")
        self._connection.execute(
            """
            INSERT INTO sidereal_chart_data (
                chart_uid, ayanamsha, ayanamsha_degrees, calculation_version,
                source_recalculation_token, positions, retrogrades, ascendant,
                mc, house_cusps, aspects, nakshatras, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            ON CONFLICT(chart_uid, ayanamsha) DO UPDATE SET
                ayanamsha_degrees = excluded.ayanamsha_degrees,
                calculation_version = excluded.calculation_version,
                source_recalculation_token = excluded.source_recalculation_token,
                positions = excluded.positions,
                retrogrades = excluded.retrogrades,
                ascendant = excluded.ascendant,
                mc = excluded.mc,
                house_cusps = excluded.house_cusps,
                aspects = excluded.aspects,
                nakshatras = excluded.nakshatras,
                updated_at = excluded.updated_at
            """,
            (
                uid, data.ayanamsha, data.ayanamsha_degrees, data.calculation_version,
                data.source_recalculation_token,
                _json(dict(data.positions)), _json(dict(data.retrogrades)),
                data.ascendant, data.mc,
                None if data.house_cusps is None else _json(data.house_cusps),
                _json([dict(value) for value in data.aspects]),
                _json({key: asdict(value) for key, value in data.nakshatras.items()}),
            ),
        )

    def delete(self, chart_uid: str, *, ayanamsha: str | None = None) -> int:
        uid = _normalize_uid(chart_uid)
        if ayanamsha is None:
            cursor = self._connection.execute(
                "DELETE FROM sidereal_chart_data WHERE chart_uid = ?", (uid,)
            )
        else:
            cursor = self._connection.execute(
                "DELETE FROM sidereal_chart_data WHERE chart_uid = ? AND ayanamsha = ?",
                (uid, ayanamsha.strip().lower()),
            )
        return int(cursor.rowcount)


def _normalize_uid(value: str) -> str:
    uid = "".join(character for character in str(value or "").strip().upper() if character.isalnum())
    if len(uid) < 8:
        raise ValueError("chart_uid is required")
    return uid[:64]


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
