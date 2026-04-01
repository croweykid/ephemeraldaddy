from ephemeraldaddy.analysis.country_lookup import normalize_country, resolve_country

CITY_DISPLAY_OVERRIDES = {
    "greater london": "London",
}

_CITY_PREFIX_BLOCKLIST = (
    "united states post office",
)


def normalize_city(raw_city: str, raw_country: str | None = None) -> str | None:
    city = (raw_city or "").strip()
    if not city:
        return None

    city_key = city.lower()
    if city_key in CITY_DISPLAY_OVERRIDES:
        city = CITY_DISPLAY_OVERRIDES[city_key]
        city_key = city.lower()

    if any(city_key.startswith(prefix) for prefix in _CITY_PREFIX_BLOCKLIST):
        return None

    country_label = normalize_country(raw_country or "") if raw_country else None
    if country_label and city_key == country_label.lower():
        return None

    if resolve_country(city) is not None:
        return None

    return city

