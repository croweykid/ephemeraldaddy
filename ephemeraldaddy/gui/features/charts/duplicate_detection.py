"""Helpers for detecting possible duplicate charts in Database View."""

from __future__ import annotations

from difflib import SequenceMatcher
import re
from typing import Callable

from ephemeraldaddy.analysis.get_astro_twin import chart_similarity_score
from ephemeraldaddy.core.chart import Chart

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
    *,
    load_chart: Callable[[int], Chart | None] | None = None,
    similarity_threshold_percent: float = 90.0,
    similarity_ceiling_percent: float = 100.0,
) -> tuple[set[int], dict[int, dict[str, list[str]]]]:
    duplicate_ids: set[int] = set()
    related_names: dict[int, dict[str, set[str]]] = {}
    chart_names: dict[int, str] = {}

    birthday_groups: dict[tuple[int, int], list[int]] = {}
    normalized_name_to_ids: dict[str, set[int]] = {}
    chart_variants: dict[int, set[str]] = {}
    placeholder_ids: set[int] = set()

    for row in rows:
        chart_id = int(row[0])
        name = row[1]
        alias = row[2]
        birth_month = row[17]
        birth_day = row[18]
        is_placeholder = bool(row[15]) if len(row) > 15 else False
        if is_placeholder:
            placeholder_ids.add(chart_id)
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

    def mark_related(group_ids: set[int], reason_key: str) -> None:
        if len(group_ids) < 2:
            return
        duplicate_ids.update(group_ids)
        for chart_id in group_ids:
            related_by_reason = related_names.setdefault(chart_id, {})
            related = related_by_reason.setdefault(reason_key, set())
            for other_id in group_ids:
                if other_id == chart_id:
                    continue
                related.add(chart_names.get(other_id, f"Chart #{other_id}"))

    for chart_ids in birthday_groups.values():
        mark_related(set(chart_ids), "birth_date")
    for chart_ids in normalized_name_to_ids.values():
        mark_related(set(chart_ids), "name")

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
                mark_related(left_ids.union(right_ids), "name")

    if load_chart is not None and similarity_ceiling_percent >= similarity_threshold_percent:
        min_score = float(similarity_threshold_percent) / 100.0
        max_score = float(similarity_ceiling_percent) / 100.0
        eligible_ids = sorted(
            chart_id
            for chart_id in chart_names
            if chart_id not in placeholder_ids
        )
        loaded_charts: dict[int, Chart | None] = {}

        def get_chart(chart_id: int) -> Chart | None:
            if chart_id not in loaded_charts:
                try:
                    loaded_charts[chart_id] = load_chart(chart_id)
                except Exception:
                    loaded_charts[chart_id] = None
            return loaded_charts[chart_id]

        for index, left_id in enumerate(eligible_ids):
            left_chart = get_chart(left_id)
            if left_chart is None or not getattr(left_chart, "positions", None):
                continue
            for right_id in eligible_ids[index + 1 :]:
                right_chart = get_chart(right_id)
                if right_chart is None or not getattr(right_chart, "positions", None):
                    continue
                final_score, _placement, _aspect, _distribution = chart_similarity_score(left_chart, right_chart)
                if not (min_score <= final_score <= max_score):
                    continue
                duplicate_ids.update({left_id, right_id})
                left_related = related_names.setdefault(left_id, {}).setdefault("chart_similarity_90_100", set())
                right_related = related_names.setdefault(right_id, {}).setdefault("chart_similarity_90_100", set())
                left_related.add(f"{chart_names.get(right_id, f'Chart #{right_id}')} ({final_score * 100.0:.1f}%)")
                right_related.add(f"{chart_names.get(left_id, f'Chart #{left_id}')} ({final_score * 100.0:.1f}%)")

    return duplicate_ids, {
        chart_id: {
            reason_key: sorted(names, key=str.casefold)
            for reason_key, names in grouped_names.items()
            if names
        }
        for chart_id, grouped_names in related_names.items()
        if grouped_names
    }
