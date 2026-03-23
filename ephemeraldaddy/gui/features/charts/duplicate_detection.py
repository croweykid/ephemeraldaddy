"""Helpers for detecting possible duplicate charts in Database View."""

from __future__ import annotations

from difflib import SequenceMatcher
import re


def _normalize_name(value: object) -> str:
    text = str(value or "").strip().casefold()
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", "", text)


def _display_name(chart_id: int, name: object, alias: object) -> str:
    primary = str(name or "").strip()
    secondary = str(alias or "").strip()
    if primary and secondary:
        return f"{primary} ({secondary})"
    if primary:
        return primary
    if secondary:
        return secondary
    return f"Chart #{chart_id}"


def find_possible_duplicate_charts(
    rows: list[
        tuple[
            int,
            str | None,
            str | None,
            str | None,
            str | None,
            str | None,
            str | None,
            int,
            int,
            int,
            int,
            int,
            int | None,
            int,
            str,
            int,
            int,
            int | None,
            int | None,
            int | None,
        ]
    ],
) -> tuple[set[int], dict[int, list[str]]]:
    duplicate_ids: set[int] = set()
    related_names: dict[int, set[str]] = {}
    chart_names: dict[int, str] = {}

    birthday_groups: dict[tuple[int, int], list[int]] = {}
    normalized_name_to_ids: dict[str, set[int]] = {}
    chart_variants: dict[int, set[str]] = {}

    for row in rows:
        chart_id = int(row[0])
        name = row[1]
        alias = row[2]
        birth_month = row[17]
        birth_day = row[18]
        chart_names[chart_id] = _display_name(chart_id, name, alias)

        if isinstance(birth_month, int) and isinstance(birth_day, int):
            birthday_groups.setdefault((birth_month, birth_day), []).append(chart_id)

        normalized_variants = {
            value
            for value in (_normalize_name(name), _normalize_name(alias))
            if value
        }
        if not normalized_variants:
            continue
        chart_variants[chart_id] = normalized_variants
        for variant in normalized_variants:
            normalized_name_to_ids.setdefault(variant, set()).add(chart_id)

    def mark_related(group_ids: set[int]) -> None:
        if len(group_ids) < 2:
            return
        duplicate_ids.update(group_ids)
        for chart_id in group_ids:
            related = related_names.setdefault(chart_id, set())
            for other_id in group_ids:
                if other_id == chart_id:
                    continue
                related.add(chart_names.get(other_id, f"Chart #{other_id}"))

    for chart_ids in birthday_groups.values():
        mark_related(set(chart_ids))
    for chart_ids in normalized_name_to_ids.values():
        mark_related(set(chart_ids))

    variant_values = list(normalized_name_to_ids.keys())
    buckets: dict[str, list[str]] = {}
    for variant in variant_values:
        buckets.setdefault(variant[:1], []).append(variant)

    for variants in buckets.values():
        for index, left_variant in enumerate(variants):
            for right_variant in variants[index + 1 :]:
                if abs(len(left_variant) - len(right_variant)) > 2:
                    continue
                score = SequenceMatcher(None, left_variant, right_variant).ratio()
                if score < 0.88:
                    continue
                left_ids = normalized_name_to_ids.get(left_variant, set())
                right_ids = normalized_name_to_ids.get(right_variant, set())
                mark_related(left_ids.union(right_ids))

    return duplicate_ids, {
        chart_id: sorted(names, key=str.casefold)
        for chart_id, names in related_names.items()
        if names
    }
