from threading import Event
from urllib.error import HTTPError

import pytest

from ephemeraldaddy.io.web_profile.pacing import (
    LookupCancelled, RequestPacer, paced_requests, paced_urlopen, _retry_delay,
)


class FakeEvent:
    def __init__(self):
        self.now = 0
        self.delays = []
    def is_set(self):
        return False
    def wait(self, delay):
        self.delays.append(delay)
        self.now += delay
        return False


def test_nested_provider_calls_are_paced_and_retry_after_is_respected(monkeypatch):
    from ephemeraldaddy.gui import wikipedia_search, astrotheme_search
    from ephemeraldaddy.gui.wikipedia_blurb_getter import fetch_wikipedia_blurb
    event = FakeEvent()
    pacer = RequestPacer(clock=lambda: event.now)
    calls = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"query":{"pages":[{"title":"A","extract":"Bio"}]}}'
    def opener(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 2:
            raise HTTPError(request.full_url, 429, 'Slow down', {'Retry-After': '4'}, None)
        return Response()
    monkeypatch.setattr(wikipedia_search, 'urlopen', opener)
    monkeypatch.setattr(astrotheme_search, 'urlopen', opener)
    with paced_requests(event, pacer):
        astrotheme_search._astrotheme_http_get('https://www.astrotheme.com/test')
        wikipedia_search._wikipedia_http_get_json('https://www.wikidata.org/test')
        assert fetch_wikipedia_blurb('A').text == 'Bio'
    assert len(calls) == 4
    assert event.delays == [1, 4, 1]


def test_cancelled_request_never_opens_connection():
    event = Event(); event.set()
    with paced_requests(event), pytest.raises(LookupCancelled):
        paced_urlopen(lambda *a, **k: pytest.fail('opened connection'), 'url', timeout=10)


def test_cancel_during_retry_wait_stops_requests():
    class CancelOnWait(FakeEvent):
        def wait(self, delay): return True
    event = CancelOnWait()
    calls = []
    def opener(*args, **kwargs):
        calls.append(1)
        raise HTTPError('url', 503, 'Unavailable', {'Retry-After': '30'}, None)
    with paced_requests(event), pytest.raises(LookupCancelled):
        paced_urlopen(opener, 'url', timeout=10)
    assert len(calls) == 1


def test_retry_after_http_date():
    assert _retry_delay('Thu, 01 Jan 1970 00:00:00 GMT') == 0
    assert _retry_delay('invalid') == 1


@pytest.mark.parametrize('status, attempts', [(429, 3), (503, 3), (404, 1)])
def test_retries_are_bounded_and_other_http_errors_are_not_retried(status, attempts):
    event = FakeEvent()
    calls = []
    def opener(*args, **kwargs):
        calls.append(1)
        raise HTTPError('url', status, 'Error', {'Retry-After': '1'}, None)
    with paced_requests(event, RequestPacer(clock=lambda:event.now)), pytest.raises(HTTPError):
        paced_urlopen(opener, 'url', timeout=10)
    assert len(calls) == attempts


def test_batch_policy_does_not_leak_to_interactive_requests():
    event = Event(); event.set()
    with paced_requests(event):
        pass
    assert paced_urlopen(lambda *args, **kwargs:'response', 'url', timeout=10) == 'response'
