from __future__ import annotations

import io
import sqlite3
from pathlib import Path
from uuid import uuid4
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

from ephemeraldaddy.core import db, photo_gallery


def _image_bytes(color: str) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (12, 12), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _isolated_db(monkeypatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "charts.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "_SCHEMA_READY", False)
    monkeypatch.setattr(db, "_SCHEMA_READY_DB_PATH", None)
    monkeypatch.setattr(photo_gallery, "DB_PATH", db_path)
    return db_path


def _insert_chart(chart_uid: str) -> None:
    conn = db._get_conn()
    with conn:
        conn.execute(
            """
            INSERT INTO charts (chart_uid, name, datetime_iso, lat, lon, created_at)
            VALUES (?, 'Photo Test', '2000-01-01T00:00:00+00:00', 0, 0, '2026-01-01T00:00:00+00:00')
            """,
            (chart_uid,),
        )
    conn.close()


def test_first_uploaded_photo_becomes_profile_pic(monkeypatch, tmp_path):
    _isolated_db(monkeypatch, tmp_path)
    chart_uid = str(uuid4()).upper()
    _insert_chart(chart_uid)

    first_id = photo_gallery._insert_photo(chart_uid, _image_bytes("gold"), source="first", filename="first.png")
    second_id = photo_gallery._insert_photo(chart_uid, _image_bytes("blue"), source="second", filename="second.png")

    assert photo_gallery.get_profile_photo_id(chart_uid) == first_id
    assert db.get_chart_profile_pic(chart_uid) == str(first_id)
    assert second_id != first_id


def test_setting_and_deleting_profile_pic_keeps_metadata_valid(monkeypatch, tmp_path):
    _isolated_db(monkeypatch, tmp_path)
    chart_uid = str(uuid4()).upper()
    _insert_chart(chart_uid)
    first_id = photo_gallery._insert_photo(chart_uid, _image_bytes("red"), source="first", filename="first.png")
    second_id = photo_gallery._insert_photo(chart_uid, _image_bytes("green"), source="second", filename="second.png")

    assert photo_gallery.set_profile_photo(chart_uid, second_id) is True
    assert photo_gallery.get_profile_photo_id(chart_uid) == second_id

    assert photo_gallery.delete_photo(second_id, chart_uid) is True
    assert photo_gallery.get_profile_photo_id(chart_uid) == first_id

    assert photo_gallery.delete_photo(first_id, chart_uid) is True
    assert photo_gallery.get_profile_photo_id(chart_uid) is None
    assert db.get_chart_profile_pic(chart_uid) == ""


def test_stale_profile_pic_is_replaced_by_next_upload(monkeypatch, tmp_path):
    _isolated_db(monkeypatch, tmp_path)
    chart_uid = str(uuid4()).upper()
    _insert_chart(chart_uid)
    db.set_chart_profile_pic(chart_uid, "999999")

    photo_id = photo_gallery._insert_photo(chart_uid, _image_bytes("purple"), source="only", filename="only.png")

    assert photo_gallery.get_profile_photo_id(chart_uid) == photo_id
    assert db.get_chart_profile_pic(chart_uid) == str(photo_id)
