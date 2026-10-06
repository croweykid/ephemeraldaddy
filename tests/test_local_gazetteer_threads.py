from concurrent.futures import ThreadPoolExecutor
import sqlite3
import pytest

from ephemeraldaddy.io.local_gazetteer import LocalGazetteer


@pytest.mark.parametrize("fts", [False, True])
def test_gazetteer_connection_supports_background_validation(tmp_path, fts):
    path = tmp_path / 'places.db'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE places(id INTEGER PRIMARY KEY, label TEXT, latitude REAL, longitude REAL, population INTEGER, search_text TEXT)')
        conn.execute("INSERT INTO places VALUES (1, 'Here', 1, 2, 100, 'here')")
        if fts:
            conn.execute("CREATE VIRTUAL TABLE places_fts USING fts5(label, search_text)")
            conn.execute("INSERT INTO places_fts(rowid, label, search_text) VALUES (1, 'Here', 'here')")
    gazetteer = LocalGazetteer(path)
    try:
        assert gazetteer.geocode('Here').latitude == 1
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(gazetteer.geocode, ['Here'] * 8))
        assert all(result.longitude == 2 for result in results)
    finally:
        gazetteer.close()
