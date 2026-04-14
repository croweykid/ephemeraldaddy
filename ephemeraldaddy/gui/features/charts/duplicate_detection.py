"""Helpers for detecting and tiering possible duplicate charts in Database View."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from typing import Callable, Literal

from ephemeraldaddy.analysis.get_astro_twin import chart_similarity_score
from ephemeraldaddy.core.chart import Chart

DuplicateLikelihood = Literal[
    "definite",
    "likely",
    "probable_name",
    "mid_birth_date",
    "suspected",
]

LIKELIHOOD_SORT_WEIGHT: dict[DuplicateLikelihood, int] = {
    "definite": 0,
    "likely": 1,
    "probable_name": 1,
    "mid_birth_date": 2,
    "suspected": 3,
}


@dataclass(frozen=True)
class DuplicateDetectionResult:
    duplicate_ids: set[int]
    related_names: dict[int, dict[str, list[str]]]
    likelihood_by_chart_id: dict[int, DuplicateLikelihood]
    duplicate_sort_key_by_chart_id: dict[int, tuple[int, int, str]]
    duplicate_group_by_chart_id: dict[int, int]


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
    similarity_threshold_percent: float = 65.0,
    similarity_ceiling_percent: float = 100.0,
    excluded_pairs: set[tuple[int, int]] | None = None,
) -> DuplicateDetectionResult:
    duplicate_ids: set[int] = set()
    related_names: dict[int, dict[str, set[str]]] = {}
    chart_names: dict[int, str] = {}

    birthday_groups: dict[tuple[int, int, int], list[int]] = {}
    normalized_name_to_ids: dict[str, set[int]] = {}
    placeholder_ids: set[int] = set()
    chart_links: dict[int, set[int]] = {}
    likelihood_by_chart_id: dict[int, DuplicateLikelihood] = {}
    excluded = excluded_pairs or set()

    def canonical_pair(left_id: int, right_id: int) -> tuple[int, int]:
        left = int(left_id)
        right = int(right_id)
        return (left, right) if left < right else (right, left)

    def attach_likelihood(chart_id: int, likelihood: DuplicateLikelihood) -> None:
        current = likelihood_by_chart_id.get(chart_id)
        if current is None or LIKELIHOOD_SORT_WEIGHT[likelihood] < LIKELIHOOD_SORT_WEIGHT[current]:
            likelihood_by_chart_id[chart_id] = likelihood

    def connect_pair(left_id: int, right_id: int) -> None:
        if left_id == right_id:
            return
        if canonical_pair(left_id, right_id) in excluded:
            return
        chart_links.setdefault(left_id, set()).add(right_id)
        chart_links.setdefault(right_id, set()).add(left_id)

    for row in rows:
        chart_id = int(row[0])
        name = row[1]
        alias = row[2]
        birth_month = row[17]
        birth_day = row[18]
        birth_year = row[19]
        is_placeholder = bool(row[15]) if len(row) > 15 else False
        if is_placeholder:
            placeholder_ids.add(chart_id)
        chart_names[chart_id] = _display_name(chart_id, name, alias)

        if (
            isinstance(birth_year, int)
            and isinstance(birth_month, int)
            and isinstance(birth_day, int)
        ):
            birthday_groups.setdefault((birth_year, birth_month, birth_day), []).append(chart_id)

        normalized_variants = {
            value
            for value in (_normalize_name(name), _normalize_name(alias))
            if value
        }
        for variant in normalized_variants:
            normalized_name_to_ids.setdefault(variant, set()).add(chart_id)

    def mark_related(group_ids: set[int], reason_key: str, likelihood: DuplicateLikelihood) -> None:
        if len(group_ids) < 2:
            return
        duplicate_ids.update(group_ids)
        group_values = sorted(group_ids)
        for i, left_id in enumerate(group_values):
            attach_likelihood(left_id, likelihood)
            for right_id in group_values[i + 1 :]:
                connect_pair(left_id, right_id)
        for chart_id in group_ids:
            related_by_reason = related_names.setdefault(chart_id, {})
            related = related_by_reason.setdefault(reason_key, set())
            for other_id in group_ids:
                if other_id == chart_id:
                    continue
                if canonical_pair(chart_id, other_id) in excluded:
                    continue
                related.add(chart_names.get(other_id, f"Chart #{other_id}"))

    for chart_ids in birthday_groups.values():
        mark_related(set(chart_ids), "birth_date_year", "mid_birth_date")
    for chart_ids in normalized_name_to_ids.values():
        mark_related(set(chart_ids), "name_exact", "probable_name")

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
                mark_related(left_ids.union(right_ids), "name_fuzzy", "suspected")

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
                percent = final_score * 100.0
                if final_score >= 0.999999:
                    reason_key = "chart_similarity_100"
                    likelihood = "definite"
                else:
                    reason_key = "chart_similarity_65_100"
                    likelihood = "likely"
                mark_related({left_id, right_id}, reason_key, likelihood)
                left_related = related_names.setdefault(left_id, {}).setdefault(reason_key, set())
                right_related = related_names.setdefault(right_id, {}).setdefault(reason_key, set())
                left_related.add(f"{chart_names.get(right_id, f'Chart #{right_id}')} ({percent:.1f}%)")
                right_related.add(f"{chart_names.get(left_id, f'Chart #{left_id}')} ({percent:.1f}%)")

    duplicate_ids = set(chart_links.keys())

    component_id_by_chart: dict[int, int] = {}
    component_index = 0
    for chart_id in sorted(duplicate_ids):
        if chart_id in component_id_by_chart:
            continue
        component_index += 1
        stack = [chart_id]
        component_id_by_chart[chart_id] = component_index
        while stack:
            current = stack.pop()
            for neighbor in chart_links.get(current, set()):
                if neighbor in component_id_by_chart:
                    continue
                component_id_by_chart[neighbor] = component_index
                stack.append(neighbor)

    duplicate_sort_key_by_chart_id = {
        chart_id: (
            component_id_by_chart.get(chart_id, 10_000_000),
            LIKELIHOOD_SORT_WEIGHT.get(likelihood_by_chart_id.get(chart_id, "suspected"), 9),
            chart_names.get(chart_id, "").casefold(),
        )
        for chart_id in duplicate_ids
    }

    return DuplicateDetectionResult(
        duplicate_ids=duplicate_ids,
        related_names={
            chart_id: {
                reason_key: sorted(names, key=str.casefold)
                for reason_key, names in grouped_names.items()
                if names
            }
            for chart_id, grouped_names in related_names.items()
            if grouped_names and chart_id in duplicate_ids
        },
        likelihood_by_chart_id={
            chart_id: likelihood
            for chart_id, likelihood in likelihood_by_chart_id.items()
            if chart_id in duplicate_ids
        },
        duplicate_sort_key_by_chart_id=duplicate_sort_key_by_chart_id,
        duplicate_group_by_chart_id=component_id_by_chart,
    )
