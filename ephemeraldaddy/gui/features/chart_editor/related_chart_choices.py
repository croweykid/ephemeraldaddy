"""UID-first related-chart choices for Chart Editor autocompleters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class RelatedChartChoiceRecord:
    """The stable identity and searchable labels for one saved chart."""

    chart_uid: str
    name: str
    alias: str


def build_related_chart_choices(
    records: Iterable[RelatedChartChoiceRecord],
    *,
    current_chart_uid: str | None,
) -> list[str]:
    """Return deduplicated name, alias, and UID choices for another chart."""
    excluded_uid = str(current_chart_uid or "").strip().upper()
    choices: list[str] = []
    seen: set[str] = set()
    for record in records:
        chart_uid = str(record.chart_uid or "").strip().upper()
        if not chart_uid or chart_uid == excluded_uid:
            continue
        for raw_choice in (record.name, record.alias, chart_uid):
            choice = str(raw_choice or "").strip()
            key = choice.casefold()
            if choice and key not in seen:
                choices.append(choice)
                seen.add(key)
    return choices
