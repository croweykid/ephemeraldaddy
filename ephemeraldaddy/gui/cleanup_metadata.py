from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable
from typing import Any


HTTP_URL_PATTERN = re.compile(r"http://\S+", re.IGNORECASE)
BIOGRAPHY_CUTOFF_MARKER = "Astrological Profile of"

ACTION_ALIAS_TO_FROM = "alias_to_from"
ACTION_COMMENTS_TO_SOURCE = "comments_to_source"
ACTION_CLEAN_BIOGRAPHY = "clean_biography"

MIGRATION_ACTION_LABELS: dict[str, str] = {
    ACTION_ALIAS_TO_FROM: "Alias -> From",
    ACTION_COMMENTS_TO_SOURCE: "Comments -> Source",
    ACTION_CLEAN_BIOGRAPHY: "Clean up Biography Text",
}


@dataclass(frozen=True)
class MetadataMigrationOutcome:
    selected_count: int
    updated_chart_count: int
    changed_unit_count: int
    error_count: int

    @property
    def unchanged_count(self) -> int:
        return max(0, self.selected_count - self.updated_chart_count - self.error_count)


def move_alias_to_from_whence(chart: Any) -> bool:
    alias_value = str(getattr(chart, "alias", "") or "").strip()
    if not alias_value:
        return False
    chart.from_whence = alias_value
    chart.alias = ""
    return True


def migrate_comment_urls_to_source(chart: Any) -> int:
    comments = str(getattr(chart, "comments", "") or "")
    if not comments:
        return 0

    matches = [match.group(0) for match in HTTP_URL_PATTERN.finditer(comments)]
    if not matches:
        return 0

    existing_source = str(getattr(chart, "chart_data_source", "") or "").strip()
    source_parts = [part.strip() for part in existing_source.splitlines() if part.strip()]
    for url in matches:
        if url not in source_parts:
            source_parts.append(url)

    updated_comments = comments
    for url in matches:
        updated_comments = updated_comments.replace(url, "")

    chart.chart_data_source = "\n".join(source_parts)
    chart.comments = updated_comments
    return len(matches)


def cleanup_biography_text(chart: Any) -> bool:
    biography_value = str(getattr(chart, "biography", "") or getattr(chart, "bio", "") or "")
    marker_index = biography_value.find(BIOGRAPHY_CUTOFF_MARKER)
    if marker_index < 0:
        return False
    cleaned_value = biography_value[:marker_index].rstrip()
    if cleaned_value == biography_value:
        return False
    if hasattr(chart, "biography"):
        chart.biography = cleaned_value
    if hasattr(chart, "bio"):
        chart.bio = cleaned_value
    return True


def run_metadata_migration(
    *,
    chart_ids: list[int],
    action: str,
    load_chart_by_id: Callable[[int], Any],
    update_chart_by_id: Callable[[int, Any], None],
) -> tuple[MetadataMigrationOutcome, set[int]]:
    changed_chart_ids: set[int] = set()
    changed_unit_count = 0
    error_count = 0

    for chart_id in chart_ids:
        try:
            chart = load_chart_by_id(int(chart_id))
            if chart is None:
                error_count += 1
                continue
            if action == ACTION_ALIAS_TO_FROM:
                if not move_alias_to_from_whence(chart):
                    continue
                changed_unit_count += 1
            elif action == ACTION_COMMENTS_TO_SOURCE:
                moved_url_count = migrate_comment_urls_to_source(chart)
                if moved_url_count <= 0:
                    continue
                changed_unit_count += moved_url_count
            elif action == ACTION_CLEAN_BIOGRAPHY:
                if not cleanup_biography_text(chart):
                    continue
                changed_unit_count += 1
            else:
                raise ValueError(f"Unsupported metadata migration action: {action}")

            update_chart_by_id(int(chart_id), chart)
            changed_chart_ids.add(int(chart_id))
        except Exception:
            error_count += 1

    outcome = MetadataMigrationOutcome(
        selected_count=len(chart_ids),
        updated_chart_count=len(changed_chart_ids),
        changed_unit_count=changed_unit_count,
        error_count=error_count,
    )
    return outcome, changed_chart_ids
