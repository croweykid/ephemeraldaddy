from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Iterable, TextIO

from ephemeraldaddy.core.db import parse_tags
from .models import BatchImportRow, BatchImportSeed


def parse_pasted_names(text: str) -> list[BatchImportSeed]:
    return [BatchImportSeed(line.strip()) for line in text.splitlines() if line.strip()]


def load_seeds(stream: TextIO) -> list[BatchImportSeed]:
    reader = csv.DictReader(stream)
    headers = {str(name).strip().lower(): name for name in (reader.fieldnames or [])}
    if "name" not in headers:
        raise ValueError("CSV must contain a name column")
    result = []
    for raw in reader:
        get = lambda key: str(raw.get(headers.get(key, ""), "") or "").strip()
        if get("name"):
            # Optional metadata and partial birth data must not suppress lookup.
            try:
                date.fromisoformat(get("birth_date"))
                restored = bool(get("birth_place"))
            except ValueError:
                restored = False
            result.append(BatchImportSeed(
                name=get("name"), alias=get("alias"), from_whence=get("from"),
                tags=tuple(parse_tags(get("tags"))), notes=get("notes"),
                birth_date=get("birth_date"), birth_time=get("birth_time"),
                birth_place=get("birth_place"), biography=get("bio"),
                sources=tuple(source.strip() for source in get("sources").split(";") if source.strip()),
                data_rating=get("data_rating"), restored=restored,
            ))
    return result


def export_failures(rows: Iterable[BatchImportRow], target: str | Path | TextIO) -> None:
    close = False
    if hasattr(target, "write"): stream = target
    else:
        stream = open(target, "w", newline="", encoding="utf-8"); close = True
    try:
        writer = csv.DictWriter(stream, fieldnames=("name", "alias", "from", "tags", "notes", "birth_date", "birth_time", "birth_place", "bio", "sources", "data_rating", "error"))
        writer.writeheader()
        for row in rows:
            if row.imported_uid is not None: continue
            if row.importable and not row.included and not row.save_error: continue
            writer.writerow({"name": row.name, "alias": row.alias, "from": row.from_whence, "tags": ", ".join(row.tags), "notes": row.notes, "birth_date": row.birth_date, "birth_time": row.birth_time or "unknown", "birth_place": row.birth_place, "bio": row.biography, "sources": "; ".join(row.sources), "data_rating": row.data_rating, "error": row.error_text})
    finally:
        if close: stream.close()
