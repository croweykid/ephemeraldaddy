from types import SimpleNamespace

import pytest

from ephemeraldaddy.analysis.birthplace import (
    BirthplaceLocality, birthplace_label, chart_locality, gazetteer_label, locality_from_address,
    locality_from_text, needs_locality_lookup,
)
from ephemeraldaddy.io import geocode


@pytest.mark.parametrize("address,expected", [
    (dict(amenity="United States Post Office", house_number="12", road="Main Street",
          city="Atlanta", county="Fulton County", state="Georgia", postcode="30303",
          country="United States", country_code="us"), ("Atlanta", "Georgia", "USA")),
    (dict(village="Small Village", state="Québec", country_code="ca"),
     ("Small Village", "Québec", "Canada")),
    (dict(city="Москва", state="Московская область", country_code="ru"),
     ("Москва", "Московская область", "Russia")),
    (dict(town="Town", municipality="Rural Council", province="Province", country_code="za"),
     ("Town", "Province", "South Africa")),
    (dict(city="Singapore", country_code="sg"), ("Singapore", "", "Singapore")),
    (dict(amenity="Government Building", county="Some County", country_code="us"),
     ("", "", "USA")),
])
def test_structured_locality_uses_settlement_and_region_not_feature_names(address, expected):
    place = locality_from_address(address)
    assert (place.city, place.region, place.country) == expected


@pytest.mark.parametrize("raw,label,city", [
    ("Chicago, IL, US", "Chicago, Illinois, USA", "Chicago"),
    ("Paris, Île-de-France, France", "Paris, Île-de-France, France", "Paris"),
    ("Paris, 11, FR", "Paris, France", "Paris"),
    ("New York, New York, US", "New York, New York, USA", "New York"),
    ("Paris, France", "Paris, France", "Paris"),
    ("Kinshasa, Kinshasa, Congo, The Democratic Republic of the",
     "Kinshasa, Kinshasa, Congo, The Democratic Republic of the", "Kinshasa"),
    ("United States Post Office, 12 Main Street, Atlanta, Fulton County, Georgia, 30303, United States",
     "Georgia, USA", ""),
    ("Government Building", "", ""),
    ("The Blue House", "", ""),
    ("France", "France", ""),
    ("City Hall, Baker Street, London, England, UK", "UK", ""),
])
def test_legacy_addresses_cannot_be_counted_as_cities(raw, label, city):
    place = locality_from_text(raw)
    assert place.label == label
    assert place.city == city
    assert birthplace_label(raw) == label


def test_online_forward_and_candidate_search_keep_coordinates_but_format_locality(monkeypatch):
    calls = []
    location = SimpleNamespace(
        latitude=33.7491, longitude=-84.3882,
        address="United States Post Office, 12 Main Street, Atlanta, Georgia, USA",
        raw={"address": dict(amenity="United States Post Office", road="Main Street",
                             city="Atlanta", state="Georgia", country_code="us")},
    )
    class Provider:
        def geocode(self, query, **kwargs):
            calls.append(kwargs)
            return [location] if kwargs.get("exactly_one") is False else location
    monkeypatch.setattr(geocode, "_get_geolocator", Provider)
    monkeypatch.setattr(geocode, "local_geocode_location", lambda query: None)
    monkeypatch.setattr(geocode, "local_search_locations", lambda query, limit: [])
    monkeypatch.setattr(geocode, "resolve_search_sources", lambda: ["online"])
    monkeypatch.delenv("EPHEMERALDADDY_GAZETTEER_ONLY", raising=False)
    assert geocode.geocode_location("Atlanta") == (
        33.7491, -84.3882, "Atlanta, Georgia, USA",
    )
    assert geocode.search_locations("Atlanta", allow_online=True) == [
        ("Atlanta, Georgia, USA", 33.7491, -84.3882),
    ]
    assert all(call["addressdetails"] for call in calls)


def test_reverse_lookup_requests_city_level_metadata_at_original_coordinates(monkeypatch):
    calls = []
    class Provider:
        def reverse(self, coordinates, **kwargs):
            calls.append((coordinates, kwargs))
            return SimpleNamespace(raw={"address": dict(
                city="Springfield", state="Illinois", country_code="us",
                building="Court House",
            )})
    monkeypatch.setattr(geocode, "_get_geolocator", Provider)
    monkeypatch.delenv("EPHEMERALDADDY_GAZETTEER_ONLY", raising=False)
    place = geocode.locality_for_coordinates(39.801, -89.644)
    assert place.label == "Springfield, Illinois, USA"
    assert calls == [((39.801, -89.644), dict(
        exactly_one=True, addressdetails=True, zoom=10,
    ))]


def test_missing_settlement_does_not_fall_back_to_a_building_or_nearest_city(monkeypatch):
    location = SimpleNamespace(
        address="Government Building, USA",
        raw={"address": dict(amenity="Government Building", country_code="us")},
    )
    monkeypatch.setattr(geocode, "_get_geolocator", lambda: SimpleNamespace(
        reverse=lambda *args, **kwargs: location,
    ))
    monkeypatch.delenv("EPHEMERALDADDY_GAZETTEER_ONLY", raising=False)
    with pytest.raises(geocode.LocationLookupError, match="no confirmed city"):
        geocode.locality_for_coordinates(1, 2)


def test_chart_locality_cache_is_rejected_after_birth_data_edits():
    chart = SimpleNamespace(birth_place="Government Building", lat=1, lon=2)
    chart.birthplace_locality = BirthplaceLocality("Town", "Region", "USA")
    chart._birthplace_locality_source = ("Government Building", 1, 2)
    assert chart_locality(chart).city == "Town"
    chart.lat = 3
    assert not chart_locality(chart).city
    chart.birth_place = "Paris, France"
    assert chart_locality(chart).city == "Paris"


def test_all_uncached_legacy_labels_require_authoritative_locality_metadata():
    assert needs_locality_lookup("Paris, 11, FR")
    assert needs_locality_lookup("United States Post Office")
    assert needs_locality_lookup("Paris, Île-de-France, FR")
    assert needs_locality_lookup("Chicago, IL, US")
    assert not needs_locality_lookup("")


def test_provider_without_structured_metadata_does_not_use_its_raw_address(monkeypatch):
    monkeypatch.setattr(geocode, "_get_geolocator", lambda: SimpleNamespace(
        geocode=lambda *args, **kwargs: SimpleNamespace(
            address="The Blue House", latitude=1, longitude=2,
        ),
    ))
    with pytest.raises(geocode.LocationLookupError, match="No locality metadata"):
        geocode._online_geocode("Seoul")


def test_populated_place_names_are_not_removed_by_legacy_address_safety_checks():
    assert gazetteer_label("Hospital, 02, CR") == "Hospital, Costa Rica"


def test_forward_and_reverse_requests_share_a_provider_gate(monkeypatch):
    import geopy.extra.rate_limiter
    gates, calls = [], []
    class FakeGate:
        def __init__(self, request, **kwargs):
            gates.append(self)
            self.request = request
        def __call__(self, method, *args, **kwargs):
            calls.append(method.__name__)
            return self.request(method, *args, **kwargs)
    class Provider:
        def geocode(self, *args, **kwargs): return "forward"
        def reverse(self, *args, **kwargs): return "reverse"
    monkeypatch.setattr(geocode, "_geolocator", None)
    monkeypatch.setattr(geocode, "ensure_package", lambda name: SimpleNamespace(
        geocoders=SimpleNamespace(Nominatim=lambda **kwargs: Provider()),
    ))
    monkeypatch.setattr(geopy.extra.rate_limiter, "RateLimiter", FakeGate)
    locator = geocode._get_geolocator()
    assert locator.geocode("Town") == "forward"
    assert locator.reverse((1, 2)) == "reverse"
    assert len(gates) == 1 and calls == ["geocode", "reverse"]


def test_country_with_comma_retains_its_identity_when_formatted_and_parsed():
    place = locality_from_address(dict(city="Kinshasa", state="Kinshasa", country_code="cd"))
    assert locality_from_text(place.label) == place
