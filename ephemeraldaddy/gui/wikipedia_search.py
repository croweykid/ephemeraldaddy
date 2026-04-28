from __future__ import annotations

import datetime
import json
import re
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_USER_AGENT = "Mozilla/5.0 (compatible; EphemeralDaddy Wikipedia helper)"
WIKIPEDIA_HTTP_TIMEOUT_SECONDS = 10


def _wikipedia_http_get_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": WIKIPEDIA_USER_AGENT})
    with urlopen(request, timeout=WIKIPEDIA_HTTP_TIMEOUT_SECONDS) as response:
        payload = response.read()
    return json.loads(payload.decode("utf-8", errors="replace"))


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

def _fetch_wikipedia_intro_text(title: str) -> str:
    url = (
        f"{WIKIPEDIA_API_URL}?action=query&format=json&redirects=1&prop=extracts&"
        f"exintro=1&explaintext=1&titles={quote(title)}"
    )
    data = _wikipedia_http_get_json(url)
    pages = data.get("query", {}).get("pages", {})
    if not isinstance(pages, dict):
        return ""
    for page in pages.values():
        if not isinstance(page, dict):
            continue
        extract = str(page.get("extract", "") or "").strip()
        if extract:
            return extract.split("\n", 1)[0].strip()
    return ""


def _fetch_wikipedia_page_html(title: str) -> str:
    url = f"{WIKIPEDIA_API_URL}?action=parse&format=json&prop=text&page={quote(title)}"
    data = _wikipedia_http_get_json(url)
    parse_node = data.get("parse", {})
    if not isinstance(parse_node, dict):
        return ""
    text_node = parse_node.get("text", {})
    if not isinstance(text_node, dict):
        return ""
    return str(text_node.get("*", "") or "")


def _strip_html(fragment: str) -> str:
    cleaned = re.sub(
        r"<sup[^>]*class=[\"'][^\"']*reference[^\"']*[\"'][^>]*>.*?</sup>",
        " ",
        fragment,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+\[\d+\]\s*", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def resolve_wikipedia_page_options(search_query: str) -> dict[str, Any]:
    pages = _query_pages_for_title(search_query)
    exact = next((page for page in pages if "missing" not in page), None)
    if exact is not None:
        title = str(exact.get("title", "")).strip()
        if title:
            pageprops = exact.get("pageprops", {})
            if isinstance(pageprops, dict) and "disambiguation" in pageprops:
                options = _search_wikipedia_titles(search_query, limit=15)
                options = [option for option in options if "(disambiguation)" not in option.lower()]
                if options:
                    return {"status": "multiple", "options": options}
            return {"status": "single", "title": title}

    options = _search_wikipedia_titles(search_query, limit=15)
    if not options:
        return {"status": "not_found"}
    if len(options) == 1:
        return {"status": "single", "title": options[0]}
    return {"status": "multiple", "options": options}


def parse_wikipedia_birth_data(page_title: str) -> dict[str, Any]:
    page_slug = quote(page_title.replace(" ", "_"))
    page_url = f"https://en.wikipedia.org/wiki/{page_slug}"
    html_text = _wikipedia_http_get_text(page_url)

    bday_match = re.search(
        r'<span[^>]*class=["\'][^"\']*\bbday\b[^"\']*["\'][^>]*>(\d{4})-(\d{2})-(\d{2})</span>',
        html_text,
        flags=re.IGNORECASE,
    )
    if bday_match is None:
        raise ValueError("No birthdate info is available")
    year = int(bday_match.group(1))
    month = int(bday_match.group(2))
    day = int(bday_match.group(3))
    datetime.date(year, month, day)

    birthplace_match = re.search(
        r'<div[^>]*class=["\'][^"\']*\bbirthplace\b[^"\']*["\'][^>]*>(.*?)</div>',
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    birth_place = ""
    if birthplace_match is not None:
        raw_place = birthplace_match.group(1)
        birth_place = re.sub(r"<[^>]+>", " ", raw_place)
        birth_place = re.sub(r"\s+", " ", birth_place).strip(" ,")


    biography = ""
    content_match = re.search(
        r'<div[^>]*class=["\'][^"\']*\bmw-parser-output\b[^"\']*["\'][^>]*>(.*?)</div>',
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    content_html = content_match.group(1) if content_match else html_text
    for paragraph_html in re.findall(
        r"<p[^>]*>(.*?)</p>",
        content_html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        cleaned = re.sub(
            r"<sup[^>]*class=[\"'][^\"']*reference[^\"']*[\"'][^>]*>.*?</sup>",
            " ",
            paragraph_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            biography = cleaned
            break

    return {
        "name": page_title,
        "birth_year": year,
        "birth_month": month,
        "birth_day": day,
        "birth_place": birth_place,
        "biography": biography,
        "source_url": page_url,
    }
