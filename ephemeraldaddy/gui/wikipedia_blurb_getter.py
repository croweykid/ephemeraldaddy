from __future__ import annotations

import datetime
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlparse

from ephemeraldaddy.gui.wikipedia_search import (
    _wikipedia_api_query,
    resolve_wikipedia_page_options,
)


class WikipediaError(RuntimeError):
    """Base exception for Wikipedia retrieval errors."""


class WikipediaPageNotFound(WikipediaError):
    pass


class WikipediaDisambiguationError(WikipediaError):
    pass


class WikipediaAmbiguousPageError(WikipediaError):
    """Raised when a name search needs a person to choose among candidates."""

    def __init__(self, chart_name: str, options: list[str]) -> None:
        self.options = options
        super().__init__(
            f"Wikipedia found multiple pages for {chart_name!r}; choose one: "
            + ", ".join(options)
        )


@dataclass(frozen=True)
class WikipediaBlurb:
    title: str
    paragraphs: list[str]
    page_url: str
    page_id: int

    @property
    def text(self) -> str:
        return "\n\n".join(self.paragraphs)


def unique_title_matching_birth_date(
    candidates: list[tuple[str, datetime.date | None]],
    chart_birth_date: datetime.date | None,
) -> str | None:
    """Return a candidate only when exactly one birthday is a factual match."""
    if chart_birth_date is None:
        return None
    matches = [
        title for title, birth_date in candidates if birth_date == chart_birth_date
    ]
    return matches[0] if len(matches) == 1 else None


def _title_from_name_or_url(value: str) -> str:
    """
    Accept either:
        Noam Chomsky
        Noam_Chomsky
        https://en.wikipedia.org/wiki/Noam_Chomsky
    """
    value = value.strip()

    if not value:
        raise ValueError("Wikipedia title cannot be empty.")

    parsed = urlparse(value)

    if parsed.scheme and parsed.netloc:
        marker = "/wiki/"

        if marker not in parsed.path:
            raise ValueError("The URL is not a Wikipedia article URL.")

        value = parsed.path.split(marker, 1)[1]

    return unquote(value).replace("_", " ").strip()


def fetch_wikipedia_blurb(
    person: str,
    *,
    paragraph_limit: int = 3,
    api_query: Callable[[Mapping[str, Any]], dict[str, Any]] = _wikipedia_api_query,
) -> WikipediaBlurb:
    """
    Retrieve the introductory paragraphs from an English Wikipedia article.

    The function deliberately refuses disambiguation pages rather than
    silently choosing the wrong human.
    """
    if paragraph_limit < 1:
        raise ValueError("paragraph_limit must be at least 1.")

    requested_title = _title_from_name_or_url(person)
    params: dict[str, Any] = {
        "action": "query",
        "format": "json",
        "formatversion": 2,

        # Retrieve introductory article text.
        "prop": "extracts|pageprops|info",
        "exintro": 1,
        "explaintext": 1,

        # Resolve ordinary redirects and normalized title forms.
        "redirects": 1,
        "converttitles": 1,

        # Include the canonical article URL.
        "inprop": "url",
        "titles": requested_title,
    }

    try:
        payload = api_query(params)
    except Exception as exc:
        raise WikipediaError(
            f"Wikipedia request failed for {requested_title!r}."
        ) from exc

    pages = payload.get("query", {}).get("pages", [])

    if not pages:
        raise WikipediaPageNotFound(
            f"No Wikipedia result was returned for {requested_title!r}."
        )

    page = pages[0]

    if page.get("missing") is True:
        raise WikipediaPageNotFound(
            f"No Wikipedia article exists under {requested_title!r}."
        )

    if not isinstance(page, dict):
        raise WikipediaError("Wikipedia returned an invalid page record.")

    pageprops = page.get("pageprops", {})

    if "disambiguation" in pageprops:
        raise WikipediaDisambiguationError(
            f"{page.get('title', requested_title)!r} is a "
            "disambiguation page; more identifying information is required."
        )

    extract = page.get("extract", "").strip()

    # TextExtracts ordinarily separates lead paragraphs with newline runs.
    paragraphs = [
        paragraph.strip()
        for paragraph in extract.splitlines()
        if paragraph.strip()
    ]

    return WikipediaBlurb(
        title=str(page.get("title") or requested_title),
        paragraphs=paragraphs[:paragraph_limit],
        page_url=str(page.get("fullurl") or ""),
        page_id=int(page.get("pageid") or 0),
    )


def fetch_wikipedia_biography_by_name(
    chart_name: str,
    *,
    paragraph_limit: int = 3,
) -> str:
    """Resolve a chart name through Wikipedia search and return its lead text."""
    resolution = resolve_wikipedia_page_options(chart_name)
    status = str(resolution.get("status") or "")
    if status == "not_found":
        raise WikipediaPageNotFound(
            f"No Wikipedia page was found for {chart_name!r}."
        )
    if status == "multiple":
        options = [
            str(option).strip()
            for option in resolution.get("options", [])
            if str(option).strip()
        ]
        raise WikipediaAmbiguousPageError(chart_name, options)

    resolved_title = str(resolution.get("title") or "").strip()
    if not resolved_title:
        raise WikipediaPageNotFound(
            f"No Wikipedia page was found for {chart_name!r}."
        )
    blurb = fetch_wikipedia_blurb(resolved_title, paragraph_limit=paragraph_limit)
    if not blurb.text:
        raise WikipediaError(
            f"Wikipedia did not provide biography text for {blurb.title!r}."
        )
    return blurb.text


def populate_wikipedia_biography(
    profile_data: MutableMapping[str, Any],
    *,
    page_title: str | None = None,
    paragraph_limit: int = 3,
) -> WikipediaBlurb:
    """Populate EphemeralDaddy's biography metadata from a Wikipedia lead.

    ``page_title`` should be supplied when the import flow has already resolved
    a specific Wikipedia result.  Otherwise the imported chart name is used,
    allowing Wikipedia to handle ordinary redirects without introducing a
    second, potentially inconsistent search-selection step.
    """
    lookup_title = str(page_title or profile_data.get("name") or "").strip()
    if not lookup_title:
        raise ValueError("A chart name or resolved Wikipedia title is required.")

    blurb = fetch_wikipedia_blurb(lookup_title, paragraph_limit=paragraph_limit)
    if blurb.text:
        profile_data["biography"] = blurb.text
    return blurb
