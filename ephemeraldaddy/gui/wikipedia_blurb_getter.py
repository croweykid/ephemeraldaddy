from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable, Mapping, MutableMapping
from typing import Any
from urllib.parse import unquote, urlparse

from ephemeraldaddy.gui.wikipedia_search import _wikipedia_api_query


class WikipediaError(RuntimeError):
    """Base exception for Wikipedia retrieval errors."""


class WikipediaPageNotFound(WikipediaError):
    pass


class WikipediaDisambiguationError(WikipediaError):
    pass


@dataclass(frozen=True)
class WikipediaBlurb:
    title: str
    paragraphs: list[str]
    page_url: str
    page_id: int

    @property
    def text(self) -> str:
        return "\n\n".join(self.paragraphs)


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
    """Return Wikipedia lead text for Chart Editor biography imports."""
    blurb = fetch_wikipedia_blurb(chart_name, paragraph_limit=paragraph_limit)
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
