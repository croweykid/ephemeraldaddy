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
    required_tags: list[str],
    include_untagged: bool,
) -> bool:
    """Evaluate whether a chart's tags satisfy search filters."""
    normalized_required = [tag.casefold() for tag in required_tags]
    chart_tags = chart_tags_for_search(raw_tags)
    is_untagged = not chart_tags
    if include_untagged and is_untagged:
        return True
    if normalized_required and not all(tag in chart_tags for tag in normalized_required):
        return False
    return bool(normalized_required) or not include_untagged or not is_untagged
