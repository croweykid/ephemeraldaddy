from __future__ import annotations

import datetime
import json
from types import SimpleNamespace

from ephemeraldaddy.gui.features.transits.cache import (
    PERSONAL_TIMELINE_CACHE_SCHEMA_VERSION,
    PersonalTimelineDiskCache,
    personal_timeline_fingerprint,
)


UTC = datetime.timezone.utc


def _chart() -> SimpleNamespace:
    return SimpleNamespace(
        dt=datetime.datetime(2000, 1, 1, 12, tzinfo=UTC),
        lat=42.0,
        lon=-71.0,
        positions={"Sun": 280.5, "Saturn": 17.0, "AS": 92.25},
        birthtime_unknown=False,
        retcon_time_used=False,
        retcon_hour=None,
        retcon_minute=None,
        rectification_range_used=False,
        rectification_range_start_minute=None,
        rectification_range_end_minute=None,
        signs_unknown=False,
        unknown_signs=[],
        is_deceased=False,
        death_year=None,
        death_month=None,
        death_day=None,
        comments="cosmetic metadata must not dirty transit cache",
    )


def _window() -> SimpleNamespace:
    transit = SimpleNamespace(
        transiting_body="Saturn",
        natal_body="Sun",
        natal_longitude=280.5,
        aspect_name="square",
        aspect_angle=90.0,
        orb_deg=3.0,
    )
    return SimpleNamespace(
        chart_uid="ABCDEF1234567890",
        transit=transit,
        start=datetime.datetime(2030, 1, 2, 3, tzinfo=UTC),
        end=datetime.datetime(2030, 2, 3, 4, tzinfo=UTC),
        start_truncated=False,
        end_truncated=True,
    )


def _config() -> dict[str, object]:
    return {
        "algorithm_version": 1,
        "timeline_years": 120,
        "scan_step_days": 2,
        "transiting_bodies": ["Saturn"],
        "aspects": [{"name": "square", "angle_deg": 90.0, "orb_deg": 3.0}],
    }


def test_personal_timeline_disk_cache_round_trip(tmp_path) -> None:
    chart = _chart()
    fingerprint = personal_timeline_fingerprint(
        "abcdef1234567890", chart, _config()
    )
    cache = PersonalTimelineDiskCache(cache_dir=tmp_path)

    path = cache.put("abcdef1234567890", fingerprint, [_window()])
    payloads = cache.get("ABCDEF1234567890", fingerprint)

    assert path.exists()
    assert payloads is not None
    assert len(payloads) == 1
    assert payloads[0]["chart_uid"] == "ABCDEF1234567890"
    assert payloads[0]["transit"]["aspect_name"] == "square"
    assert payloads[0]["end_truncated"] is True
    assert list(tmp_path.glob("*.tmp")) == []


def test_fingerprint_ignores_cosmetic_metadata_but_tracks_transit_inputs() -> None:
    chart = _chart()
    baseline = personal_timeline_fingerprint("ABCDEF1234567890", chart, _config())

    chart.comments = "changed without affecting astronomy"
    assert personal_timeline_fingerprint(
        "ABCDEF1234567890", chart, _config()
    ) == baseline

    chart.positions["Saturn"] = 18.0
    assert personal_timeline_fingerprint(
        "ABCDEF1234567890", chart, _config()
    ) != baseline


def test_fingerprint_tracks_death_bounds_and_generation_config() -> None:
    chart = _chart()
    baseline = personal_timeline_fingerprint("ABCDEF1234567890", chart, _config())

    chart.is_deceased = True
    chart.death_year = 2070
    chart.death_month = 5
    chart.death_day = 6
    assert personal_timeline_fingerprint(
        "ABCDEF1234567890", chart, _config()
    ) != baseline

    chart = _chart()
    changed_config = _config()
    changed_config["scan_step_days"] = 1
    assert personal_timeline_fingerprint(
        "ABCDEF1234567890", chart, changed_config
    ) != baseline


def test_stale_or_malformed_cache_is_a_miss(tmp_path) -> None:
    chart = _chart()
    fingerprint = personal_timeline_fingerprint(
        "ABCDEF1234567890", chart, _config()
    )
    cache = PersonalTimelineDiskCache(cache_dir=tmp_path)
    path = cache.put("ABCDEF1234567890", fingerprint, [_window()])

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema_version"] = PERSONAL_TIMELINE_CACHE_SCHEMA_VERSION + 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert cache.get("ABCDEF1234567890", fingerprint) is None

    path.write_text("{ definitely not json", encoding="utf-8")
    assert cache.get("ABCDEF1234567890", fingerprint) is None


def test_fingerprint_mismatch_does_not_reuse_old_windows(tmp_path) -> None:
    chart = _chart()
    cache = PersonalTimelineDiskCache(cache_dir=tmp_path)
    old_fingerprint = personal_timeline_fingerprint(
        "ABCDEF1234567890", chart, _config()
    )
    cache.put("ABCDEF1234567890", old_fingerprint, [_window()])

    chart.positions["Sun"] = 281.0
    new_fingerprint = personal_timeline_fingerprint(
        "ABCDEF1234567890", chart, _config()
    )

    assert new_fingerprint != old_fingerprint
    assert cache.get("ABCDEF1234567890", new_fingerprint) is None
