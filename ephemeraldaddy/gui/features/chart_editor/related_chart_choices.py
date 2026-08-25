"""UID-first related-chart choices for Chart Editor autocompleters."""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from typing import Iterable


@dataclass(frozen=True, slots=True)
class RelatedChartChoiceRecord:
    """The stable identity and searchable labels for one saved chart."""

    chart_uid: str
    name: str
    alias: str
    from_whence: str = ""
    display_chart_id: int | None = None


def build_related_chart_choice_map(
    records: Iterable[RelatedChartChoiceRecord],
    *,
    current_chart_uid: str | None,
) -> dict[str, str]:
    """Map unambiguous user-facing choices to their stable internal UIDs."""
    excluded_uid = str(current_chart_uid or "").strip().upper()
    eligible = [
        record
        for record in records
        if str(record.chart_uid or "").strip().upper()
        and str(record.chart_uid or "").strip().upper() != excluded_uid
    ]
    label_counts = Counter(
        label.casefold()
        for record in eligible
        for label in (str(record.name or "").strip(), str(record.alias or "").strip())
        if label
    )
    choices: dict[str, str] = {}
    for record in eligible:
        chart_uid = str(record.chart_uid or "").strip().upper()
        name = str(record.name or "").strip()
        alias = str(record.alias or "").strip()
        from_whence = str(record.from_whence or "").strip()
        for label in dict.fromkeys(value for value in (name, alias) if value):
            choice = label
            if label_counts[label.casefold()] > 1:
                qualifiers = [
                    value
                    for value in (alias if label != alias else name, from_whence)
                    if value and value.casefold() != label.casefold()
                ]
                if qualifiers:
                    choice = f"{label} — {'; '.join(qualifiers)}"
                elif record.display_chart_id is not None:
                    choice = f"{label} — Chart ID #{record.display_chart_id}"
                else:
                    # An unavailable Database View rank must not cause the wrong
                    # duplicate chart to be selected silently.
                    continue
            choices.setdefault(choice, chart_uid)
    return choices


def build_related_chart_choices(
    records: Iterable[RelatedChartChoiceRecord],
    *,
    current_chart_uid: str | None,
) -> list[str]:
    """Return unambiguous user-facing labels for another chart."""
    return list(
        build_related_chart_choice_map(
            records,
            current_chart_uid=current_chart_uid,
        )
    )
