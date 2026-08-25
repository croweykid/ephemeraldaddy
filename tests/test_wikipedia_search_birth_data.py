from __future__ import annotations

import pytest

from ephemeraldaddy.gui import wikipedia_search as subject


def _wiki_response(wikitext: str) -> dict:
    return {
        "query": {
            "pages": [
                {
                    "pageid": 1,
                    "title": "Example Person",
                    "revisions": [
                        {"slots": {"main": {"content": wikitext}}}
                    ],
                }
            ]
        }
    }


def _time_claim(
    time_text: str,
    *,
    precision: int = 11,
    rank: str = "normal",
) -> dict:
    return {
        "rank": rank,
        "mainsnak": {
            "snaktype": "value",
            "datavalue": {
                "type": "time",
                "value": {
                    "time": time_text,
                    "precision": precision,
                },
            },
        },
    }


def _place_claim(entity_id: str, *, rank: str = "normal") -> dict:
    return {
        "rank": rank,
        "mainsnak": {
            "snaktype": "value",
            "datavalue": {
                "type": "wikibase-entityid",
                "value": {
                    "entity-type": "item",
                    "id": entity_id,
                },
            },
        },
    }


def test_parse_wikipedia_birth_data_uses_curtis_turner_infobox_first(monkeypatch):
    wikitext = """
{{Infobox racing driver
| name = Curtis Turner
| birth_date = {{Birth date|1924|4|12}}
| birth_place = [[Floyd, Virginia]], U.S.
| death_date = {{Death date and age|1970|10|4|1924|4|12}}
}}
"""
    monkeypatch.setattr(
        subject,
        "_wikipedia_api_query",
        lambda _params: _wiki_response(wikitext),
    )
    monkeypatch.setattr(
        subject,
        "_wikidata_api_query",
        lambda _params: (_ for _ in ()).throw(
            AssertionError("complete Wikipedia infobox should not need Wikidata")
        ),
    )

    result = subject.parse_wikipedia_birth_data("Curtis Turner")

    assert result == {
        "name": "Curtis Turner",
        "birth_year": 1924,
        "birth_month": 4,
        "birth_day": 12,
        "birth_place": "Floyd, Virginia, U.S.",
        "source_url": "https://en.wikipedia.org/wiki/Curtis_Turner",
    }


def test_parse_wikipedia_birth_data_handles_red_farmer_birth_date_and_age(monkeypatch):
    wikitext = """
{{Infobox NASCAR driver
| name = Red Farmer
| birth_date = {{Birth date and age|1932|10|15}}
| birth_place = [[Nashville, Tennessee]], U.S.
}}
"""
    monkeypatch.setattr(
        subject,
        "_wikipedia_api_query",
        lambda _params: _wiki_response(wikitext),
    )
    monkeypatch.setattr(
        subject,
        "_wikidata_api_query",
        lambda _params: (_ for _ in ()).throw(
            AssertionError("complete Wikipedia infobox should not need Wikidata")
        ),
    )

    result = subject.parse_wikipedia_birth_data("Red Farmer")

    assert (
        result["birth_year"],
        result["birth_month"],
        result["birth_day"],
    ) == (1932, 10, 15)
    assert result["birth_place"] == "Nashville, Tennessee, U.S."


def test_infobox_parser_preserves_nested_link_pipes():
    wikitext = """
{{Infobox person
| birth_date = {{Birth date|1990|4|5}}
| birth_place = [[Floyd, Virginia|Floyd]], [[Virginia]], [[United States|U.S.]]
| occupation = Driver
}}
"""

    birth_date, birth_place = subject._wikipedia_infobox_birth_data(wikitext)

    assert birth_date is not None
    assert birth_date.isoformat() == "1990-04-05"
    assert birth_place == "Floyd, Virginia, Virginia, United States"


def test_parse_wikipedia_birth_data_falls_back_to_wikidata(monkeypatch):
    monkeypatch.setattr(
        subject,
        "_wikipedia_api_query",
        lambda _params: _wiki_response("{{Infobox person\n| name = Neil Bonnett\n}}"),
    )

    calls = []

    def api_query(params):
        calls.append(dict(params))
        if params.get("sites") == "enwiki":
            return {
                "entities": {
                    "Q123": {
                        "id": "Q123",
                        "claims": {
                            "P569": [_time_claim("+1946-07-30T00:00:00Z")],
                            "P19": [_place_claim("Q456")],
                        },
                    }
                }
            }
        if params.get("ids") == "Q456":
            return {
                "entities": {
                    "Q456": {
                        "id": "Q456",
                        "labels": {
                            "en": {"language": "en", "value": "Hueytown"}
                        },
                        "sitelinks": {
                            "enwiki": {
                                "site": "enwiki",
                                "title": "Hueytown, Alabama",
                            }
                        },
                    }
                }
            }
        raise AssertionError(f"Unexpected Wikidata request: {params!r}")

    monkeypatch.setattr(subject, "_wikidata_api_query", api_query)

    result = subject.parse_wikipedia_birth_data("Neil Bonnett")

    assert (
        result["birth_year"],
        result["birth_month"],
        result["birth_day"],
    ) == (1946, 7, 30)
    assert result["birth_place"] == "Hueytown, Alabama"
    assert calls[0]["action"] == "wbgetentities"
    assert calls[0]["titles"] == "Neil Bonnett"


def test_wikipedia_plain_full_date_does_not_require_wikidata(monkeypatch):
    wikitext = """
{{Infobox person
| birth_date = April 5, 1990
| birth_place = Exampleville
}}
"""
    monkeypatch.setattr(
        subject,
        "_wikipedia_api_query",
        lambda _params: _wiki_response(wikitext),
    )
    monkeypatch.setattr(
        subject,
        "_wikidata_api_query",
        lambda _params: (_ for _ in ()).throw(RuntimeError("Wikidata unavailable")),
    )

    result = subject.parse_wikipedia_birth_data("Example Person")

    assert (
        result["birth_year"],
        result["birth_month"],
        result["birth_day"],
    ) == (1990, 4, 5)
    assert result["birth_place"] == "Exampleville"


def test_parse_wikipedia_birth_data_prefers_preferred_wikidata_birthdate(monkeypatch):
    monkeypatch.setattr(
        subject,
        "_wikipedia_api_query",
        lambda _params: _wiki_response("{{Infobox person|name=Example Person}}"),
    )

    def api_query(params):
        if params.get("sites") == "enwiki":
            return {
                "entities": {
                    "Q123": {
                        "claims": {
                            "P569": [
                                _time_claim("+1945-07-30T00:00:00Z"),
                                _time_claim(
                                    "+1946-07-30T00:00:00Z",
                                    rank="preferred",
                                ),
                            ],
                            "P19": [],
                        }
                    }
                }
            }
        raise AssertionError(f"Unexpected Wikidata request: {params!r}")

    monkeypatch.setattr(subject, "_wikidata_api_query", api_query)

    result = subject.parse_wikipedia_birth_data("Example Person")

    assert (
        result["birth_year"],
        result["birth_month"],
        result["birth_day"],
    ) == (1946, 7, 30)
    assert result["birth_place"] == ""


def test_parse_wikipedia_birth_data_rejects_partial_wikidata_date(monkeypatch):
    monkeypatch.setattr(
        subject,
        "_wikipedia_api_query",
        lambda _params: _wiki_response("{{Infobox person|name=Example Person}}"),
    )
    monkeypatch.setattr(
        subject,
        "_wikidata_api_query",
        lambda _params: {
            "entities": {
                "Q123": {
                    "claims": {
                        "P569": [
                            _time_claim(
                                "+1946-00-00T00:00:00Z",
                                precision=9,
                            )
                        ],
                        "P19": [],
                    }
                }
            }
        },
    )

    with pytest.raises(ValueError, match="No complete birthdate info"):
        subject.parse_wikipedia_birth_data("Example Person")


def test_rendered_wikipedia_html_is_not_part_of_birth_lookup():
    source = subject.__file__
    assert source is not None
    module_text = open(source, encoding="utf-8").read()
    assert "_wikipedia_http_get_text" not in module_text
    assert 'class=["\\\']' not in module_text
