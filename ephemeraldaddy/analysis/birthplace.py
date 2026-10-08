"""Locality names for display and analysis, independent of birth coordinates."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re
from typing import Mapping

from .city_lookup import normalize_city
from .country_lookup import normalize_country, resolve_country
from .us_state_lookup import US_STATE_ABBREVIATIONS


@dataclass(frozen=True)
class BirthplaceLocality:
    city: str = ""
    region: str = ""
    country: str = ""

    @property
    def label(self) -> str:
        parts = [self.city, self.region, self.country]
        return ", ".join(part for part in parts if part)

    @property
    def components(self) -> tuple[str | None, str | None, str | None]:
        return self.city or None, self.region or None, self.country or None


def _region(value: str, country: str) -> str:
    value = value.strip()
    meta = resolve_country(country)
    if meta and meta.get("alpha_2") == "US":
        return US_STATE_ABBREVIATIONS.get(value.upper(), value)
    return value


def locality_from_address(address: Mapping[str, object]) -> BirthplaceLocality:
    """Use administrative fields, never the feature name or display_name."""
    def text(key):
        return str(address.get(key) or "").strip()

    city = next((text(key) for key in (
        "city", "town", "village", "hamlet", "municipality",
    ) if text(key)), "")
    country_value = text("country_code") or text("country")
    country = normalize_country(country_value) or text("country")
    region = text("state") or text("province") or text("region")
    return BirthplaceLocality(
        normalize_city(city, country) or "", _region(region, country), country,
    )


_ADDRESS_TOKEN = re.compile(
    r"\b(post office|courthouse|city hall|town hall|government|hospital|"
    r"building|embassy|consulate|airport|university|museum|"
    r"street|avenue|road|boulevard|highway|lane|drive|"
    r"county|district|borough|suburb|neighbourhood|neighborhood|ward)\b",
    re.IGNORECASE,
)
_POSTCODE = re.compile(r"^(?:\d[\d\s-]*|[A-Z]\d[A-Z]\s?\d[A-Z]\d|[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})$", re.I)


def _address_token(token: str) -> bool:
    return bool(_ADDRESS_TOKEN.search(token) or _POSTCODE.fullmatch(token) or re.match(r"^\d+\s", token))


@lru_cache(maxsize=8192)
def locality_from_text(raw: str) -> BirthplaceLocality:
    """Read simple legacy locality labels without inventing cities from addresses.

    Ambiguous full addresses retain only a recognized region/country until their
    saved coordinates have supplied structured locality metadata.
    """
    parts = [part.strip() for part in str(raw or "").split(",") if part.strip()]
    if not parts:
        return BirthplaceLocality()
    # Some canonical country names contain commas (notably DR Congo).
    country_index = next((i for i in range(len(parts))
                          if resolve_country(", ".join(parts[i:]))), None)
    country_text = ", ".join(parts[country_index:]) if country_index is not None else ""
    if country_index is None:
        country_index = next((i for i in range(len(parts) - 1, -1, -1)
                              if resolve_country(parts[i])), None)
        country_text = parts[country_index] if country_index is not None else ""
    if country_index is None:
        # An unqualified old label could be either a city or a named building.
        # Retain the original privately and obtain locality from coordinates.
        return BirthplaceLocality()
    country = normalize_country(country_text) or ""
    local = parts[:country_index]
    meta = resolve_country(country)
    region = ""
    if meta and meta.get("alpha_2") == "US":
        states = {name.casefold(): name for name in US_STATE_ABBREVIATIONS.values()}
        for token in reversed(local):
            if token.upper() in US_STATE_ABBREVIATIONS or token.casefold() in states:
                region = _region(token, country)
                break
    # A simple city/region/country label is trustworthy; a street-address
    # hierarchy is not, even if its first token happens to look like a city.
    if (len(local) <= 2 and (not local or not _address_token(local[0]))
            and (len(local) < 2 or local[1].isdigit() or not _address_token(local[1]))):
        city = local[0] if local else ""
        if len(local) == 2:
            region = _region(local[1], country) if not local[1].isdigit() else ""
        if len(local) == 1 and city.casefold() == region.casefold():
            city = ""
        return BirthplaceLocality(normalize_city(city, country) or "", region, country)
    return BirthplaceLocality(region=region, country=country)


def birthplace_label(raw: str) -> str:
    return locality_from_text(raw).label


def gazetteer_label(raw: str) -> str:
    """The populated-place dataset supplies a city, even for unusual names."""
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if not parts:
        return ""
    country = normalize_country(parts[-1]) if len(parts) > 1 else ""
    region = parts[1] if len(parts) >= 3 and not parts[1].isdigit() else ""
    return BirthplaceLocality(
        normalize_city(parts[0], country) or "", _region(region, country or ""),
        country or "",
    ).label


def needs_locality_lookup(raw: str) -> bool:
    """Legacy strings have no provenance proving which tokens are localities.

    Even a short building/city/country label resembles city/region/country.
    Confirm each saved coordinate once; the repository skips cached sources.
    """
    return bool(str(raw or "").strip())


def chart_locality(chart) -> BirthplaceLocality:
    # A cached locality must never survive an in-memory edit to birth data.
    source = (str(getattr(chart, "birth_place", "") or ""),
              getattr(chart, "lat", None), getattr(chart, "lon", None))
    if getattr(chart, "_birthplace_locality_source", None) == source:
        return chart.birthplace_locality
    return locality_from_text(source[0])
