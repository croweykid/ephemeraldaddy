"""Selection summaries for user-assigned Database View typology metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


MIXED = object()


@dataclass(frozen=True)
class TypologySelection:
    """One value per typology slot, with ``MIXED`` for differing values."""

    enneagram: tuple[object, object]
    tritype: tuple[object, object, object]
    mbti: tuple[object, object, object, object]


def summarize_typology_selection(charts: Iterable[Any]) -> TypologySelection | None:
    """Summarize assigned typology values across the selected charts."""
    selected = tuple(chart for chart in charts if chart is not None)
    if not selected:
        return None
    return TypologySelection(
        enneagram=_summarize_slots(selected, "enneagram_type", 2, _integer_value),
        tritype=_summarize_slots(selected, "tritype", 3, _integer_value),
        mbti=_summarize_slots(selected, "mbti", 4, _mbti_value),
    )


def _summarize_slots(charts, attribute: str, count: int, normalize):
    rows = []
    for chart in charts:
        values = list(getattr(chart, attribute, None) or [])
        rows.append(
            tuple(
                normalize(values[index] if index < len(values) else None)
                for index in range(count)
            )
        )
    return tuple(
        column[0] if all(value == column[0] for value in column[1:]) else MIXED
        for column in zip(*rows)
    )


def _integer_value(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if 1 <= parsed <= 9 else None


def _mbti_value(value: object) -> str | None:
    parsed = str(value or "").strip()
    allowed = {
        "E", "e", "I", "i", "N", "n", "S", "s",
        "T", "t", "F", "f", "J", "j", "P", "p", "x",
    }
    return parsed if parsed in allowed else None
