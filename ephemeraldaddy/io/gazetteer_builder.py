import csv
import sqlite3
from pathlib import Path


def build_db(input_path: Path, output_path: Path, min_population: int = 0) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    conn = sqlite3.connect(str(output_path))
    conn.execute(
        """
        CREATE TABLE places (
            id INTEGER PRIMARY KEY,
            label TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            population INTEGER NOT NULL,
            search_text TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE places_fts USING fts5(
            label,
            search_text,
            tokenize='unicode61 remove_diacritics 2'
        );
        """
    )
    conn.execute("CREATE INDEX idx_places_search ON places(search_text);")
    conn.execute("CREATE INDEX idx_places_population ON places(population);")

    with input_path.open("r", encoding="utf-8", errors="ignore") as handle:
        reader = csv.reader(handle, delimiter="\t")
        rows = 0
        for row in reader:
            if len(row) < 15:
                continue
            population = int(row[14] or 0)
            if population < min_population:
                continue

            name = row[1]
            asciiname = row[2]
            alternatenames = row[3]
            latitude = float(row[4])
            longitude = float(row[5])
            country_code = row[8]
            admin1 = row[10]
            label_parts = [name]
            if admin1:
                label_parts.append(admin1)
            if country_code:
                label_parts.append(country_code)
            label = ", ".join(label_parts)
            search_text = " ".join(
                {
                    name.lower(),
                    asciiname.lower(),
                    alternatenames.lower(),
                    country_code.lower(),
                    admin1.lower(),
                }
            )
            conn.execute(
                "INSERT INTO places (label, latitude, longitude, population, search_text) VALUES (?, ?, ?, ?, ?)",
                (label, latitude, longitude, population, search_text),
            )
            conn.execute(
                "INSERT INTO places_fts(rowid, label, search_text) VALUES (last_insert_rowid(), ?, ?)",
                (label, search_text),
            )
            rows += 1

    conn.commit()
    conn.close()
    return rows
