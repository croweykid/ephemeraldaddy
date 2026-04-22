"""Settings helpers for database-level dominant weight summaries."""

from __future__ import annotations

import html
import statistics
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton

from ephemeraldaddy.core.interpretations import ZODIAC_NAMES
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_house_weights,
    calculate_dominant_planet_weights,
    calculate_dominant_sign_weights,
)


def _format_database_weight_summary_html(
    *,
    title: str,
    key_order: list[str],
    values_by_key: dict[str, list[float]],
    totals: list[float],
) -> str:
    if not key_order:
        return f"<b>{html.escape(title)}</b><br><i>No values available.</i>"
    rows: list[str] = [f"<b>{html.escape(title)}</b>"]
    for key in key_order:
        numeric_values = [float(value) for value in values_by_key.get(key, [])]
        if not numeric_values:
            continue
        avg_value = statistics.fmean(numeric_values)
        median_value = statistics.median(numeric_values)
        rows.append(
            f"{html.escape(str(key))}: avg {avg_value:.2f}, median {median_value:.2f}"
        )
    if totals:
        total_avg = statistics.fmean(totals)
        total_median = statistics.median(totals)
        rows.append(f"Totals: avg {total_avg:.2f}, median {total_median:.2f}")
    return "<br>".join(rows)


def refresh_database_info(owner: Any) -> None:
    output_label = getattr(owner, "_settings_db_info_label", None)
    if output_label is None:
        return

    chart_ids: list[int] = []
    for row in getattr(owner, "_chart_rows", []):
        normalized = owner._normalize_chart_row(row)
        if normalized is None:
            continue
        chart_ids.append(normalized[0])

    if not chart_ids:
        output_label.setText("No charts available in the database.")
        return

    body_keys: list[str] = []
    body_values_by_key: dict[str, list[float]] = {}
    sign_values_by_key: dict[str, list[float]] = {sign: [] for sign in ZODIAC_NAMES}
    house_values_by_key: dict[str, list[float]] = {str(house_num): [] for house_num in range(1, 13)}
    body_totals: list[float] = []
    sign_totals: list[float] = []
    house_totals: list[float] = []

    for chart_id in chart_ids:
        chart = owner._get_chart_for_filter(chart_id)
        if chart is None or getattr(chart, "is_placeholder", False):
            continue

        body_weights = calculate_dominant_planet_weights(chart)
        sign_weights = getattr(chart, "dominant_sign_weights", None) or calculate_dominant_sign_weights(chart)
        house_weights = calculate_dominant_house_weights(chart)

        for key in body_weights:
            if key not in body_keys:
                body_keys.append(key)
                body_values_by_key.setdefault(key, [])
        for key in body_keys:
            body_values_by_key.setdefault(key, []).append(float(body_weights.get(key, 0.0)))
        for sign in ZODIAC_NAMES:
            sign_values_by_key[sign].append(float(sign_weights.get(sign, 0.0)))
        for house_num in range(1, 13):
            house_values_by_key[str(house_num)].append(float(house_weights.get(house_num, 0.0)))

        body_totals.append(sum(float(value) for value in body_weights.values()))
        sign_totals.append(sum(float(sign_weights.get(sign, 0.0)) for sign in ZODIAC_NAMES))
        house_totals.append(sum(float(house_weights.get(house_num, 0.0)) for house_num in range(1, 13)))

    if not body_totals and not sign_totals and not house_totals:
        output_label.setText("No non-placeholder charts were available for analysis.")
        return

    owner._database_weight_norms = {
        "body_values_by_key": body_values_by_key,
        "sign_values_by_key": sign_values_by_key,
        "house_values_by_key": house_values_by_key,
        "body_totals": body_totals,
        "sign_totals": sign_totals,
        "house_totals": house_totals,
    }

    body_html = _format_database_weight_summary_html(
        title="Body Weights",
        key_order=body_keys,
        values_by_key=body_values_by_key,
        totals=body_totals,
    )
    sign_html = _format_database_weight_summary_html(
        title="Sign Weights",
        key_order=list(ZODIAC_NAMES),
        values_by_key=sign_values_by_key,
        totals=sign_totals,
    )
    house_html = _format_database_weight_summary_html(
        title="House Weights",
        key_order=[str(house_num) for house_num in range(1, 13)],
        values_by_key=house_values_by_key,
        totals=house_totals,
    )
    output_label.setText(f"{body_html}<br><br>{sign_html}<br><br>{house_html}")


def add_database_info_settings_section(owner: Any, content_layout) -> None:
    section_layout = owner._add_settings_collapsible_section(content_layout, "Database Info")
    section_layout.addWidget(
        QLabel("Compute database-level medians/averages for dominant body, sign, and house weights.")
    )

    refresh_button = QPushButton("Refresh Database Info")
    refresh_button.setToolTip(
        "Calculate per-item and per-category total medians/averages across the saved charts."
    )
    refresh_button.clicked.connect(lambda _checked=False: refresh_database_info(owner))
    section_layout.addWidget(refresh_button, alignment=Qt.AlignLeft)

    owner._settings_db_info_label = QLabel("No database info computed yet.")
    owner._settings_db_info_label.setWordWrap(True)
    owner._settings_db_info_label.setTextFormat(Qt.RichText)
    section_layout.addWidget(owner._settings_db_info_label)
