from __future__ import annotations

import datetime
import html
import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from ephemeraldaddy.analysis.us_state_lookup import normalize_us_state

ASTROTHEME_SEARCH_URL = "https://www.astrotheme.com/celebrities/recherche.php"
ASTROTHEME_USER_AGENT = "Mozilla/5.0 (compatible; EphemeralDaddy Astrotheme helper)"


def _astrotheme_http_get(url: str) -> str:
    request = Request(url, headers={"User-Agent": ASTROTHEME_USER_AGENT})
    with urlopen(request, timeout=20) as response:
        payload = response.read()
    return payload.decode("utf-8", errors="replace")


def _normalize_astrotheme_name(raw_name: str) -> str:
    value = html.unescape(raw_name or "")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^\w\s'-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip().lower()
    return value




def _decode_percent_sequences(value: str) -> str:
    if not value:
        return ""
    previous = value
    for _ in range(3):
        decoded = unquote(previous)
        if decoded == previous:
            break
        previous = decoded
    return previous


def _astrotheme_name_variants(raw_name: str) -> list[str]:
    base = html.unescape(raw_name or "").strip()
    decoded = _decode_percent_sequences(base)
    variants: list[str] = []

    def _push(candidate: str) -> None:
        cleaned = re.sub(r"\s+", " ", candidate).strip()
        if cleaned and cleaned not in variants:
            variants.append(cleaned)

    _push(base)
    _push(decoded)
    _push(decoded.replace("_", " "))
    normalized = _normalize_astrotheme_name(decoded)
    if normalized:
        _push(normalized)
    return variants


def _astrotheme_slug_variants(search_query: str) -> list[str]:
    slugs: list[str] = []

    def _push_slug(text: str, *, strip_accents: bool) -> None:
        working = html.unescape(text or "")
        working = _decode_percent_sequences(working)
        if strip_accents:
            working = unicodedata.normalize("NFKD", working)
            working = "".join(ch for ch in working if not unicodedata.combining(ch))
        else:
            working = unicodedata.normalize("NFKC", working)
        working = re.sub(r"[^\w\s'’-]", " ", working)
        working = re.sub(r"\s+", " ", working).strip(" _-")
        if not working:
            return
        slug = re.sub(r"\s+", "_", working)
        if slug and slug not in slugs:
            slugs.append(slug)

    for variant in _astrotheme_name_variants(search_query):
        _push_slug(variant, strip_accents=False)
        _push_slug(variant, strip_accents=True)

    return slugs


def _astrotheme_profile_slug_to_name(profile_url: str) -> str:
    slug = Path(urlparse(profile_url).path).name
    if slug.lower().endswith(".php"):
        slug = slug[:-4]
    return unquote(slug).replace("_", " ").strip()


def _astrotheme_is_profile_like_url(url: str) -> bool:
    parsed = urlparse(url)
    if "astrotheme.com" not in parsed.netloc.lower():
        return False
    if not parsed.path.startswith("/astrology/"):
        return False
    slug = Path(parsed.path).name
    return bool(slug and slug.lower() not in {"astrology", "index.php"})




_US_COUNTRY_TOKENS = {
    "us",
    "u.s.",
    "usa",
    "u.s.a.",
    "united states",
    "united states of america",
}

_US_NON_CITY_MARKERS = (
    "county",
    "avenue",
    "ave",
    "street",
    "st",
    "highway",
    "hwy",
    "road",
    "rd",
    "boulevard",
    "blvd",
    "drive",
    "dr",
    "lane",
    "ln",
    "parkway",
    "pkwy",
    "route",
    "post office",
    "zip",
)


def _normalize_astrotheme_birth_place(raw_place: str) -> str:
    cleaned = raw_place.replace(") (", ", ").replace("(", "").replace(")", "").strip()
    if not cleaned:
        return ""

    parts = [part.strip() for part in cleaned.split(",") if part.strip()]
    if len(parts) < 3:
        return cleaned

    country_token = parts[-1].lower()
    if country_token not in _US_COUNTRY_TOKENS:
        return cleaned

    state_index = None
    state_code = None
    for idx in range(len(parts) - 2, -1, -1):
        candidate_code = normalize_us_state(parts[idx])
        if candidate_code:
            state_index = idx
            state_code = candidate_code
            break

    if state_index is None or state_code is None:
        return cleaned

    city = None
    for idx in range(state_index - 1, -1, -1):
        token = parts[idx]
        lowered = token.lower()
        if any(ch.isdigit() for ch in token):
            continue
        if any(marker in lowered for marker in _US_NON_CITY_MARKERS):
            continue
        city = token
        break

    if not city:
        return cleaned

    return f"{city}, {state_code}, US"

def _astrotheme_profile_has_fiche_table(profile_url: str) -> bool:
    try:
        html_text = _astrotheme_http_get(profile_url)
    except Exception:
        return False
    return bool(
        re.search(
            r'<table[^>]*class=["\'][^"\']*fiche[^"\']*["\']',
            html_text,
            flags=re.IGNORECASE,
        )
    )


def _strip_html_text(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", fragment, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_profile_candidates_from_html(html_text: str) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    seen_urls: set[str] = set()
    for href, anchor_text in re.findall(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        href = href.strip()
        if href.startswith("/"):
            href = f"https://www.astrotheme.com{href}"
        if not _astrotheme_is_profile_like_url(href):
            continue
        if href in seen_urls:
            continue
        seen_urls.add(href)
        anchor_name = _strip_html_text(anchor_text) or _astrotheme_profile_slug_to_name(href)
        candidates.append((href, anchor_name))
    return candidates


def _candidate_score(query: str, candidate_name: str, url: str) -> int:
    query_norm = _normalize_astrotheme_name(query)
    candidate_norm = _normalize_astrotheme_name(candidate_name)
    slug_norm = _normalize_astrotheme_name(_astrotheme_profile_slug_to_name(url))

    if not query_norm:
        return -1

    query_tokens = set(query_norm.split())
    candidate_tokens = set(candidate_norm.split())
    slug_tokens = set(slug_norm.split())

    def _score_name(name_norm: str, tokens: set[str]) -> int:
        if not name_norm:
            return 0
        if name_norm == query_norm:
            return 10_000
        if tokens == query_tokens and tokens:
            return 9_000
        overlap = len(query_tokens & tokens)
        if query_tokens and query_tokens.issubset(tokens):
            return 8_000 + overlap * 200 - max(0, len(tokens) - len(query_tokens)) * 120
        if name_norm.startswith(query_norm):
            return 7_000 + overlap * 100
        if query_norm.startswith(name_norm):
            return 6_800 + overlap * 100
        if not query_tokens:
            return 0
        token_ratio = overlap / len(query_tokens)
        return int(token_ratio * 5_000)

    return max(_score_name(candidate_norm, candidate_tokens), _score_name(slug_norm, slug_tokens))


def _collect_astrotheme_search_candidates(search_query: str) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    for query_variant in _astrotheme_name_variants(search_query):
        for param_name in ("nom", "q"):
            search_url = f"{ASTROTHEME_SEARCH_URL}?{param_name}={quote_plus(query_variant)}"
            try:
                html_text = _astrotheme_http_get(search_url)
            except Exception:
                continue
            candidates.extend(_extract_profile_candidates_from_html(html_text))
    return candidates


def _collect_web_search_candidates(search_query: str) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    for query_variant in _astrotheme_name_variants(search_query):
        q = quote_plus(f'{query_variant} site:astrotheme.com/astrology')
        search_urls = [
            f"https://duckduckgo.com/html/?q={q}",
            f"https://www.bing.com/search?q={q}",
        ]
        for url in search_urls:
            try:
                html_text = _astrotheme_http_get(url)
            except Exception:
                continue
            candidates.extend(_extract_profile_candidates_from_html(html_text))
    return candidates


def search_astrotheme_profile_url(search_query: str) -> str | None:
    for query_slug in _astrotheme_slug_variants(search_query):
        encoded_slug = quote_plus(query_slug).replace("+", "_")
        guessed_url = f"https://www.astrotheme.com/astrology/{encoded_slug}"
        if _astrotheme_profile_has_fiche_table(guessed_url):
            return guessed_url

    all_candidates: list[tuple[str, str]] = []
    all_candidates.extend(_collect_astrotheme_search_candidates(search_query))
    all_candidates.extend(_collect_web_search_candidates(search_query))

    best_url: str | None = None
    best_score = -1
    seen: set[str] = set()
    for url, name in all_candidates:
        if url in seen:
            continue
        seen.add(url)
        score = _candidate_score(search_query, name, url)
        if score > best_score:
            best_score = score
            best_url = url

    if best_url and best_score >= 4_000:
        return best_url
    return None


def parse_astrotheme_profile(profile_url: str) -> dict[str, Any]:
    html_text = _astrotheme_http_get(profile_url)
    table_match = re.search(
        r'<table[^>]*class=["\'][^"\']*fiche[^"\']*["\'][^>]*>(.*?)</table>',
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if table_match is None:
        raise ValueError("Could not find Astrotheme profile data table.")

    table_html = table_match.group(0)
    born_match = re.search(
        r">\s*Born:\s*</td>\s*<td[^>]*>(.*?)</td>",
        table_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    place_match = re.search(
        r">\s*In:\s*</td>\s*<td[^>]*>(.*?)</td>",
        table_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    rodden_match = re.search(
        r">\s*Rodden\s*Rating\s*:?\s*</td>\s*<td[^>]*>(.*?)</td>",
        table_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if born_match is None:
        raise ValueError("Could not parse born date from Astrotheme profile.")

    born_text = _strip_html_text(born_match.group(1))
    place_text = _strip_html_text(place_match.group(1)) if place_match else ""
    rodden_text = _strip_html_text(rodden_match.group(1)) if rodden_match else ""

    parsed_url = urlparse(profile_url)
    slug = Path(parsed_url.path).name
    if slug.lower().endswith(".php"):
        slug = slug[:-4]
    name = unquote(slug).replace("_", " ").strip() or "Unknown"

    date_match = re.search(
        r"\b([A-Za-z]+)\s+(\d{1,2})\s*,\s*(\d{4})\b",
        born_text,
        flags=re.IGNORECASE,
    )
    if date_match is None:
        raise ValueError(f"Could not parse Astrotheme birth date: {born_text}")
    month_name, day_raw, year_raw = date_match.groups()
    month_number = datetime.datetime.strptime(month_name.title(), "%B").month
    day_number = int(day_raw)
    year_number = int(year_raw)

    time_unknown = bool(re.search(r"time\s+unknown", born_text, flags=re.IGNORECASE))
    hour = 12
    minute = 0
    if not time_unknown:
        time_match = re.search(
            r"\b(\d{1,2})[:h](\d{2})(?:\s*(AM|PM))?\b",
            born_text,
            flags=re.IGNORECASE,
        )
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            am_pm = (time_match.group(3) or "").upper()
            if am_pm == "PM" and hour != 12:
                hour += 12
            if am_pm == "AM" and hour == 12:
                hour = 0
        else:
            time_unknown = True

    cleaned_place = _normalize_astrotheme_birth_place(place_text)
    if not cleaned_place:
        raise ValueError("Could not parse Astrotheme birthplace.")

    data_rating = "blank"
    rodden_upper = rodden_text.upper()
    for candidate in ("AA", "DD", "XX", "A", "B", "C", "X"):
        if re.search(rf"\b{re.escape(candidate)}\b", rodden_upper):
            data_rating = candidate
            break

    return {
        "name": name,
        "birth_year": year_number,
        "birth_month": month_number,
        "birth_day": day_number,
        "birth_hour": hour,
        "birth_minute": minute,
        "time_unknown": time_unknown,
        "birth_place": cleaned_place,
        "data_rating": data_rating,
        "profile_url": profile_url,
    }
