import urllib.error

import pytest

from ephemeraldaddy.gui import astrotheme_search


def test_http_failures_are_classified_as_network_errors(monkeypatch):
    def fail_urlopen(*_args, **_kwargs):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(astrotheme_search, "urlopen", fail_urlopen)

    with pytest.raises(astrotheme_search.AstrothemeNetworkError):
        astrotheme_search._astrotheme_http_get("https://example.invalid/profile")


def test_invalid_profile_markup_is_classified_as_format_error(monkeypatch):
    monkeypatch.setattr(astrotheme_search, "_astrotheme_http_get", lambda _url: "<html></html>")

    with pytest.raises(astrotheme_search.AstrothemeProfileFormatError):
        astrotheme_search.parse_astrotheme_profile("https://www.astrotheme.com/astrology/Test")
