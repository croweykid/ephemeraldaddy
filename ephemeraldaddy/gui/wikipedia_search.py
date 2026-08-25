from __future__ import annotations

import datetime
import json
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
WIKIPEDIA_USER_AGENT = "Mozilla/5.0 (compatible; EphemeralDaddy Wikipedia helper)"
WIKIPEDIA_HTTP_TIMEOUT_SECONDS = 10

WIKIDATA_BIRTH_DATE_PROPERTY = "P569"
WIKIDATA_BIRTH_PLACE_PROPERTY = "P19"
WIKIDATA_DAY_PRECISION = 11


def _wikipedia_http_get_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": WIKIPEDIA_USER_AGENT})
    with urlopen(request, timeout=WIKIPEDIA_HTTP_TIMEOUT_SECONDS) as response:
        payload = response.read()
    return json.loads(payload.decode("utf-8", errors="replace"))


def _wikipedia_api_query(params: Mapping[str, Any]) -> dict[str, Any]:
    """Call the shared Wikipedia endpoint with EphemeralDaddy's HTTP policy."""
    return _wikipedia_http_get_json(f"{WIKIPEDIA_API_URL}?{urlencode(params)}")


def _wikidata_api_query(params: Mapping[str, Any]) -> dict[str, Any]:
    """Call Wikidata with the same HTTP policy used for Wikipedia."""
    return _wikipedia_http_get_json(f"{WIKIDATA_API_URL}?{urlencode(params)}")


def _wikipedia_http_get_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": WIKIPEDIA_USER_AGENT})
    with urlopen(request, timeout=WIKIPEDIA_HTTP_TIMEOUT_SECONDS) as response:
        payload = response.read()
    return payload.decode("utf-8", errors="replace")


def _query_pages_for_title(title: str) -> list[dict[str, Any]]:
    url = (
        f"{WIKIPEDIA_API_URL}?action=query&format=json&redirects=1&"
        f"prop=pageprops&titles={quote(title)}"
    )
    data = _wikipedia_http_get_json(url)
    pages = data.get("query", {}).get("pages", {})
    if not isinstance(pages, dict):
        return []
    return [page for page in pages.values() if isinstance(page, dict)]


def _search_wikipedia_titles(search_query: str, limit: int = 10) -> list[str]:
    url = (
        f"{WIKIPEDIA_API_URL}?action=query&format=json&list=search&utf8=1&"
        f"srsearch={quote(search_query)}&srlimit={int(limit)}"
    )
    data = _wikipedia_http_get_json(url)
    rows = data.get("query", {}).get("search", [])
    if not isinstance(rows, list):
        return []
    titles: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title", "")).strip()
        if title and title not in titles:
            titles.append(title)
    return titles


def resolve_wikipedia_page_options(search_query: str) -> dict[str, Any]:
    pages = _query_pages_for_title(search_query)
    exact = next((page for page in pages if "missing" not in page), None)
    if exact is not None:
        title = str(exact.get("title", "")).strip()
        if title:
            pageprops = exact.get("pageprops", {})
            if isinstance(pageprops, dict) and "disambiguation" in pageprops:
                options = _search_wikipedia_titles(search_query, limit=15)
                options = [
                    option
                    for option in options
                    if "(disambiguation)" not in option.lower()
                ]
                if options:
                    return {"status": "multiple", "options": options}
            return {"status": "single", "title": title}

    options = _search_wikipedia_titles(search_query, limit=15)
    if not options:
        return {"status": "not_found"}
    if len(options) == 1:
        return {"status": "single", "title": options[0]}
    return {"status": "multiple", "options": options}


def _wikidata_entity_for_wikipedia_title(
    page_title: str,
) -> dict[str, Any] | None:
    data = _wikidata_api_query(
        {
            "action": "wbgetentities",
            "format": "json",
            "sites": "enwiki",
            "titles": page_title,
            "props": "claims",
        }
    )
    entities = data.get("entities", {})
    if not isinstance(entities, dict):
        return None
    return next(
        (
            entity
            for entity in entities.values()
            if isinstance(entity, dict) and "missing" not in entity
        ),
        None,
    )


def _ranked_wikidata_claims(
    entity: Mapping[str, Any],
    property_id: str,
) -> list[dict[str, Any]]:
    claims = entity.get("claims", {})
    if not isinstance(claims, dict):
        return []
    rows = claims.get(property_id, [])
    if not isinstance(rows, list):
        return []

    usable = [
        claim
        for claim in rows
        if isinstance(claim, dict) and claim.get("rank") != "deprecated"
    ]
    return sorted(
        usable,
        key=lambda claim: 0 if claim.get("rank") == "preferred" else 1,
    )


def _wikidata_birth_date(entity: Mapping[str, Any]) -> datetime.date | None:
    for claim in _ranked_wikidata_claims(entity, WIKIDATA_BIRTH_DATE_PROPERTY):
        mainsnak = claim.get("mainsnak", {})
        if not isinstance(mainsnak, dict) or mainsnak.get("snaktype") != "value":
            continue
        datavalue = mainsnak.get("datavalue", {})
        if not isinstance(datavalue, dict) or datavalue.get("type") != "time":
            continue
        value = datavalue.get("value", {})
        if not isinstance(value, dict):
            continue

        try:
            precision = int(value.get("precision", 0))
        except (TypeError, ValueError):
            continue
        if precision < WIKIDATA_DAY_PRECISION:
            continue

        time_text = str(value.get("time", "") or "")
        match = re.match(r"^\+(\d+)-(\d{2})-(\d{2})T", time_text)
        if match is None:
            continue
        year, month, day = (int(part) for part in match.groups())
        if not 1 <= year <= 9999:
            continue
        try:
            return datetime.date(year, month, day)
        except ValueError:
            continue
    return None


def _wikidata_birth_place_id(entity: Mapping[str, Any]) -> str:
    for claim in _ranked_wikidata_claims(entity, WIKIDATA_BIRTH_PLACE_PROPERTY):
        mainsnak = claim.get("mainsnak", {})
        if not isinstance(mainsnak, dict) or mainsnak.get("snaktype") != "value":
            continue
        datavalue = mainsnak.get("datavalue", {})
        if (
            not isinstance(datavalue, dict)
            or datavalue.get("type") != "wikibase-entityid"
        ):
            continue
        value = datavalue.get("value", {})
        if not isinstance(value, dict):
            continue
        entity_id = str(value.get("id", "") or "").strip()
        if entity_id:
            return entity_id
        numeric_id = value.get("numeric-id")
        if isinstance(numeric_id, int) and numeric_id > 0:
            return f"Q{numeric_id}"
    return ""


def _wikidata_place_name(entity_id: str) -> str:
    if not entity_id:
        return ""
    data = _wikidata_api_query(
        {
            "action": "wbgetentities",
            "format": "json",
            "ids": entity_id,
            "props": "labels|sitelinks",
            "languages": "en",
            "sitefilter": "enwiki",
        }
    )
    entities = data.get("entities", {})
    if not isinstance(entities, dict):
        return ""
    entity = entities.get(entity_id)
    if not isinstance(entity, dict) or "missing" in entity:
        return ""

    sitelinks = entity.get("sitelinks", {})
    if isinstance(sitelinks, dict):
        enwiki = sitelinks.get("enwiki", {})
        if isinstance(enwiki, dict):
            title = str(enwiki.get("title", "") or "").strip()
            if title:
                return title

    labels = entity.get("labels", {})
    if isinstance(labels, dict):
        english = labels.get("en", {})
        if isinstance(english, dict):
            return str(english.get("value", "") or "").strip()
    return ""


def parse_wikipedia_birth_data(page_title: str) -> dict[str, Any]:
    """Return structured birth data for a resolved English Wikipedia article.

    Wikipedia remains the page-resolution layer, while Wikidata supplies the
    machine-readable birth date/place. This intentionally avoids depending on
    Wikipedia's rendered HTML, parser implementation, or infobox CSS classes.
    """
    normalized_title = str(page_title or "").strip()
    if not normalized_title:
        raise ValueError("Wikipedia title cannot be empty")

    entity = _wikidata_entity_for_wikipedia_title(normalized_title)
    if entity is None:
        raise ValueError("No Wikidata entity is available for this Wikipedia page")

    birth_date = _wikidata_birth_date(entity)
    if birth_date is None:
        raise ValueError("No complete birthdate info is available")

    birth_place_id = _wikidata_birth_place_id(entity)
    birth_place = _wikidata_place_name(birth_place_id)

    page_slug = quote(normalized_title.replace(" ", "_"))
    page_url = f"https://en.wikipedia.org/wiki/{page_slug}"

    return {
        "name": normalized_title,
        "birth_year": birth_date.year,
        "birth_month": birth_date.month,
        "birth_day": birth_date.day,
        "birth_place": birth_place,
        "source_url": page_url,
    }
