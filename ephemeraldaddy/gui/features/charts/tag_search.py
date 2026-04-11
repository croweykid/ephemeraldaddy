"""Helpers for database tag-search behavior."""

from __future__ import annotations

from typing import Iterable

from ephemeraldaddy.gui.features.charts.tagging import normalize_tag_list


def chart_tags_for_search(raw_tags: Iterable[str] | None) -> set[str]:
    """Return normalized, casefolded chart tags for matching."""
    return {tag.casefold() for tag in normalize_tag_list(raw_tags)}


def chart_matches_tag_filters(
    raw_tags: Iterable[str] | None,
    *,
    included_tags: list[str],
    excluded_tags: list[str],
    untagged_mode: int,
) -> bool:
    """Evaluate whether a chart's tags satisfy search filters."""
    normalized_included = [tag.casefold() for tag in included_tags]
    normalized_excluded = [tag.casefold() for tag in excluded_tags]
    chart_tags = chart_tags_for_search(raw_tags)
    is_untagged = not chart_tags
    if untagged_mode == 1:
        return is_untagged
    if untagged_mode == 2 and is_untagged:
        return False
    if normalized_excluded and any(tag in chart_tags for tag in normalized_excluded):
        return False
    if normalized_included:
        return all(tag in chart_tags for tag in normalized_included)
    return True
