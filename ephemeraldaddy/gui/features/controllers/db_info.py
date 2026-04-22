"""Settings helpers for database-level dominant weight summaries."""

from __future__ import annotations

import html
import json
import statistics
from datetime import date
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QToolButton

from ephemeraldaddy.core.interpretations import ZODIAC_NAMES
from ephemeraldaddy.gui.features.charts.collections import (
    DEFAULT_COLLECTION_ALL,
    DEFAULT_COLLECTION_PARASOCIAL,
    DEFAULT_COLLECTION_PERSONAL,
    DEFAULT_COLLECTION_PUBLIC,
    chart_belongs_to_collection,
)
from ephemeraldaddy.gui.features.charts.exporters import get_text_export_path
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_house_weights,
    calculate_dominant_planet_weights,
    calculate_dominant_sign_weights,
)
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR, similarity_gradient_rgb_for_range

_DB_INFO_CACHE_KEY = "settings/database_info/cache_v2"
_DB_INFO_EXPORT_EXTENSION_KEY = "settings/database_info/export_extension"
_DB_INFO_MAX_ADDED_CHARTS = 45
_DB_INFO_COLLECTION_OPTIONS: tuple[tuple[str, str], ...] = (
    ("All", DEFAULT_COLLECTION_ALL),
    ("Personal", DEFAULT_COLLECTION_PERSONAL),
    ("Parasocial", DEFAULT_COLLECTION_PARASOCIAL),
    ("Public", DEFAULT_COLLECTION_PUBLIC),
)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    red, green, blue = rgb
    return f"#{int(red):02x}{int(green):02x}{int(blue):02x}"


def _value_color_for_range(value: float, minimum: float, maximum: float) -> str:
    return _rgb_to_hex(similarity_gradient_rgb_for_range(float(value), float(minimum), float(maximum)))


def _highlight_label(label: str) -> str:
    return (
        f"<span style=\"font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};\">"
        f"{html.escape(label)}</span>"
    )


def _format_database_weight_summary_html(
    *,
    title: str,
    key_order: list[str],
    values_by_key: dict[str, list[float]],
    totals: list[float],
    chart_ranges: list[float],
) -> str:
    if not key_order:
        return f"{_highlight_label(title)}<br><i>No values available.</i>"

    rows: list[str] = [_highlight_label(title)]
    avg_by_key: dict[str, float] = {}
    med_by_key: dict[str, float] = {}
    for key in key_order:
        numeric_values = [float(value) for value in values_by_key.get(key, [])]
        if not numeric_values:
            continue
        avg_by_key[key] = statistics.fmean(numeric_values)
        med_by_key[key] = statistics.median(numeric_values)

    if not avg_by_key:
        rows.append("<i>No values available.</i>")
        return "<br>".join(rows)

    avg_min = min(avg_by_key.values())
    avg_max = max(avg_by_key.values())
    med_min = min(med_by_key.values())
    med_max = max(med_by_key.values())

    for key in key_order:
        if key not in avg_by_key:
            continue
        avg_value = avg_by_key[key]
        med_value = med_by_key[key]
        avg_color = _value_color_for_range(avg_value, avg_min, avg_max)
        med_color = _value_color_for_range(med_value, med_min, med_max)
        rows.append(
            f"{_highlight_label(f'{key}:')} "
            f"{_highlight_label('avg')} <span style=\"color: {avg_color};\">{avg_value:.2f}</span>, "
            f"{_highlight_label('med')} <span style=\"color: {med_color};\">{med_value:.2f}</span>"
        )

    if totals:
        total_avg = statistics.fmean(totals)
        total_med = statistics.median(totals)
        total_min = min(totals)
        total_max = max(totals)
        total_avg_color = _value_color_for_range(total_avg, total_min, total_max)
        total_med_color = _value_color_for_range(total_med, total_min, total_max)
        rows.append(
            f"{_highlight_label('Totals:')} "
            f"{_highlight_label('avg')} <span style=\"color: {total_avg_color};\">{total_avg:.2f}</span>, "
            f"{_highlight_label('med')} <span style=\"color: {total_med_color};\">{total_med:.2f}</span>"
        )

    if chart_ranges:
        range_avg = statistics.fmean(chart_ranges)
        range_med = statistics.median(chart_ranges)
        range_min = min(chart_ranges)
        range_max = max(chart_ranges)
        range_avg_color = _value_color_for_range(range_avg, range_min, range_max)
        range_med_color = _value_color_for_range(range_med, range_min, range_max)
        rows.append(
            f"{_highlight_label('Range:')} "
            f"{_highlight_label('avg')} <span style=\"color: {range_avg_color};\">{range_avg:.2f}</span>, "
            f"{_highlight_label('med')} <span style=\"color: {range_med_color};\">{range_med:.2f}</span>"
        )
    return "<br>".join(rows)


def _normalize_chart_ids(owner: Any) -> list[int]:
    chart_ids: list[int] = []
    for row in getattr(owner, "_chart_rows", []):
        normalized = owner._normalize_chart_row(row)
        if normalized is None:
            continue
        chart_ids.append(int(normalized[0]))
    return chart_ids


def _normalized_collection_from_ui(owner: Any) -> str:
    combo = getattr(owner, "_settings_db_info_collection_combo", None)
    if combo is None:
        return DEFAULT_COLLECTION_ALL
    value = combo.currentData()
    return str(value or DEFAULT_COLLECTION_ALL)


def _iter_filtered_non_placeholder_charts(owner: Any, *, collection_id: str):
    for chart_id in _normalize_chart_ids(owner):
        chart = owner._get_chart_for_filter(chart_id)
        if chart is None or getattr(chart, "is_placeholder", False):
            continue
        if not chart_belongs_to_collection(
            collection_id,
            chart=chart,
            source=getattr(chart, "source", None),
            custom_collections=getattr(owner, "_custom_collections", {}),
            chart_id=chart_id,
        ):
            continue
        yield chart


def _non_placeholder_chart_count(owner: Any) -> int:
    count = 0
    for chart_id in _normalize_chart_ids(owner):
        chart = owner._get_chart_for_filter(chart_id)
        if chart is None or getattr(chart, "is_placeholder", False):
            continue
        count += 1
    return count


def _save_database_info_cache(owner: Any, payload: dict[str, Any]) -> None:
    settings = getattr(owner, "_settings", None)
    if settings is None:
        return
    settings.setValue(_DB_INFO_CACHE_KEY, json.dumps(payload))


def _load_database_info_cache(owner: Any) -> dict[str, Any] | None:
    settings = getattr(owner, "_settings", None)
    if settings is None:
        return None
    raw_payload = settings.value(_DB_INFO_CACHE_KEY, "")
    if not raw_payload:
        return None
    try:
        parsed = json.loads(str(raw_payload))
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def _current_default_export_stem() -> str:
    return f"ephemeraldaddy-db_info-{date.today().isoformat()}"


def _export_database_info(owner: Any) -> None:
    rendered = getattr(owner, "_settings_db_info_rendered", None)
    if not isinstance(rendered, dict):
        return

    settings = getattr(owner, "_settings", None)
    if settings is None:
        return

    file_path = get_text_export_path(
        owner,
        settings,
        dialog_title="Export Database Info",
        default_stem=_current_default_export_stem(),
        preference_key=_DB_INFO_EXPORT_EXTENSION_KEY,
        default_extension=".txt",
    )
    if not file_path:
        return

    selected_collection_label = rendered.get("collection_label", "All")
    lines = [
        f"Database Info ({selected_collection_label})",
        "",
        f"Charts Assessed: {int(rendered.get('charts_assessed', 0))}",
        "",
    ]
    for section in ("body", "sign", "house"):
        section_lines = rendered.get(section, [])
        if section_lines:
            lines.extend(section_lines)
            lines.append("")

    suffix = Path(file_path).suffix.lower()
    if suffix == ".md":
        markdown_lines: list[str] = [f"# Database Info ({selected_collection_label})", ""]
        markdown_lines.append(f"*Charts Assessed: {int(rendered.get('charts_assessed', 0))}*")
        markdown_lines.append("")
        for section in ("body", "sign", "house"):
            section_lines = rendered.get(section, [])
            if not section_lines:
                continue
            markdown_lines.append(f"## {section_lines[0]}")
            for line in section_lines[1:]:
                markdown_lines.append(f"- {line}")
            markdown_lines.append("")
        output_text = "\n".join(markdown_lines).rstrip() + "\n"
    else:
        output_text = "\n".join(lines).rstrip() + "\n"

    with open(file_path, "w", encoding="utf-8") as handle:
        handle.write(output_text)


def refresh_database_info(owner: Any, *, force_recompute: bool = False) -> None:
    output_label = getattr(owner, "_settings_db_info_label", None)
    if output_label is None:
        return

    active_collection_id = _normalized_collection_from_ui(owner)
    active_collection_label = next(
        (label for label, value in _DB_INFO_COLLECTION_OPTIONS if value == active_collection_id),
        "All",
    )

    total_non_placeholder = _non_placeholder_chart_count(owner)
    cached = _load_database_info_cache(owner)
    if (
        (not force_recompute)
        and isinstance(cached, dict)
        and isinstance(cached.get("rendered_html_by_collection"), dict)
    ):
        baseline_count = int(cached.get("baseline_non_placeholder_count", 0))
        if (total_non_placeholder - baseline_count) < _DB_INFO_MAX_ADDED_CHARTS:
            cached_html = str(cached["rendered_html_by_collection"].get(active_collection_id, "")).strip()
            cached_rendered = cached.get("rendered_export_data_by_collection", {}).get(active_collection_id)
            if cached_html:
                output_label.setText(cached_html)
                if isinstance(cached_rendered, dict):
                    owner._settings_db_info_rendered = cached_rendered
                return

    body_keys: list[str] = []
    body_values_by_key: dict[str, list[float]] = {}
    sign_values_by_key: dict[str, list[float]] = {sign: [] for sign in ZODIAC_NAMES}
    house_values_by_key: dict[str, list[float]] = {str(house_num): [] for house_num in range(1, 13)}
    body_totals: list[float] = []
    sign_totals: list[float] = []
    house_totals: list[float] = []
    body_chart_ranges: list[float] = []
    sign_chart_ranges: list[float] = []
    house_chart_ranges: list[float] = []
    charts_assessed_count = 0

    for chart in _iter_filtered_non_placeholder_charts(owner, collection_id=active_collection_id):
        charts_assessed_count += 1
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
            body_chart_ranges.append(max(body_values) - min(body_values))
        if sign_values:
            sign_chart_ranges.append(max(sign_values) - min(sign_values))
        if house_values:
            house_chart_ranges.append(max(house_values) - min(house_values))

    if not body_totals and not sign_totals and not house_totals:
        output_label.setText("No non-placeholder charts were available for analysis in this collection.")
        return

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
    charts_assessed_html = f"{_highlight_label('Charts Assessed:')} {charts_assessed_count}"
    divider_html = f"<hr style='border:0;border-top:1px solid {CHART_DATA_HIGHLIGHT_COLOR};'>"
    rendered_html = f"{charts_assessed_html}<br>{divider_html}{body_html}<br><br>{sign_html}<br><br>{house_html}"
    output_label.setText(rendered_html)

    body_text = ["Body Weights"]
    for key in body_keys:
        values = [float(value) for value in body_values_by_key.get(key, [])]
        if not values:
            continue
        body_text.append(f"{key}: avg {statistics.fmean(values):.2f}, med {statistics.median(values):.2f}")
    body_text.append(f"Totals: avg {statistics.fmean(body_totals):.2f}, med {statistics.median(body_totals):.2f}")
    body_text.append(
        f"Range: avg {statistics.fmean(body_chart_ranges):.2f}, med {statistics.median(body_chart_ranges):.2f}"
    )

    sign_text = ["Sign Weights"]
    for key in ZODIAC_NAMES:
        values = [float(value) for value in sign_values_by_key.get(key, [])]
        if not values:
            continue
        sign_text.append(f"{key}: avg {statistics.fmean(values):.2f}, med {statistics.median(values):.2f}")
    sign_text.append(f"Totals: avg {statistics.fmean(sign_totals):.2f}, med {statistics.median(sign_totals):.2f}")
    sign_text.append(
        f"Range: avg {statistics.fmean(sign_chart_ranges):.2f}, med {statistics.median(sign_chart_ranges):.2f}"
    )

    house_text = ["House Weights"]
    for house_num in range(1, 13):
        key = str(house_num)
        values = [float(value) for value in house_values_by_key.get(key, [])]
        if not values:
            continue
        house_text.append(f"{key}: avg {statistics.fmean(values):.2f}, med {statistics.median(values):.2f}")
    house_text.append(f"Totals: avg {statistics.fmean(house_totals):.2f}, med {statistics.median(house_totals):.2f}")
    house_text.append(
        f"Range: avg {statistics.fmean(house_chart_ranges):.2f}, med {statistics.median(house_chart_ranges):.2f}"
    )

    rendered_export_data = {
        "collection_id": active_collection_id,
        "collection_label": active_collection_label,
        "charts_assessed": charts_assessed_count,
        "body": body_text,
        "sign": sign_text,
        "house": house_text,
    }
    owner._settings_db_info_rendered = rendered_export_data

    merged_html_by_collection: dict[str, str] = {}
    merged_export_by_collection: dict[str, dict[str, Any]] = {}
    if isinstance(cached, dict):
        merged_html_by_collection.update(
            {
                str(key): str(value)
                for key, value in (cached.get("rendered_html_by_collection") or {}).items()
                if isinstance(key, str)
            }
        )
        merged_export_by_collection.update(
            {
                str(key): value
                for key, value in (cached.get("rendered_export_data_by_collection") or {}).items()
                if isinstance(key, str) and isinstance(value, dict)
            }
        )

    if force_recompute:
        merged_html_by_collection = {}
        merged_export_by_collection = {}

    merged_html_by_collection[active_collection_id] = rendered_html
    merged_export_by_collection[active_collection_id] = rendered_export_data
    _save_database_info_cache(
        owner,
        {
            "baseline_non_placeholder_count": total_non_placeholder,
            "rendered_html_by_collection": merged_html_by_collection,
            "rendered_export_data_by_collection": merged_export_by_collection,
        },
    )


def add_database_info_settings_section(owner: Any, content_layout) -> None:
    section_layout = owner._add_settings_collapsible_section(content_layout, "Database Info")

    top_row = QHBoxLayout()
    subheader_label = QLabel(
        "Compute database-level meds/averages for dominant body, sign, and house weights for a selected collection."
    )
    subheader_label.setWordWrap(True)
    subheader_label.setStyleSheet(f"font-style: italic; color: {CHART_DATA_HIGHLIGHT_COLOR};")
    subheader_label.setSizePolicy(subheader_label.sizePolicy().horizontalPolicy(), subheader_label.sizePolicy().verticalPolicy())
    top_row.addWidget(subheader_label, 1)

    export_button = QToolButton()
    share_icon_path = Path(__file__).resolve().parents[3] / "graphics" / "share_icon2.png"
    if share_icon_path.exists():
        export_button.setIcon(QIcon(str(share_icon_path)))
    else:
        export_button.setText("⇪")
    export_button.setToolTip("Export Database Info as TXT or MD")
    export_button.setCursor(Qt.PointingHandCursor)
    export_button.clicked.connect(lambda _checked=False: _export_database_info(owner))
    top_row.addWidget(export_button, 0, Qt.AlignTop | Qt.AlignRight)
    section_layout.addLayout(top_row)

    controls_row = QHBoxLayout()
    collection_combo = QComboBox()
    for label, value in _DB_INFO_COLLECTION_OPTIONS:
        collection_combo.addItem(label, value)
    collection_combo.currentIndexChanged.connect(
        lambda _index: refresh_database_info(owner, force_recompute=False)
    )
    controls_row.addWidget(collection_combo, 0, Qt.AlignLeft)

    refresh_button = QPushButton("Refresh Database Info")
    refresh_button.setToolTip(
        "Recalculate and reset persisted Database Info values for the selected collection."
    )
    refresh_button.clicked.connect(lambda _checked=False: refresh_database_info(owner, force_recompute=True))
    controls_row.addWidget(refresh_button, 0, Qt.AlignLeft)
    controls_row.addStretch(1)
    section_layout.addLayout(controls_row)

    divider = QFrame()
    divider.setFrameShape(QFrame.HLine)
    divider.setFrameShadow(QFrame.Sunken)
    section_layout.addWidget(divider)

    owner._settings_db_info_collection_combo = collection_combo
    owner._settings_db_info_export_button = export_button
    owner._settings_db_info_label = QLabel("No database info computed yet.")
    owner._settings_db_info_label.setWordWrap(True)
    owner._settings_db_info_label.setTextFormat(Qt.RichText)
    section_layout.addWidget(owner._settings_db_info_label)

    refresh_database_info(owner, force_recompute=False)
