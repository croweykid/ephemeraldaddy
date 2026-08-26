"""Qt adapter for Chart Editor's UID-first related-chart choices."""

from __future__ import annotations

from PySide6.QtCore import QStringListModel, Qt
from PySide6.QtWidgets import QCompleter, QLineEdit

from ephemeraldaddy.core.db import get_chart_uid_map, list_charts
from ephemeraldaddy.gui.features.chart_editor.related_chart_choices import (
    RelatedChartChoiceRecord,
    build_related_chart_choice_map,
)


def _load_related_chart_choice_records(
    display_chart_ids_by_uid: dict[str, int] | None = None,
) -> list[RelatedChartChoiceRecord]:
    """Convert persistence rows to the UID-first workflow value object."""
    rows = list_charts()
    # Numeric row keys remain confined to this persistence-boundary conversion.
    uid_by_local_row = get_chart_uid_map(row[0] for row in rows)
    return [
        RelatedChartChoiceRecord(
            chart_uid=str(uid_by_local_row.get(int(row[0]), "") or ""),
            name=str(row[1] or ""),
            alias=str(row[2] or ""),
            from_whence=str(row[22] or "") if len(row) > 22 else "",
            display_chart_id=(display_chart_ids_by_uid or {}).get(
                str(uid_by_local_row.get(int(row[0]), "") or "").strip().upper()
            ),
        )
        for row in rows
    ]


def refresh_material_relatives_completer(
    line_edit: QLineEdit | None,
    *,
    current_chart_uid: str | None,
    display_chart_ids_by_uid: dict[str, int] | None = None,
) -> None:
    """Refresh a Relatives field in place from the current saved-chart catalog."""
    if not isinstance(line_edit, QLineEdit):
        return
    records = _load_related_chart_choice_records(display_chart_ids_by_uid)
    choice_uids = build_related_chart_choice_map(
        records,
        current_chart_uid=current_chart_uid,
    )
    choices = list(choice_uids)
    line_edit.setProperty("relatedChartUidByChoice", choice_uids)
    completer = line_edit.completer()
    if not isinstance(completer, QCompleter):
        completer = QCompleter(QStringListModel(choices, line_edit), line_edit)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.popup().setFocusPolicy(Qt.NoFocus)
        line_edit.setCompleter(completer)
        return
    model = completer.model()
    if isinstance(model, QStringListModel):
        model.setStringList(choices)
    else:
        completer.setModel(QStringListModel(choices, completer))
