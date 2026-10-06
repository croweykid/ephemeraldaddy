from __future__ import annotations

import datetime

from ephemeraldaddy.core.chart import Chart, apply_time_specific_metadata_policy
from ephemeraldaddy.core.chart_types import CHART_TYPE_PUBLIC_DB
from ephemeraldaddy.core.backups import create_backup_package
from ephemeraldaddy.core.db import save_chart
from .models import BatchImportRow


def build_chart(row: BatchImportRow) -> Chart:
    errors = row.validation_errors()
    if errors: raise ValueError(" ".join(errors))
    day = datetime.date.fromisoformat(row.birth_date)
    unknown = not row.birth_time.strip() or row.birth_time.strip().lower() == "unknown"
    clock = datetime.time(12, 0) if unknown else datetime.time.fromisoformat(row.birth_time)
    assert row.place is not None
    chart = Chart(row.name, datetime.datetime.combine(day, clock), row.place.latitude, row.place.longitude, alias=row.alias or None, from_whence=row.from_whence or None)
    chart.birthtime_unknown = unknown; chart.birth_place = row.place.label
    chart.biography = row.biography; chart.comments = row.notes; chart.tags = list(row.tags)
    chart.data_rating = row.data_rating or "blank"; chart.chart_data_source = "; ".join(row.sources)
    chart.auto_generated = True
    chart.chart_type = CHART_TYPE_PUBLIC_DB
    chart.relationship_types = ["public figure"]
    apply_time_specific_metadata_policy(chart)
    from ephemeraldaddy.gui.features.charts.metrics import (
        calculate_dominant_sign_weights, calculate_dominant_planet_weights,
        calculate_dominant_nakshatra_weights, calculate_dominant_element_weights,
    )
    chart.dominant_sign_weights = calculate_dominant_sign_weights(chart)
    chart.dominant_planet_weights = calculate_dominant_planet_weights(chart)
    chart.dominant_nakshatra_weights = calculate_dominant_nakshatra_weights(chart)
    chart.dominant_element_weights = calculate_dominant_element_weights(chart)
    return chart


def import_rows(rows, *, save=save_chart, backup=create_backup_package,
                cancel_event=None, progress=None, on_result=None) -> tuple[list[str], list[BatchImportRow]]:
    uids, failures = [], []
    selected = [row for row in rows if row.included and row.importable]
    if selected and not (cancel_event and cancel_event.is_set()):
        if progress: progress("Backing up charts…")
        backup(included_component_keys={"charts"})
    for index, row in enumerate(selected, 1):
        if cancel_event and cancel_event.is_set(): break
        if progress: progress(f"Importing {index} / {len(selected)} — {row.name}")
        row.save_error = ""
        try:
            chart = build_chart(row)
            # A running save is allowed to finish before cancellation takes effect.
            if cancel_event and cancel_event.is_set(): break
            save(chart, birth_place=chart.birth_place, birthtime_unknown=chart.birthtime_unknown, birth_month=chart.dt.month, birth_day=chart.dt.day, birth_year=chart.dt.year, auto_generated=True, chart_type=CHART_TYPE_PUBLIC_DB)
            row.imported_uid = chart.chart_uid
            row.included = False
            uids.append(chart.chart_uid)
        except Exception as exc:
            row.save_error = f"Chart save failed: {exc}"
            row.included = False
            failures.append(row)
        if on_result: on_result(row)
    return uids, failures
