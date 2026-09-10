from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

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
