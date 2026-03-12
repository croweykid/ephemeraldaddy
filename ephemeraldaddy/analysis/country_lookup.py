import json
import unicodedata
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "compiled" / "country_data.json"

def normalize(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))

with DATA_PATH.open("r", encoding="utf-8") as f:
    _DATA = json.load(f)

ISO_META = _DATA["iso_meta"]
COUNTRY_ALIASES = _DATA["aliases"]


def resolve_country(input_name: str):
    key = normalize(input_name)
    iso2 = COUNTRY_ALIASES.get(key)

    if not iso2:
        return None

    return ISO_META.get(iso2)


def normalize_country(raw_name: str) -> str | None:
    country = resolve_country(raw_name)
    if not country:
        return None
    display_name = country.get("name")
    return str(display_name).strip() if display_name else None