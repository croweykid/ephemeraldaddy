"""Export text builders for Transit View outputs."""

from __future__ import annotations

from ephemeraldaddy.core.chart import Chart


def build_transit_chart_export_text(
    *,
    chart: Chart,
    date_label: str,
    time_label: str,
    location_label: str,
    chart_data_text: str,
) -> str:
    return "\n".join(
        [
            "🌍Transit Chart",
            f"Name:       {chart.name}",
            f"Date:       {date_label}",
            f"Time:       {time_label}",
            f"Location:   {location_label}, {chart.lat:.4f}, {chart.lon:.4f}",
            "",
            chart_data_text,
        ]
    )
