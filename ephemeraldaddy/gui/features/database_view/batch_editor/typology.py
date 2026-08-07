"""Pure typology patch construction for Database View batch edits."""

from __future__ import annotations

from typing import Any


TypologyPatch = dict[str, list[int] | list[str]]


def typology_patch_for_chart(
    chart: Any,
    *,
    enneagram_values: tuple[int | None, int | None],
    tritype_values: tuple[int | None, int | None, int | None],
    mbti_values: tuple[str | None, str | None, str | None, str | None],
) -> TypologyPatch:
    """Return a patch preserving every batch field left unspecified."""
    patch: TypologyPatch = {}
    if any(value is not None for value in enneagram_values):
        current = _normalized_int_slots(getattr(chart, "enneagram_type", None), 2)
        patch["enneagram_type"] = [
            value if value is not None else current[index]
            for index, value in enumerate(enneagram_values)
        ]
    if any(value is not None for value in tritype_values):
        current = _normalized_int_slots(getattr(chart, "tritype", None), 3)
        patch["tritype"] = [
            value if value is not None else current[index]
            for index, value in enumerate(tritype_values)
        ]
    if any(value is not None for value in mbti_values):
        current = _normalized_mbti_slots(getattr(chart, "mbti", None))
        patch["mbti"] = [
            value if value is not None else current[index]
            for index, value in enumerate(mbti_values)
        ]
    return patch


def _normalized_int_slots(values: object, size: int) -> list[int]:
    raw_values = list(values or []) if isinstance(values, (list, tuple)) else []
    result: list[int] = []
    for index in range(size):
        try:
            value = int(raw_values[index])
        except (IndexError, TypeError, ValueError):
            value = 0
        result.append(value if 1 <= value <= 9 else 0)
    return result


def _normalized_mbti_slots(values: object) -> list[str]:
    raw_values = list(values or []) if isinstance(values, (list, tuple)) else []
    allowed = (("E", "I"), ("N", "S"), ("T", "F"), ("J", "P"))
    result: list[str] = []
    for index, choices in enumerate(allowed):
        value = str(raw_values[index] if index < len(raw_values) else "?").upper()
        result.append(value if value in choices else "?")
    return result
