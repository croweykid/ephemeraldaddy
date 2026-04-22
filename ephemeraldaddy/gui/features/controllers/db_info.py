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
from ephemeraldaddy.gui.style import similarity_gradient_rgb_for_range


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    red, green, blue = rgb
    return f"#{int(red):02x}{int(green):02x}{int(blue):02x}"


def _value_color_for_range(value: float, minimum: float, maximum: float) -> str:
    return _rgb_to_hex(similarity_gradient_rgb_for_range(float(value), float(minimum), float(maximum)))


def _format_database_weight_summary_html(
    *,
    title: str,
    key_order: list[str],
    values_by_key: dict[str, list[float]],
    totals: list[float],
    chart_ranges: list[float],
) -> str:
    if not key_order:
        return f"<b>{html.escape(title)}</b><br><i>No values available.</i>"
    rows: list[str] = [f"<b>{html.escape(title)}</b>"]
    avg_by_key: dict[str, float] = {}
    median_by_key: dict[str, float] = {}
    for key in key_order:
        numeric_values = [float(value) for value in values_by_key.get(key, [])]
        if not numeric_values:
            continue
        avg_by_key[key] = statistics.fmean(numeric_values)
        median_by_key[key] = statistics.median(numeric_values)

    if not avg_by_key:
        rows.append("<i>No values available.</i>")
        return "<br>".join(rows)

    avg_min = min(avg_by_key.values())
    avg_max = max(avg_by_key.values())
    median_min = min(median_by_key.values())
    median_max = max(median_by_key.values())

    for key in key_order:
        if key not in avg_by_key:
            continue
        avg_value = avg_by_key[key]
        median_value = median_by_key[key]
        avg_color = _value_color_for_range(avg_value, avg_min, avg_max)
        median_color = _value_color_for_range(median_value, median_min, median_max)
        rows.append(
            f"<b>{html.escape(str(key))}:</b> "
            f"avg <span style=\"color: {avg_color};\">{avg_value:.2f}</span>, "
            f"median <span style=\"color: {median_color};\">{median_value:.2f}</span>"
        )
    if totals:
        total_avg = statistics.fmean(totals)
        total_median = statistics.median(totals)
        total_min = min(totals)
        total_max = max(totals)
        total_avg_color = _value_color_for_range(total_avg, total_min, total_max)
        total_median_color = _value_color_for_range(total_median, total_min, total_max)
        rows.append(
            "Totals: "
            f"avg <span style=\"color: {total_avg_color};\">{total_avg:.2f}</span>, "
            f"median <span style=\"color: {total_median_color};\">{total_median:.2f}</span>"
        )
    if chart_ranges:
        range_avg = statistics.fmean(chart_ranges)
        range_median = statistics.median(chart_ranges)
        range_min = min(chart_ranges)
        range_max = max(chart_ranges)
        range_avg_color = _value_color_for_range(range_avg, range_min, range_max)
        range_median_color = _value_color_for_range(range_median, range_min, range_max)
        rows.append(
            "Range: "
            f"avg <span style=\"color: {range_avg_color};\">{range_avg:.2f}</span>, "
            f"median <span style=\"color: {range_median_color};\">{range_median:.2f}</span>"
        )
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
    body_chart_averages: list[float] = []
    body_chart_medians: list[float] = []
    body_chart_ranges: list[float] = []
    sign_chart_averages: list[float] = []
    sign_chart_medians: list[float] = []
    sign_chart_ranges: list[float] = []
    house_chart_averages: list[float] = []
    house_chart_medians: list[float] = []
    house_chart_ranges: list[float] = []

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

        body_values = [float(value) for value in body_weights.values()]
        sign_values = [float(sign_weights.get(sign, 0.0)) for sign in ZODIAC_NAMES]
        house_values = [float(house_weights.get(house_num, 0.0)) for house_num in range(1, 13)]
        if body_values:
            body_chart_averages.append(statistics.fmean(body_values))
            body_chart_medians.append(statistics.median(body_values))
            body_chart_ranges.append(max(body_values) - min(body_values))
        if sign_values:
            sign_chart_averages.append(statistics.fmean(sign_values))
            sign_chart_medians.append(statistics.median(sign_values))
            sign_chart_ranges.append(max(sign_values) - min(sign_values))
        if house_values:
            house_chart_averages.append(statistics.fmean(house_values))
            house_chart_medians.append(statistics.median(house_values))
            house_chart_ranges.append(max(house_values) - min(house_values))

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
        "chart_distribution_norms": {
            "bodies": {
                "avg": body_chart_averages,
                "median": body_chart_medians,
                "range": body_chart_ranges,
                "total": body_totals,
            },
            "signs": {
                "avg": sign_chart_averages,
                "median": sign_chart_medians,
                "range": sign_chart_ranges,
                "total": sign_totals,
            },
            "houses": {
                "avg": house_chart_averages,
                "median": house_chart_medians,
                "range": house_chart_ranges,
                "total": house_totals,
            },
        },
    }

    body_html = _format_database_weight_summary_html(
        title="Body Weights",
        key_order=body_keys,
        values_by_key=body_values_by_key,
        totals=body_totals,
        chart_ranges=body_chart_ranges,
    )
    sign_html = _format_database_weight_summary_html(
        title="Sign Weights",
        key_order=list(ZODIAC_NAMES),
        values_by_key=sign_values_by_key,
        totals=sign_totals,
        chart_ranges=sign_chart_ranges,
    )
    house_html = _format_database_weight_summary_html(
        title="House Weights",
        key_order=[str(house_num) for house_num in range(1, 13)],
        values_by_key=house_values_by_key,
        totals=house_totals,
        chart_ranges=house_chart_ranges,
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
