"""Helpers for detecting and tiering possible duplicate charts in Database View."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from typing import Callable, Literal, Mapping, Sequence

from ephemeraldaddy.analysis.get_astro_twin import chart_similarity_score
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.gui.features.charts.provenance import chart_row_is_non_aggregable

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
    duplicate_uids: set[str]
    related_names: dict[str, dict[str, list[str]]]
    likelihood_by_chart_uid: dict[str, DuplicateLikelihood]
    duplicate_sort_key_by_chart_uid: dict[str, tuple[int, int, str]]
    duplicate_group_by_chart_uid: dict[str, int]


@dataclass(frozen=True)
class DuplicateSaveWarning:
    title: str
    message: str


def _normalize_name(value: object) -> str:
    text = str(value or "").strip().casefold()
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", "", text)


def _display_name(chart_uid: str, name: object, alias: object) -> str:
    primary = str(name or "").strip()
    secondary = str(alias or "").strip()
    if primary and secondary:
        return f"{primary} ({secondary})"
    if primary:
        return primary
    if secondary:
        return secondary
    return f"UID {chart_uid}"


def _display_warning_name(chart_uid: str, name: object, alias: object) -> str:
    display_name = _display_name(chart_uid, name, alias)
    if display_name == f"UID {chart_uid}":
        return display_name
    return f"UID {chart_uid}: {display_name}"


def _append_duplicate_warning_section(
    lines: list[str],
    heading: str,
    matches: list[str],
    *,
    preview_limit: int = 12,
) -> None:
    if not matches:
        return
    lines.extend([heading, ""])
    preview_names = matches[:preview_limit]
    extra_count = max(0, len(matches) - len(preview_names))
    lines.extend(f"• {name}" for name in preview_names)
    if extra_count:
        lines.append(f"• ...and {extra_count} more")
    lines.append("")


def _chart_birth_components(chart: Chart) -> tuple[int | None, int | None, int | None]:
    month = getattr(chart, "birth_month", None)
    day = getattr(chart, "birth_day", None)
    year = getattr(chart, "birth_year", None)
    is_placeholder = bool(getattr(chart, "is_placeholder", False))
    if (month is None or day is None or year is None) and not is_placeholder:
        dt = getattr(chart, "dt", None)
        month = month if month is not None else getattr(dt, "month", None)
        day = day if day is not None else getattr(dt, "day", None)
        year = year if year is not None else getattr(dt, "year", None)
    return (
        int(month) if month is not None else None,
        int(day) if day is not None else None,
        int(year) if year is not None else None,
    )


def build_duplicate_save_warning(
    chart: Chart,
    rows: Sequence[Sequence[object]],
    chart_uids_by_local_row: Mapping[int, str],
) -> DuplicateSaveWarning | None:
    """Build duplicate-warning dialog text for a chart before saving."""
    month, day, year = _chart_birth_components(chart)
    proposed_tokens = {
        token
        for token in (
            _normalize_name(getattr(chart, "name", "")),
            _normalize_name(getattr(chart, "alias", "")),
        )
        if token
    }

    exact_birth_date_matches: list[str] = []
    birthday_matches: list[str] = []
    name_or_alias_matches: list[str] = []
    matched_name_uids: set[str] = set()

    for row in rows:
        local_row_id = int(row[0])
        chart_uid = chart_uids_by_local_row.get(local_row_id)
        if not chart_uid:
            continue
        existing_name = row[1] if len(row) > 1 else ""
        existing_alias = row[2] if len(row) > 2 else ""
        display_name = _display_warning_name(chart_uid, existing_name, existing_alias)
        existing_month = row[17] if len(row) > 17 else None
        existing_day = row[18] if len(row) > 18 else None
        existing_year = row[19] if len(row) > 19 else None

        if month is not None and day is not None:
            if existing_month == month and existing_day == day:
                if year is not None and existing_year == year:
                    exact_birth_date_matches.append(display_name)
                else:
                    birthday_matches.append(display_name)

        if proposed_tokens:
            existing_tokens = {
                token
                for token in (
                    _normalize_name(existing_name),
                    _normalize_name(existing_alias),
                )
                if token
            }
            if proposed_tokens.intersection(existing_tokens):
                if chart_uid not in matched_name_uids:
                    name_or_alias_matches.append(display_name)
                    matched_name_uids.add(chart_uid)

    if not exact_birth_date_matches and not birthday_matches and not name_or_alias_matches:
        return None

    lines = [
        "This chart looks like it may already exist in your database.",
        "",
    ]
    if month is not None and day is not None and year is not None:
        _append_duplicate_warning_section(
            lines,
            (
                f"Same birth date ({year:04d}-{month:02d}-{day:02d}): "
                f"{len(exact_birth_date_matches)} chart(s)"
            ),
            exact_birth_date_matches,
        )
    _append_duplicate_warning_section(
        lines,
        (
            f"Same birthday ({month:02d}/{day:02d}): "
            f"{len(birthday_matches)} chart(s)"
        )
        if month is not None and day is not None
        else "Same birthday:",
        birthday_matches,
    )
    _append_duplicate_warning_section(
        lines,
        f"Same name or alias: {len(name_or_alias_matches)} chart(s)",
        name_or_alias_matches,
    )
    lines.append("Continue and save this chart anyway?")

    return DuplicateSaveWarning(
        title="Possible duplicate chart",
        message="\n".join(lines),
    )


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
    chart_uids_by_local_row: Mapping[int, str],
    load_chart_by_uid: Callable[[str], Chart | None] | None = None,
    similarity_threshold_percent: float = 65.0,
    similarity_ceiling_percent: float = 100.0,
    excluded_pairs: set[tuple[str, str]] | None = None,
) -> DuplicateDetectionResult:
    duplicate_uids: set[str] = set()
    related_names: dict[str, dict[str, set[str]]] = {}
    chart_names: dict[str, str] = {}

    birthday_groups: dict[tuple[int, int, int], list[str]] = {}
    normalized_name_to_uids: dict[str, set[str]] = {}
    placeholder_uids: set[str] = set()
    chart_links: dict[str, set[str]] = {}
    likelihood_by_chart_uid: dict[str, DuplicateLikelihood] = {}
    raw_excluded_pairs = excluded_pairs or set()

    def canonical_pair(left_uid: str, right_uid: str) -> tuple[str, str]:
        left = left_uid
        right = right_uid
        return (left, right) if left < right else (right, left)

    excluded = {
        canonical_pair(left_uid, right_uid)
        for left_uid, right_uid in raw_excluded_pairs
        if left_uid != right_uid
    }

    def attach_likelihood(chart_uid: str, likelihood: DuplicateLikelihood) -> None:
        current = likelihood_by_chart_uid.get(chart_uid)
        if current is None or LIKELIHOOD_SORT_WEIGHT[likelihood] < LIKELIHOOD_SORT_WEIGHT[current]:
            likelihood_by_chart_uid[chart_uid] = likelihood

    def connect_pair(left_uid: str, right_uid: str) -> None:
        if left_uid == right_uid:
            return
        if canonical_pair(left_uid, right_uid) in excluded:
            return
        chart_links.setdefault(left_uid, set()).add(right_uid)
        chart_links.setdefault(right_uid, set()).add(left_uid)

    for row in rows:
        local_row_id = int(row[0])
        chart_uid = chart_uids_by_local_row.get(local_row_id)
        if not chart_uid:
            continue
        name = row[1]
        alias = row[2]
        birth_month = row[17]
        birth_day = row[18]
        birth_year = row[19]
        if chart_row_is_non_aggregable(row):
            placeholder_uids.add(chart_uid)
        chart_names[chart_uid] = _display_name(chart_uid, name, alias)

        if (
            isinstance(birth_year, int)
            and isinstance(birth_month, int)
            and isinstance(birth_day, int)
        ):
            birthday_groups.setdefault((birth_year, birth_month, birth_day), []).append(chart_uid)

        normalized_variants = {
            value
            for value in (_normalize_name(name), _normalize_name(alias))
            if value
        }
        for variant in normalized_variants:
            normalized_name_to_uids.setdefault(variant, set()).add(chart_uid)

    def mark_related(group_uids: set[str], reason_key: str, likelihood: DuplicateLikelihood) -> None:
        if len(group_uids) < 2:
            return
        duplicate_uids.update(group_uids)
        group_values = sorted(group_uids)
        for i, left_uid in enumerate(group_values):
            attach_likelihood(left_uid, likelihood)
            for right_uid in group_values[i + 1 :]:
                connect_pair(left_uid, right_uid)
        for chart_uid in group_uids:
            related_by_reason = related_names.setdefault(chart_uid, {})
            related = related_by_reason.setdefault(reason_key, set())
            for other_uid in group_uids:
                if other_uid == chart_uid:
                    continue
                if canonical_pair(chart_uid, other_uid) in excluded:
                    continue
                related.add(chart_names.get(other_uid, f"UID {other_uid}"))

    for chart_uids in birthday_groups.values():
        mark_related(set(chart_uids), "birth_date_year", "mid_birth_date")
    for chart_uids in normalized_name_to_uids.values():
        mark_related(set(chart_uids), "name_exact", "probable_name")

    variant_values = list(normalized_name_to_uids.keys())
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
                left_uids = normalized_name_to_uids.get(left_variant, set())
                right_uids = normalized_name_to_uids.get(right_variant, set())
                mark_related(left_uids.union(right_uids), "name_fuzzy", "suspected")

    if load_chart_by_uid is not None and similarity_ceiling_percent >= similarity_threshold_percent:
        min_score = float(similarity_threshold_percent) / 100.0
        max_score = float(similarity_ceiling_percent) / 100.0
        eligible_uids = sorted(
            chart_uid
            for chart_uid in chart_names
            if chart_uid not in placeholder_uids
        )
        loaded_charts: dict[str, Chart | None] = {}

        def get_chart(chart_uid: str) -> Chart | None:
            if chart_uid not in loaded_charts:
                try:
                    loaded_charts[chart_uid] = load_chart_by_uid(chart_uid)
                except Exception:
                    loaded_charts[chart_uid] = None
            return loaded_charts[chart_uid]

        for index, left_uid in enumerate(eligible_uids):
            left_chart = get_chart(left_uid)
            if left_chart is None or not getattr(left_chart, "positions", None):
                continue
            for right_uid in eligible_uids[index + 1 :]:
                right_chart = get_chart(right_uid)
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
                mark_related({left_uid, right_uid}, reason_key, likelihood)
                left_related = related_names.setdefault(left_uid, {}).setdefault(reason_key, set())
                right_related = related_names.setdefault(right_uid, {}).setdefault(reason_key, set())
                left_related.add(f"{chart_names.get(right_uid, f'UID {right_uid}')} ({percent:.1f}%)")
                right_related.add(f"{chart_names.get(left_uid, f'UID {left_uid}')} ({percent:.1f}%)")

    component_uid_by_chart: dict[str, int] = {}
    component_index = 0
    for chart_uid in sorted(duplicate_uids):
        if chart_uid in component_uid_by_chart:
            continue
        component_index += 1
        stack = [chart_uid]
        component_uid_by_chart[chart_uid] = component_index
        while stack:
            current = stack.pop()
            for neighbor in chart_links.get(current, set()):
                if neighbor in component_uid_by_chart:
                    continue
                component_uid_by_chart[neighbor] = component_index
                stack.append(neighbor)

    duplicate_sort_key_by_chart_uid = {
        chart_uid: (
            component_uid_by_chart.get(chart_uid, 10_000_000),
            LIKELIHOOD_SORT_WEIGHT.get(likelihood_by_chart_uid.get(chart_uid, "suspected"), 9),
            chart_names.get(chart_uid, "").casefold(),
        )
        for chart_uid in duplicate_uids
    }

    return DuplicateDetectionResult(
        duplicate_uids=duplicate_uids,
        related_names={
            chart_uid: {
                reason_key: sorted(names, key=str.casefold)
                for reason_key, names in grouped_names.items()
                if names
            }
            for chart_uid, grouped_names in related_names.items()
            if any(grouped_names.values())
        },
        likelihood_by_chart_uid=likelihood_by_chart_uid,
        duplicate_sort_key_by_chart_uid=duplicate_sort_key_by_chart_uid,
        duplicate_group_by_chart_uid=component_uid_by_chart,
    )
