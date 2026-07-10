from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"


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


def _make_session() -> requests.Session:
    retry_policy = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )

    session = requests.Session()
    session.mount(
        "https://",
        HTTPAdapter(max_retries=retry_policy),
    )

    # Replace this with your app's actual name and contact/project page.
    session.headers.update({
        "User-Agent": (
            "EphemeralDaddy/1.0 "
            "(Wikipedia biography retriever; contact: your-email@example.com)"
        )
    })

    return session


def fetch_wikipedia_blurb(
    person: str,
    *,
    paragraph_limit: int = 3,
    timeout: float = 12.0,
    session: requests.Session | None = None,
) -> WikipediaBlurb:
    """
    Retrieve the introductory paragraphs from an English Wikipedia article.

    The function deliberately refuses disambiguation pages rather than
    silently choosing the wrong human.
    """
    if paragraph_limit < 1:
        raise ValueError("paragraph_limit must be at least 1.")

    requested_title = _title_from_name_or_url(person)
    http = session or _make_session()

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
        response = http.get(
            WIKIPEDIA_API,
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise WikipediaError(
            f"Wikipedia request failed for {requested_title!r}."
        ) from exc
    except ValueError as exc:
        raise WikipediaError(
            "Wikipedia returned invalid JSON."
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
        title=page["title"],
        paragraphs=paragraphs[:paragraph_limit],
        page_url=page["fullurl"],
        page_id=page["pageid"],
    )

# Sample usage:
# blurb = fetch_wikipedia_blurb(
# "https://en.wikipedia.org/wiki/Frances_Willard",
# paragraph_limit=3,
# )
# print(blurb.title)
# print(blurb.text)
# print(blurb.page_url)