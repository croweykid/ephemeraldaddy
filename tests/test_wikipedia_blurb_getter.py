from __future__ import annotations

import pytest

from ephemeraldaddy.gui import wikipedia_blurb_getter as subject


def _api_response(**page_overrides):
    page = {
        "pageid": 42,
        "title": "Example Person",
        "fullurl": "https://en.wikipedia.org/wiki/Example_Person",
        "extract": "First paragraph.\n\nSecond paragraph.\nThird paragraph.",
        "pageprops": {},
    }
    page.update(page_overrides)
    return {"query": {"pages": [page]}}


def test_fetch_wikipedia_blurb_uses_shared_api_and_limits_paragraphs():
    captured = {}

    def api_query(params):
        captured.update(params)
        return _api_response()

    blurb = subject.fetch_wikipedia_blurb(
        "https://en.wikipedia.org/wiki/Example_Person",
        paragraph_limit=2,
        api_query=api_query,
    )

    assert captured["titles"] == "Example Person"
    assert captured["prop"] == "extracts|pageprops|info"
    assert captured["exintro"] == 1
    assert captured["explaintext"] == 1
    assert blurb.text == "First paragraph.\n\nSecond paragraph."
    assert blurb.page_id == 42


def test_fetch_wikipedia_blurb_refuses_disambiguation_pages():
    with pytest.raises(subject.WikipediaDisambiguationError):
        subject.fetch_wikipedia_blurb(
            "Example Person",
            api_query=lambda _params: _api_response(
                pageprops={"disambiguation": ""}
            ),
        )


def test_populate_wikipedia_biography_uses_ephemeraldaddy_metadata_name(monkeypatch):
    profile_data = {"name": "Imported Person", "biography": "Old biography"}
    expected = subject.WikipediaBlurb(
        title="Imported Person",
        paragraphs=["New lead.", "More context."],
        page_url="https://en.wikipedia.org/wiki/Imported_Person",
        page_id=7,
    )
    calls = []

    def fetch(title, *, paragraph_limit):
        calls.append((title, paragraph_limit))
        return expected

    monkeypatch.setattr(subject, "fetch_wikipedia_blurb", fetch)

    result = subject.populate_wikipedia_biography(profile_data)

    assert result is expected
    assert calls == [("Imported Person", 3)]
    assert profile_data["biography"] == "New lead.\n\nMore context."


def test_populate_wikipedia_biography_preserves_existing_text_for_empty_extract(
    monkeypatch,
):
    profile_data = {"name": "Imported Person", "biography": "Existing biography"}
    monkeypatch.setattr(
        subject,
        "fetch_wikipedia_blurb",
        lambda *_args, **_kwargs: subject.WikipediaBlurb(
            title="Imported Person", paragraphs=[], page_url="", page_id=7
        ),
    )

    subject.populate_wikipedia_biography(profile_data, page_title="Resolved Person")

    assert profile_data["biography"] == "Existing biography"
