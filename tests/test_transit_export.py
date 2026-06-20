import datetime as dt

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.gui.features.transits.export import build_transit_chart_export_text


def test_build_transit_chart_export_text():
    chart = Chart("Transit", dt.datetime(2026, 6, 20, tzinfo=dt.timezone.utc), 1.25, 2.5)

    text = build_transit_chart_export_text(
        chart=chart,
        date_label="06.20.2026",
        time_label="12:00",
        location_label="Somewhere",
        chart_data_text="Summary",
    )

    assert "🌍Transit Chart" in text
    assert "Name:       Transit" in text
    assert "Location:   Somewhere, 1.2500, 2.5000" in text
    assert text.endswith("Summary")
