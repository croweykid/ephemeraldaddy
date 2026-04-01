import json
import unicodedata
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "compiled" / "country_data.json"

COUNTRY_DISPLAY_OVERRIDES = {
    "NZ": "New Zealand",
    "PS": "Palestine",
    "RU": "Russia",
    "TR": "Turkey",
    "VA": "Vatican City",
}

def normalize(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))

with DATA_PATH.open("r", encoding="utf-8") as f:
    _DATA = json.load(f)

ISO_META = _DATA["iso_meta"]
COUNTRY_ALIASES = _DATA["aliases"]


def resolve_country(input_name: str):
    candidates = [input_name]
    if "/" in input_name:
        candidates.extend(part.strip() for part in input_name.split("/") if part.strip())

    iso2 = None
    for candidate in candidates:
        key = normalize(candidate)
        iso2 = COUNTRY_ALIASES.get(key)
        if iso2:
            break

    if not iso2:
        return None

    return ISO_META.get(iso2)


def normalize_country(raw_name: str) -> str | None:
    country = resolve_country(raw_name)
    if not country:
        return None
    iso2 = str(country.get("alpha_2", "")).strip().upper()
    if iso2 in COUNTRY_DISPLAY_OVERRIDES:
        return COUNTRY_DISPLAY_OVERRIDES[iso2]
    display_name = country.get("common_name") or country.get("name")
    return str(display_name).strip() if display_name else None
