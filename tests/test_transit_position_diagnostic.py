import datetime
import logging
from types import SimpleNamespace

from ephemeraldaddy.gui.features.transits import diagnostics


def test_saturn_diagnostic_logs_stored_and_fresh_longitudes(caplog):
    chart = SimpleNamespace(
        chart_uid="chart-uid-123",
        name="Boundary Chart",
        dt=datetime.datetime(1990, 1, 1, 12, tzinfo=datetime.timezone.utc),
        positions={"Saturn": 270.0},
        retcon_time_used=False,
    )
    with caplog.at_level(logging.INFO, logger=diagnostics.__name__):
        diagnostics.log_natal_saturn_position_diagnostic(
            chart, longitude_lookup=lambda _dt, _body: 299.77
        )

    assert "chart_uid=chart-uid-123" in caplog.text
    assert "stored_longitude=270.000000" in caplog.text
    assert "fresh_longitude=299.770000" in caplog.text
    assert "difference_degrees=29.770000" in caplog.text
    assert "cache_mismatch=True" in caplog.text


def test_saturn_diagnostic_uses_rectified_time(caplog):
    chart = SimpleNamespace(
        chart_uid="chart-uid-456",
        name="Rectified Chart",
        dt=datetime.datetime(1990, 1, 1, 12, 34, tzinfo=datetime.timezone.utc),
        positions={"Saturn": 299.77},
        retcon_time_used=True,
        retcon_hour=8,
        retcon_minute=15,
    )
    observed = {}

    def fake_longitude(moment, body):
        observed["moment"] = moment
        observed["body"] = body
        return 299.77

    with caplog.at_level(logging.INFO, logger=diagnostics.__name__):
        diagnostics.log_natal_saturn_position_diagnostic(
            chart, longitude_lookup=fake_longitude
        )

    assert observed == {
        "moment": datetime.datetime(1990, 1, 1, 8, 15, tzinfo=datetime.timezone.utc),
        "body": "Saturn",
    }
    assert "cache_mismatch=False" in caplog.text
