import datetime
import logging
from types import SimpleNamespace

from ephemeraldaddy.gui.features.transits import diagnostics


def _chart(**overrides):
    values = {
        "chart_uid": "chart-uid-123",
        "name": "Boundary Chart",
        "dt": datetime.datetime(1990, 1, 1, 12, tzinfo=datetime.timezone.utc),
        "positions": {"Saturn": 270.0, "Sun": 10.0},
        "retrogrades": {"Saturn": True, "Sun": False},
        "houses": [float(value) for value in range(12)],
        "housesPo": [float(value) for value in range(12)],
        "aspects": [{"p1": "Sun", "p2": "Saturn", "type": "square"}],
        "retcon_time_used": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_derived_cache_diagnostic_logs_every_field_side_by_side_and_refreshes_chart(caplog):
    chart = _chart()
    fresh = {
        "positions": {"Saturn": 299.77, "Sun": 10.0, "Moon": 20.0},
        "retrogrades": {"Saturn": False, "Sun": False},
        "houses": chart.houses,
        "housesPo": [99.0, *chart.housesPo[1:]],
        "aspects": chart.aspects,
    }

    with caplog.at_level(logging.INFO, logger=diagnostics.__name__):
        diagnostics.log_natal_derived_cache_diagnostic(
            chart, snapshot_builder=lambda _chart: fresh
        )

    assert "field=positions key=Saturn stored=270.0 fresh=299.77" in caplog.text
    assert "field=positions key=Moon stored=None fresh=20.0" in caplog.text
    assert "field=retrogrades key=Saturn stored=True fresh=False" in caplog.text
    assert "field=houses stored=" in caplog.text
    assert "field=housesPo stored=" in caplog.text
    assert "field=aspects stored=" in caplog.text
    assert "mismatch_counts={'positions': 2, 'retrogrades': 1, 'houses': 0, 'housesPo': 1, 'aspects': 0}" in caplog.text
    assert "cache_mismatch=True" in caplog.text
    assert "refreshed_for_calculation=True" in caplog.text

    # Regression: the stale cache must not remain authoritative after the check.
    assert chart.positions == fresh["positions"]
    assert chart.retrogrades == fresh["retrogrades"]
    assert chart.housesPo == fresh["housesPo"]


def test_derived_cache_diagnostic_uses_rectified_time(caplog):
    chart = _chart(retcon_time_used=True, retcon_hour=8, retcon_minute=15)
    observed = {}

    def snapshot_builder(received_chart):
        observed["chart"] = received_chart
        return {
            field: getattr(received_chart, field) for field in diagnostics.DERIVED_FIELDS
        }

    with caplog.at_level(logging.INFO, logger=diagnostics.__name__):
        diagnostics.log_natal_derived_cache_diagnostic(
            chart, snapshot_builder=snapshot_builder
        )

    assert observed["chart"] is chart
    assert "effective_datetime=1990-01-01T08:15:00+00:00" in caplog.text
    assert "cache_mismatch=False" in caplog.text
    assert "refreshed_for_calculation=True" in caplog.text


def test_refresh_natal_derived_state_replaces_stale_values():
    chart = _chart()
    fresh = {
        "positions": {"Sun": 29.0, "Saturn": 270.0},
        "retrogrades": {"Sun": False, "Saturn": False},
        "houses": [10.0] * 12,
        "housesPo": [20.0] * 12,
        "aspects": [{"p1": "Sun", "p2": "Saturn", "type": "trine"}],
    }

    returned = diagnostics.refresh_natal_derived_state(
        chart,
        snapshot_builder=lambda _chart: fresh,
    )

    assert returned == fresh
    assert chart.positions == fresh["positions"]
    assert chart.retrogrades == fresh["retrogrades"]
    assert chart.houses == fresh["houses"]
    assert chart.housesPo == fresh["housesPo"]
    assert chart.aspects == fresh["aspects"]
