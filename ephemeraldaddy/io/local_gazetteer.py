import os
import re
import sqlite3
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from ephemeraldaddy.io.gazetteer_builder import build_db


def _default_gazetteer_path() -> Path:
    data_root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return data_root / "ephemeraldaddy" / "gazetteer.sqlite"


def gazetteer_path() -> Path:
    override = os.environ.get("EPHEMERALDADDY_GAZETTEER_DB")
    if override:
        return Path(override).expanduser()
    return _default_gazetteer_path()


@dataclass(frozen=True)
class GazetteerResult:
    label: str
    latitude: float
    longitude: float
    population: int


class LocalGazetteer:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self._conn.close()

    def _has_fts_table(self) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'places_fts'"
        ).fetchone()
        return row is not None

    @staticmethod
    def _fts_query(tokens: List[str]) -> str:
        return " ".join(f'"{token}"*' for token in tokens)

    def search(self, query: str, limit: int = 5) -> List[GazetteerResult]:
        tokens = _tokenize(query)
        if not tokens:
            return []

        if self._has_fts_table():
            fts_query = self._fts_query(tokens)
            rows = self._conn.execute(
                """
                SELECT p.label, p.latitude, p.longitude, p.population
                FROM places_fts f
                JOIN places p ON p.id = f.rowid
                WHERE places_fts MATCH ?
                ORDER BY p.population DESC, p.label ASC
                LIMIT ?
                """,
                (fts_query, limit),
            ).fetchall()
        else:
            conditions = " AND ".join(["search_text LIKE ?" for _ in tokens])
            params = [f"%{token}%" for token in tokens]
            sql = (
                "SELECT label, latitude, longitude, population "
                "FROM places "
                f"WHERE {conditions} "
                "ORDER BY population DESC, label ASC "
                "LIMIT ?"
            )
            params.append(limit)
            rows = self._conn.execute(sql, params).fetchall()

        return [
            GazetteerResult(
                label=row["label"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                population=row["population"],
            )
            for row in rows
        ]

    def geocode(self, query: str) -> Optional[GazetteerResult]:
        results = self.search(query, limit=1)
        return results[0] if results else None


def _tokenize(query: str) -> List[str]:
    return re.findall(r"[\w]+", query.lower())


_LOCAL_GAZETTEER: Optional[LocalGazetteer] = None
_LOCAL_GAZETTEER_ERROR: Optional[Exception] = None
_LOCAL_GAZETTEER_ERROR_AT: Optional[float] = None
_GEONAMES_URL_DEFAULT = "https://download.geonames.org/export/dump/cities1500.zip"
_GEONAMES_FILENAME_DEFAULT = "cities1500.txt"
_LOCAL_GAZETTEER_RETRY_SECONDS = 30.0


def _auto_download_enabled() -> bool:
    return os.environ.get("EPHEMERALDADDY_GAZETTEER_AUTO", "1").lower() not in {
        "0",
        "false",
        "no",
    }


def _geonames_url() -> str:
    return os.environ.get("EPHEMERALDADDY_GAZETTEER_URL", _GEONAMES_URL_DEFAULT)


def _geonames_filename() -> str:
    return os.environ.get(
        "EPHEMERALDADDY_GAZETTEER_FILENAME", _GEONAMES_FILENAME_DEFAULT
    )


def _gazetteer_retry_seconds() -> float:
    raw = os.environ.get("EPHEMERALDADDY_GAZETTEER_RETRY_SECONDS")
    if raw is None:
        return _LOCAL_GAZETTEER_RETRY_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return _LOCAL_GAZETTEER_RETRY_SECONDS
    return max(0.0, value)


def _download_and_build(path: Path) -> None:
    url = _geonames_url()
    filename = _geonames_filename()

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "geonames.zip"
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            if filename not in zf.namelist():
                raise FileNotFoundError(
                    f"{filename} not found in downloaded archive from {url}"
                )
            extracted_path = Path(tmpdir) / filename
            with zf.open(filename) as source, extracted_path.open("wb") as target:
                target.write(source.read())
        build_db(extracted_path, path)

def _bundled_geonames_path() -> Optional[Path]:
    repo_root = Path(__file__).resolve().parents[2]
    bundled = repo_root / "tools" / "cities15000.txt"
    return bundled if bundled.exists() else None

def get_local_gazetteer() -> Optional[LocalGazetteer]:
    global _LOCAL_GAZETTEER
    global _LOCAL_GAZETTEER_ERROR
    global _LOCAL_GAZETTEER_ERROR_AT

    if _LOCAL_GAZETTEER is not None:
        return _LOCAL_GAZETTEER
    if _LOCAL_GAZETTEER_ERROR is not None:
        now = time.monotonic()
        retry_after = _gazetteer_retry_seconds()
        if _LOCAL_GAZETTEER_ERROR_AT is not None and (now - _LOCAL_GAZETTEER_ERROR_AT) < retry_after:
            return None

    path = gazetteer_path()
    if not path.exists():
        bundled_path = _bundled_geonames_path()
        if bundled_path is not None:
            try:
                build_db(bundled_path, path)
            except Exception as exc:
                _LOCAL_GAZETTEER_ERROR = exc
                _LOCAL_GAZETTEER_ERROR_AT = time.monotonic()
                return None
        elif _auto_download_enabled():
            try:
                _download_and_build(path)
            except Exception as exc:
                _LOCAL_GAZETTEER_ERROR = exc
                _LOCAL_GAZETTEER_ERROR_AT = time.monotonic()
                return None

    try:
        _LOCAL_GAZETTEER = LocalGazetteer(path)
    except Exception as exc:
        _LOCAL_GAZETTEER_ERROR = exc
        _LOCAL_GAZETTEER_ERROR_AT = time.monotonic()
        return None

    _LOCAL_GAZETTEER_ERROR = None
    _LOCAL_GAZETTEER_ERROR_AT = None
    return _LOCAL_GAZETTEER


def local_search_locations(query: str, limit: int = 5) -> List[Tuple[str, float, float]]:
    gazetteer = get_local_gazetteer()
    if not gazetteer:
        return []

    results = gazetteer.search(query, limit=limit)
    return [(r.label, r.latitude, r.longitude) for r in results]


def local_geocode_location(query: str) -> Optional[Tuple[float, float, str]]:
    gazetteer = get_local_gazetteer()
    if not gazetteer:
        return None

    result = gazetteer.geocode(query)
    if not result:
        return None

    return result.latitude, result.longitude, result.label


def gazetteer_env_summary() -> str:
    path = gazetteer_path()
    return (
        "Local gazetteer enabled" if path.exists() else "Local gazetteer not found"
    )


def resolve_search_sources() -> Iterable[str]:
    sources = []
    if get_local_gazetteer() is not None:
        sources.append("local")
    if os.environ.get("EPHEMERALDADDY_GAZETTEER_ONLY", "").lower() in {"1", "true", "yes"}:
        return sources
    sources.append("online")
    return sources
