from __future__ import annotations

import datetime
import html
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


def _wikipedia_page_wikitext(page_title: str) -> str:
    """Fetch canonical source wikitext without depending on rendered article HTML."""
    data = _wikipedia_api_query(
        {
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "redirects": 1,
            "titles": page_title,
        }
    )
    pages = data.get("query", {}).get("pages", [])
    if not isinstance(pages, list) or not pages:
        return ""
    page = pages[0]
    if not isinstance(page, dict) or page.get("missing") is True:
        return ""
    revisions = page.get("revisions", [])
    if not isinstance(revisions, list) or not revisions:
        return ""
    revision = revisions[0]
    if not isinstance(revision, dict):
        return ""
    slots = revision.get("slots", {})
    if isinstance(slots, dict):
        main = slots.get("main", {})
        if isinstance(main, dict):
            content = main.get("content")
            if content is None:
                content = main.get("*")
            if isinstance(content, str):
                return content
    legacy_content = revision.get("*")
    return legacy_content if isinstance(legacy_content, str) else ""


def _extract_infobox_template(wikitext: str) -> str:
    """Return the first balanced {{Infobox ...}} template from source wikitext."""
    match = re.search(r"\{\{\s*infobox\b", wikitext, flags=re.IGNORECASE)
    if match is None:
        return ""

    start = match.start()
    depth = 0
    i = start
    while i < len(wikitext) - 1:
        pair = wikitext[i : i + 2]
        if pair == "{{":
            depth += 1
            i += 2
            continue
        if pair == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return wikitext[start:i]
            continue
        i += 1
    return ""


def _split_infobox_fields(template: str) -> list[str]:
    """Split an infobox on top-level pipes, preserving nested templates/links."""
    if not template.startswith("{{") or not template.endswith("}}"):
        return []

    fields: list[str] = []
    current: list[str] = []
    template_depth = 1
    link_depth = 0
    i = 2
    end = len(template) - 2

    while i < end:
        pair = template[i : i + 2]
        if pair == "{{":
            template_depth += 1
            current.append(pair)
            i += 2
            continue
        if pair == "}}":
            template_depth -= 1
            current.append(pair)
            i += 2
            continue
        if pair == "[[":
            link_depth += 1
            current.append(pair)
            i += 2
            continue
        if pair == "]]":
            link_depth = max(0, link_depth - 1)
            current.append(pair)
            i += 2
            continue
        if template[i] == "|" and template_depth == 1 and link_depth == 0:
            fields.append("".join(current))
            current = []
            i += 1
            continue
        current.append(template[i])
        i += 1

    fields.append("".join(current))
    return fields


def _wikipedia_infobox_parameters(wikitext: str) -> dict[str, str]:
    template = _extract_infobox_template(wikitext)
    if not template:
        return {}

    fields = _split_infobox_fields(template)
    if len(fields) < 2:
        return {}

    params: dict[str, str] = {}
    for field in fields[1:]:
        key, separator, value = field.partition("=")
        if not separator:
            continue
        normalized_key = re.sub(r"[\s-]+", "_", key.strip().lower())
        if normalized_key:
            params[normalized_key] = value.strip()
    return params


def _valid_calendar_date(year: int, month: int, day: int) -> datetime.date | None:
    if not 1 <= year <= 9999:
        return None
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


def _wikipedia_birth_date(value: str) -> datetime.date | None:
    """Parse common Wikipedia birth-date templates plus plain full dates."""
    value = str(value or "").strip()
    if not value:
        return None

    template_match = re.search(
        r"\{\{\s*([^|{}]+)\|([^{}]*)\}\}",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if template_match is not None:
        template_name = re.sub(
            r"[\s_-]+", " ", template_match.group(1).strip().lower()
        )
        if (
            "birth date" in template_name
            or template_name in {"bda", "dob", "date of birth"}
        ):
            tokens = [
                token.strip()
                for token in template_match.group(2).split("|")
                if token.strip()
            ]
            named: dict[str, str] = {}
            positional: list[str] = []
            for token in tokens:
                key, separator, token_value = token.partition("=")
                if separator:
                    named[key.strip().lower()] = token_value.strip()
                else:
                    positional.append(token)

            if {"year", "month", "day"} <= named.keys():
                try:
                    parsed = _valid_calendar_date(
                        int(named["year"]),
                        int(named["month"]),
                        int(named["day"]),
                    )
                except ValueError:
                    parsed = None
                if parsed is not None:
                    return parsed

            if len(positional) >= 3:
                try:
                    parsed = _valid_calendar_date(
                        int(positional[0]),
                        int(positional[1]),
                        int(positional[2]),
                    )
                except ValueError:
                    parsed = None
                if parsed is not None:
                    return parsed

    iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", value)
    if iso_match is not None:
        parsed = _valid_calendar_date(*(int(part) for part in iso_match.groups()))
        if parsed is not None:
            return parsed

    plain = _wikitext_to_plain_text(value)
    plain = re.sub(r"\([^)]*\bage\b[^)]*\)", "", plain, flags=re.IGNORECASE).strip()
    for date_format in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.datetime.strptime(plain, date_format).date()
        except ValueError:
            continue
    return None


def _wikitext_to_plain_text(value: str) -> str:
    """Reduce simple infobox wikitext to useful plain text for geocoding."""
    text = str(value or "")
    if not text:
        return ""

    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(
        r"<ref\b[^>]*>.*?</ref\s*>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r"<ref\b[^>]*/\s*>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", ", ", text, flags=re.IGNORECASE)

    def replace_link(match: re.Match[str]) -> str:
        return match.group(1).split("#", 1)[0].strip()

    text = re.sub(r"\[\[([^|\]]+)(?:\|[^\]]*)?\]\]", replace_link, text)

    def replace_simple_template(match: re.Match[str]) -> str:
        body = match.group(1).strip()
        bits = [bit.strip() for bit in body.split("|")]
        name = re.sub(r"[\s_-]+", " ", bits[0].lower()) if bits else ""
        if name in {"usa", "us", "united states"}:
            return "United States"
        if name in {"flag", "flagicon", "flag country"} and len(bits) > 1:
            return bits[1]
        return " "

    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"\{\{([^{}]*)\}\}", replace_simple_template, text)

    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("'''", "").replace("''", "")
    text = html.unescape(text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"(?:,\s*){2,}", ", ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,")
    return text


def _wikipedia_infobox_birth_data(
    wikitext: str,
) -> tuple[datetime.date | None, str]:
    params = _wikipedia_infobox_parameters(wikitext)
    birth_date_value = params.get("birth_date") or params.get("date_of_birth") or ""
    birth_place_value = (
        params.get("birth_place")
        or params.get("birthplace")
        or params.get("place_of_birth")
        or ""
    )
    return (
        _wikipedia_birth_date(birth_date_value),
        _wikitext_to_plain_text(birth_place_value),
    )


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
        parsed = _valid_calendar_date(year, month, day)
        if parsed is not None:
            return parsed
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
    """Return birth data without depending on Wikipedia's rendered HTML.

    The canonical Wikipedia infobox source is preferred because it matches the
    article the user sees and often contains more specific birthplace text.
    Wikidata is a structured fallback for fields the infobox cannot supply.
    """
    normalized_title = str(page_title or "").strip()
    if not normalized_title:
        raise ValueError("Wikipedia title cannot be empty")

    birth_date: datetime.date | None = None
    birth_place = ""

    try:
        wikitext = _wikipedia_page_wikitext(normalized_title)
        if wikitext:
            birth_date, birth_place = _wikipedia_infobox_birth_data(wikitext)
    except Exception:
        # Wikipedia source retrieval/parsing is deliberately non-fatal because
        # Wikidata remains an independent structured fallback.
        pass

    if birth_date is None or not birth_place:
        try:
            entity = _wikidata_entity_for_wikipedia_title(normalized_title)
        except Exception:
            entity = None

        if entity is not None:
            if birth_date is None:
                birth_date = _wikidata_birth_date(entity)
            if not birth_place:
                try:
                    birth_place = _wikidata_place_name(
                        _wikidata_birth_place_id(entity)
                    )
                except Exception:
                    birth_place = ""

    if birth_date is None:
        raise ValueError("No complete birthdate info is available")

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
