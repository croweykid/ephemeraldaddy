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
