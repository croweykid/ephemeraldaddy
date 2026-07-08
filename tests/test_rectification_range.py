from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ephemeraldaddy.core.chart as chart_module


def test_rectification_range_midpoint_updates_positions_without_houses(monkeypatch):
    calls = []

    def fake_positions(dt, lat, lon):
        calls.append((dt.hour, dt.minute, lat, lon))
        return {"Sun": dt.hour * 60 + dt.minute}

    monkeypatch.setattr(chart_module, "planetary_positions", fake_positions)
    monkeypatch.setattr(chart_module, "planetary_retrogrades", lambda dt: {})

    chart = SimpleNamespace(
        dt=datetime(2000, 1, 1, 12, 0),
        lat=1.0,
        lon=2.0,
        birthtime_unknown=True,
        retcon_time_used=False,
        rectification_range_used=True,
        rectification_range_start_minute=60,
        rectification_range_end_minute=300,
        positions={},
        houses=[1],
        housesPo=[1],
        aspects=[{"p1": "AS", "p2": "Sun"}],
    )

    chart_module.apply_time_specific_metadata_policy(chart)

    assert calls == [(3, 0, 1.0, 2.0)]
    assert chart.dt.hour == 3
    assert chart.dt.minute == 0
    assert chart.positions == {"Sun": 180}
    assert chart.houses == []
    assert chart.housesPo == []
    assert chart.aspects == []
    assert chart_module.chart_uses_houses(chart) is False


def test_rectification_range_persists_midpoint_without_house_usage(tmp_path, monkeypatch):
    from zoneinfo import ZoneInfo

    import ephemeraldaddy.core.db as db
    from ephemeraldaddy.core.chart import Chart

    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "charts.db")

    chart = Chart(
        "Range Chart",
        datetime(2000, 1, 1, 12, 0),
        41.8781,
        -87.6298,
        tz=ZoneInfo("UTC"),
    )
    chart.birthtime_unknown = True
    chart.retcon_time_used = False
    chart.rectification_range_used = True
    chart.rectification_range_start_minute = 120
    chart.rectification_range_end_minute = 360

    chart_id = db.save_chart(
        chart,
        birth_place="Chicago, IL, USA",
        birthtime_unknown=True,
        retcon_time_used=False,
        rectification_range_used=True,
        rectification_range_start_minute=120,
        rectification_range_end_minute=360,
    )

    loaded = db.load_chart(chart_id)

    assert loaded.dt.hour == 4
    assert loaded.dt.minute == 0
    assert loaded.birthtime_unknown is True
    assert loaded.retcon_time_used is False
    assert loaded.rectification_range_used is True
    assert loaded.rectification_range_start_minute == 120
    assert loaded.rectification_range_end_minute == 360
    assert db.chart_uses_houses(loaded) is False
    assert loaded.houses == []
