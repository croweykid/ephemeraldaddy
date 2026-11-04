from types import SimpleNamespace

from ephemeraldaddy.io import geocode, local_gazetteer


def test_batch_search_enables_online_candidates_without_changing_default(monkeypatch):
    calls = []
    monkeypatch.delenv('EPHEMERALDADDY_GAZETTEER_SEARCH_ONLINE', raising=False)
    monkeypatch.delenv('EPHEMERALDADDY_GAZETTEER_ONLY', raising=False)
    monkeypatch.setattr(local_gazetteer, 'get_local_gazetteer', lambda: None)
    class Geocoder:
        def geocode(self, query, **kwargs):
            calls.append((query, kwargs))
            return [SimpleNamespace(address='North', latitude=1, longitude=2),
                    SimpleNamespace(address='South', latitude=3, longitude=4)]
    monkeypatch.setattr(geocode, '_get_geolocator', Geocoder)
    assert geocode.search_locations('Springfield', limit=7) == []
    assert calls == []
    assert geocode.search_locations('Springfield', limit=7, allow_online=True) == [('North', 1, 2), ('South', 3, 4)]
    assert calls == [('Springfield', dict(exactly_one=False, addressdetails=True, limit=7))]


def test_online_override_still_respects_gazetteer_only(monkeypatch):
    monkeypatch.setenv('EPHEMERALDADDY_GAZETTEER_ONLY', '1')
    monkeypatch.setattr(local_gazetteer, 'get_local_gazetteer', lambda: None)
    monkeypatch.setattr(geocode, '_get_geolocator', lambda: (_ for _ in ()).throw(AssertionError('Online request')))
    assert geocode.search_locations('Missing', limit=7, allow_online=True) == []


def test_local_candidates_take_precedence_over_online_search(monkeypatch):
    monkeypatch.delenv('EPHEMERALDADDY_GAZETTEER_ONLY', raising=False)
    monkeypatch.setattr(local_gazetteer, 'get_local_gazetteer', lambda: object())
    candidates = [('North', 1, 2), ('South', 3, 4)]
    monkeypatch.setattr(geocode, 'local_search_locations', lambda query, limit: candidates)
    monkeypatch.setattr(geocode, '_get_geolocator', lambda: (_ for _ in ()).throw(AssertionError('Online request')))
    assert geocode.search_locations('Springfield', limit=7, allow_online=True) == candidates


def test_local_batch_places_never_consume_pacing_slots(monkeypatch):
    from ephemeraldaddy.gui.features.import_export.batch_web_import import window
    from ephemeraldaddy.io.web_profile import pacing
    class Pacer:
        def pace(self, *args): raise AssertionError('Paced a local lookup')
    monkeypatch.setattr(pacing, 'RequestPacer', Pacer)
    monkeypatch.setattr(local_gazetteer, 'get_local_gazetteer', lambda: object())
    monkeypatch.setattr(geocode, 'local_search_locations', lambda query, limit: [(query, 1, 2)])
    monkeypatch.setattr(geocode, '_get_geolocator', lambda: (_ for _ in ()).throw(AssertionError('Online request')))
    worker = window._PlaceValidationWorker([(index, f'Place {index}') for index in range(100)], {})
    results = []
    worker.result.connect(results.append)
    worker.run()
    assert len(results) == 100 and all(len(result[2]) == 1 and not result[3] for result in results)


def test_online_fallbacks_are_paced_while_local_hits_and_cache_hits_are_free(monkeypatch):
    from ephemeraldaddy.io.web_profile.pacing import RequestPacer
    from ephemeraldaddy.gui.features.import_export.batch_web_import import window
    now, delays, online = [0.0], [], []
    class FakeEvent:
        def is_set(self): return False
        def wait(self, delay):
            delays.append(delay)
            now[0] += delay
            return False
    event = FakeEvent()
    from ephemeraldaddy.io.web_profile import pacing
    monkeypatch.setattr(pacing, 'RequestPacer', lambda: RequestPacer(clock=lambda: now[0]))
    monkeypatch.delenv('EPHEMERALDADDY_GAZETTEER_ONLY', raising=False)
    monkeypatch.setattr(local_gazetteer, 'get_local_gazetteer', lambda: object())
    monkeypatch.setattr(geocode, 'local_search_locations', lambda query, limit: [(query, 1, 2)] if query.startswith('Local') else [])
    class Geocoder:
        def geocode(self, query, **kw):
            online.append((query, now[0]))
            return [SimpleNamespace(address=query, latitude=1, longitude=2)]
    monkeypatch.setattr(geocode, '_get_geolocator', Geocoder)
    places = ['Local A', 'Online A', 'Local B', 'Online B', 'Online A', 'Online C']
    worker = window._PlaceValidationWorker(list(enumerate(places)), {})
    worker.cancel_event = event
    results = []
    worker.result.connect(results.append)
    worker.run()
    assert len(results) == len(places)
    assert online == [('Online A', 0), ('Online B', 1), ('Online C', 2)]
    assert delays == [1, 1]


def test_cancel_during_online_pacing_prevents_network_call(monkeypatch):
    import pytest
    from ephemeraldaddy.io.web_profile.pacing import LookupCancelled, RequestPacer, paced_requests
    online = []
    class CancelOnWait:
        def is_set(self): return False
        def wait(self, delay): return True
    event = CancelOnWait()
    monkeypatch.delenv('EPHEMERALDADDY_GAZETTEER_ONLY', raising=False)
    monkeypatch.setattr(local_gazetteer, 'get_local_gazetteer', lambda: None)
    class Geocoder:
        def geocode(self, query, **kw):
            online.append(query)
            return [SimpleNamespace(address=query, latitude=1, longitude=2)]
    monkeypatch.setattr(geocode, '_get_geolocator', Geocoder)
    with paced_requests(event, RequestPacer(clock=lambda: 0)):
        geocode.search_locations('First', allow_online=True)
        with pytest.raises(LookupCancelled):
            geocode.search_locations('Second', allow_online=True)
    assert online == ['First']
