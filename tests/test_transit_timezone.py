from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

from ephemeraldaddy.gui.features.transits import timezone as transit_timezone
from ephemeraldaddy.gui.features.transits.timezone import local_transit_timezone


def test_local_transit_timezone_prefers_rule_aware_tz_environment(monkeypatch) -> None:
    monkeypatch.setenv("TZ", "America/New_York")

    timezone = local_transit_timezone()

    assert isinstance(timezone, ZoneInfo)
    assert timezone.key == "America/New_York"
    assert datetime.datetime(2026, 1, 10, tzinfo=timezone).utcoffset() == datetime.timedelta(
        hours=-5
    )
    assert datetime.datetime(2026, 9, 10, tzinfo=timezone).utcoffset() == datetime.timedelta(
        hours=-4
    )


def test_local_transit_timezone_maps_qt_windows_id_to_iana(monkeypatch) -> None:
    class FakeQTimeZone:
        @staticmethod
        def systemTimeZoneId() -> bytes:
            return b"Eastern Standard Time"

        @staticmethod
        def windowsIdToDefaultIanaId(windows_id: bytes) -> bytes:
            assert windows_id == b"Eastern Standard Time"
            return b"America/New_York"

    monkeypatch.delenv("TZ", raising=False)
    monkeypatch.setattr(transit_timezone, "QTimeZone", FakeQTimeZone)
    monkeypatch.setattr(transit_timezone.Path, "resolve", lambda _path: _path)
    monkeypatch.setattr(
        transit_timezone.Path,
        "read_text",
        lambda _path, **_kwargs: (_ for _ in ()).throw(OSError()),
    )

    timezone = local_transit_timezone()

    assert isinstance(timezone, ZoneInfo)
    assert timezone.key == "America/New_York"
    assert datetime.datetime(2026, 1, 10, tzinfo=timezone).utcoffset() == datetime.timedelta(
        hours=-5
    )
    assert datetime.datetime(2026, 9, 10, tzinfo=timezone).utcoffset() == datetime.timedelta(
        hours=-4
    )
