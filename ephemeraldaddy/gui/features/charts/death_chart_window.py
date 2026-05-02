from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.io.geocode import LocationLookupError, geocode_location


def show_death_chart_window(parent) -> None:
    if not parent.deceased_checkbox.isChecked():
        return
    month = int(parent.death_month_edit.text()) if parent.death_month_edit.text().isdigit() else None
    day = int(parent.death_day_edit.text()) if parent.death_day_edit.text().isdigit() else None
    year = int(parent.death_year_edit.text()) if parent.death_year_edit.text().isdigit() else None
    place = parent.death_place_edit.text().strip()
    if not (month and day and year and place):
        return
    hour = 12 if parent.death_time_unknown_checkbox.isChecked() else parent.death_time_edit.time().hour()
    minute = 0 if parent.death_time_unknown_checkbox.isChecked() else parent.death_time_edit.time().minute()
    try:
        lat, lon, resolved = geocode_location(place)
    except LocationLookupError:
        lat, lon, resolved = 0.0, 0.0, place
    dt_local = datetime.datetime(year, month, day, hour, minute)
    chart = Chart(f"{parent.name_edit.text().strip() or 'Anonymous'} 💀", dt_local, lat, lon, tz=ZoneInfo("UTC"))

    dialog = QDialog(parent)
    dialog.setWindowTitle("💀 Death Chart")
    dialog.resize(1000, 700)
    layout = QHBoxLayout(dialog)
    left_panel = QVBoxLayout()
    left_panel.addWidget(QLabel("Death chart wheel available in main chart rendering pipeline."))
    left_panel.addStretch(1)
    layout.addLayout(left_panel, 1)

    output = QPlainTextEdit()
    output.setReadOnly(True)
    output.setPlainText(
        f"Name: {chart.name}\nDate: {year:04d}-{month:02d}-{day:02d}\nTime: {hour:02d}:{minute:02d}" +
        (" (Unknown)" if parent.death_time_unknown_checkbox.isChecked() else "") +
        f"\nPlace: {resolved}\n\nPositions:\n" + "\n".join(f"{k}: {v}" for k, v in chart.positions.items())
    )
    layout.addWidget(output, 1)
    dialog.show()
    parent._death_chart_dialog = dialog
