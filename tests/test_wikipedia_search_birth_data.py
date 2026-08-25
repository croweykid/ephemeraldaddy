from __future__ import annotations

import pytest

from ephemeraldaddy.gui import wikipedia_search as subject


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


def test_parse_wikipedia_birth_data_uses_wikidata_not_article_html(monkeypatch):
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
    monkeypatch.setattr(
        subject,
        "_wikipedia_http_get_text",
        lambda _url: (_ for _ in ()).throw(
            AssertionError("birth lookup must not scrape Wikipedia article HTML")
        ),
    )

    result = subject.parse_wikipedia_birth_data("Neil Bonnett")

    assert result == {
        "name": "Neil Bonnett",
        "birth_year": 1946,
        "birth_month": 7,
        "birth_day": 30,
        "birth_place": "Hueytown, Alabama",
        "source_url": "https://en.wikipedia.org/wiki/Neil_Bonnett",
    }
    assert calls[0]["action"] == "wbgetentities"
    assert calls[0]["sites"] == "enwiki"
    assert calls[0]["titles"] == "Neil Bonnett"
    assert calls[1]["ids"] == "Q456"


def test_parse_wikipedia_birth_data_prefers_preferred_birthdate_claim(monkeypatch):
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


def test_parse_wikipedia_birth_data_uses_place_label_without_enwiki_sitelink(
    monkeypatch,
):
    def api_query(params):
        if params.get("sites") == "enwiki":
            return {
                "entities": {
                    "Q123": {
                        "claims": {
                            "P569": [_time_claim("+1990-04-05T00:00:00Z")],
                            "P19": [_place_claim("Q999")],
                        }
                    }
                }
            }
        if params.get("ids") == "Q999":
            return {
                "entities": {
                    "Q999": {
                        "labels": {
                            "en": {"language": "en", "value": "Exampleville"}
                        },
                        "sitelinks": {},
                    }
                }
            }
        raise AssertionError(f"Unexpected Wikidata request: {params!r}")

    monkeypatch.setattr(subject, "_wikidata_api_query", api_query)

    result = subject.parse_wikipedia_birth_data("Example Person")

    assert result["birth_place"] == "Exampleville"


def test_parse_wikipedia_birth_data_rejects_partial_wikidata_date(monkeypatch):
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


def test_parse_wikipedia_birth_data_reports_missing_wikidata_entity(monkeypatch):
    monkeypatch.setattr(
        subject,
        "_wikidata_api_query",
        lambda _params: {
            "entities": {
                "-1": {
                    "site": "enwiki",
                    "title": "Example Person",
                    "missing": "",
                }
            }
        },
    )

    with pytest.raises(ValueError, match="No Wikidata entity"):
        subject.parse_wikipedia_birth_data("Example Person")
