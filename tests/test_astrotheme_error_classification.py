import urllib.error

import pytest

from ephemeraldaddy.gui import astrotheme_search


def test_http_failures_are_classified_as_network_errors(monkeypatch):
    def fail_urlopen(*_args, **_kwargs):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(astrotheme_search, "urlopen", fail_urlopen)

    with pytest.raises(astrotheme_search.AstrothemeNetworkError):
        astrotheme_search._astrotheme_http_get("https://example.invalid/profile")


def test_http_get_sanitizes_replacement_character_before_urlopen(monkeypatch):
    requested_urls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"profile"

    def fake_urlopen(request, **_kwargs):
        requested_urls.append(request.full_url)
        request.full_url.encode("ascii")
        return Response()

    monkeypatch.setattr(astrotheme_search, "urlopen", fake_urlopen)

    assert (
        astrotheme_search._astrotheme_http_get(
            "https://www.astrotheme.com/astrology/Tom_Suozzi\ufffd"
        )
        == "profile"
    )
    assert requested_urls == ["https://www.astrotheme.com/astrology/Tom_Suozzi"]


def test_http_url_percent_encodes_legitimate_unicode_characters():
    safe_url = astrotheme_search._ascii_safe_http_url(
        "https://www.astrotheme.com/astrology/François_Hollande?q=été"
    )

    assert safe_url == (
        "https://www.astrotheme.com/astrology/Fran%C3%A7ois_Hollande?q=%C3%A9t%C3%A9"
    )
    safe_url.encode("ascii")


def test_invalid_profile_markup_is_classified_as_format_error(monkeypatch):
    monkeypatch.setattr(
        astrotheme_search, "_astrotheme_http_get", lambda _url: "<html></html>"
    )

    with pytest.raises(astrotheme_search.AstrothemeProfileFormatError):
        astrotheme_search.parse_astrotheme_profile(
            "https://www.astrotheme.com/astrology/Test"
        )
