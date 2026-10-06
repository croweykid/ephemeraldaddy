from __future__ import annotations

import datetime

from ephemeraldaddy.core.chart import Chart
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
    return chart


def import_rows(rows, *, save=save_chart, backup=create_backup_package) -> tuple[list[str], list[BatchImportRow]]:
    uids, failures = [], []
    selected = [row for row in rows if row.included and row.importable]
    if selected:
        backup(included_component_keys={"charts"})
    for row in rows:
        if not row.included or not row.importable: continue
        try:
            chart = build_chart(row)
            save(chart, birth_place=chart.birth_place, birthtime_unknown=chart.birthtime_unknown, birth_month=chart.dt.month, birth_day=chart.dt.day, birth_year=chart.dt.year, auto_generated=True)
            uids.append(chart.chart_uid)
        except Exception as exc:
            row.blocking_errors.append(f"Chart save failed: {exc}"); row.included = False; failures.append(row)
    return uids, failures
