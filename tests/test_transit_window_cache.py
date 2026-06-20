import datetime as dt
from types import SimpleNamespace

from ephemeraldaddy.gui.features.transits.cache import TransitWindowCache


class _AspectType:
    name = "Conjunction"
    angle_deg = 0.0
    orb_deg = 1.0


def _hit():
    return SimpleNamespace(
        a=SimpleNamespace(name="Mars"),
        aspect="Conjunction",
        b=SimpleNamespace(name="Venus"),
    )


def _rules():
    return SimpleNamespace(aspect_types=[_AspectType()])


def _scan_config():
    return SimpleNamespace(scan_step_hours=6, scan_precision_minutes=30)


def test_transit_window_cache_builds_stable_location_sensitive_keys():
    cache = TransitWindowCache(limit=4)
    key = cache.build_key(
        mode="Life Forecast",
        hit_obj=_hit(),
        chart_dt=dt.datetime(2026, 6, 20, 12, tzinfo=dt.timezone.utc),
        transit_location=(40.712776, -74.005974),
        mode_rules={"Life Forecast": _rules()},
        scan_config=_scan_config(),
    )

    assert key[:5] == (
        "Life Forecast",
        "Mars",
        "Conjunction",
        "Venus",
        "2026-06-20T12:00:00+00:00",
    )
    assert key[5:7] == (40.7128, -74.006)


def test_transit_window_cache_tracks_metrics_and_evicts_lru_entries():
    cache = TransitWindowCache(limit=1)

    assert cache.get(("missing",)) is None
    cache.put(("first",), {"resolved": True})
    assert cache.get(("first",)) == {"resolved": True}
    cache.put(("second",), {"resolved": False})

    assert cache.get(("first",)) is None
    assert cache.get(("second",)) == {"resolved": False}
    assert cache.metrics["cache_hits"] == 2
    assert cache.metrics["cache_misses"] == 2
    assert cache.metrics["completed_requests"] == 2
