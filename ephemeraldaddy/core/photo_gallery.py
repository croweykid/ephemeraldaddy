"""External photo-gallery storage keyed by stable chart UID."""

from __future__ import annotations

import io
import mimetypes
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from PIL import Image, ImageOps

from ephemeraldaddy.core.db import DB_PATH, get_chart_uid

PHOTO_GALLERY_FILENAME = "charts.photo_gallery.db"
MAX_PHOTO_DIMENSION = 600
PHOTO_DPI = (96, 96)


def photo_gallery_path() -> Path:
    return DB_PATH.with_name(PHOTO_GALLERY_FILENAME)


def _connect() -> sqlite3.Connection:
    path = photo_gallery_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chart_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chart_uid TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT '',
            filename TEXT NOT NULL DEFAULT '',
            mime_type TEXT NOT NULL DEFAULT 'image/jpeg',
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            image_data BLOB NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chart_photos_chart_uid ON chart_photos(chart_uid)")
    return conn


def chart_uid_for_chart_id(chart_id: int | None) -> str | None:
    return get_chart_uid(chart_id)


def _resize_image(raw: bytes) -> tuple[bytes, str, int, int]:
    with Image.open(io.BytesIO(raw)) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        image.thumbnail((MAX_PHOTO_DIMENSION, MAX_PHOTO_DIMENSION), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=90, optimize=True, dpi=PHOTO_DPI)
        return output.getvalue(), "image/jpeg", int(image.width), int(image.height)


def _insert_photo(chart_uid: str, raw: bytes, *, source: str, filename: str) -> int:
    data, mime_type, width, height = _resize_image(raw)
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO chart_photos (chart_uid, source, filename, mime_type, width, height, image_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (chart_uid, source, filename, mime_type, width, height, data, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return int(cursor.lastrowid)


def add_photo_file(chart_uid: str, path: str | Path) -> int:
    file_path = Path(path)
    return _insert_photo(chart_uid, file_path.read_bytes(), source=str(file_path), filename=file_path.name)


def add_photo_url(chart_uid: str, url: str, *, timeout: int = 20) -> int:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    parsed = urlparse(url)
    filename = Path(parsed.path).name or "downloaded-photo"
    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip()
    if content_type and not content_type.startswith("image/"):
        guessed, _ = mimetypes.guess_type(filename)
        if not (guessed or "").startswith("image/"):
            raise ValueError(f"URL did not return an image: {content_type}")
    return _insert_photo(chart_uid, response.content, source=url, filename=filename)


def list_photos(chart_uid: str | None) -> list[dict[str, Any]]:
    if not chart_uid:
        return []
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, chart_uid, source, filename, mime_type, width, height, created_at
            FROM chart_photos
            WHERE chart_uid = ?
            ORDER BY created_at DESC, id DESC
            """,
            (chart_uid,),
        ).fetchall()
    return [dict(row) for row in rows]
