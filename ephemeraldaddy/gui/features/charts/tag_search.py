"""Helpers for database tag-search behavior."""

from __future__ import annotations

from typing import Iterable


def _normalize_tag_list(tags: Iterable[str] | None) -> list[str]:
    """Return stripped, deduplicated tags without importing Qt UI helpers."""
    if not tags:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in tags:
        tag = str(raw_value or "").strip()
        if not tag:
            continue
        dedupe_key = tag.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append(tag)
    return normalized


def chart_tags_for_search(raw_tags: Iterable[str] | None) -> set[str]:
    """Return normalized, casefolded chart tags for matching."""
    return {tag.casefold() for tag in _normalize_tag_list(raw_tags)}


def tag_matches_filter(chart_tag: str, filter_tag: str) -> bool:
    """Return whether ``chart_tag`` is the requested tag or one of its children."""
    normalized_chart_tag = str(chart_tag or "").strip().casefold()
    normalized_filter_tag = str(filter_tag or "").strip().casefold()
    if not normalized_chart_tag or not normalized_filter_tag:
        return False
    return normalized_chart_tag == normalized_filter_tag or normalized_chart_tag.startswith(
        f"{normalized_filter_tag}."
    )


def any_tag_matches_filter(chart_tags: Iterable[str], filter_tag: str) -> bool:
    """Return whether any chart tag matches a selected tag-tree filter."""
    return any(tag_matches_filter(chart_tag, filter_tag) for chart_tag in chart_tags)


def chart_matches_tag_filters(
    raw_tags: Iterable[str] | None,
    *,
    included_tags: list[str],
    excluded_tags: list[str],
    untagged_mode: int,
    optional_tags: list[str] | None = None,
) -> bool:
    """Evaluate whether a chart's tags satisfy search filters."""
    normalized_included = [tag.casefold() for tag in included_tags]
    normalized_excluded = [tag.casefold() for tag in excluded_tags]
    normalized_optional = [tag.casefold() for tag in (optional_tags or [])]
    chart_tags = chart_tags_for_search(raw_tags)
    is_untagged = not chart_tags
    if untagged_mode == 1:
        return is_untagged
    if untagged_mode == 2 and is_untagged:
        return False
    if normalized_excluded and any(
        any_tag_matches_filter(chart_tags, tag) for tag in normalized_excluded
    ):
        return False
    if normalized_included and not all(
        any_tag_matches_filter(chart_tags, tag) for tag in normalized_included
    ):
        return False
    if normalized_optional and not any(
        any_tag_matches_filter(chart_tags, tag) for tag in normalized_optional
    ):
        return False
    return True
