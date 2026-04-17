from __future__ import annotations

import re
import random
import time
from dataclasses import dataclass
from typing import Callable
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from ephemeraldaddy.gui.astrotheme_search import (
    parse_astrotheme_profile,
    search_astrotheme_profile_url,
)

HTTP_URL_PATTERN = re.compile(r"Astrotheme profile: https://\S+", re.IGNORECASE)
BIOGRAPHY_CUTOFF_MARKER = "Astrological Profile of"

ACTION_ALIAS_TO_FROM = "alias_to_from"
ACTION_COMMENTS_TO_SOURCE = "comments_to_source"
ACTION_CLEAN_BIOGRAPHY = "clean_biography"
ACTION_GET_BIO = "get_bio"

MIGRATION_ACTION_LABELS: dict[str, str] = {
    ACTION_ALIAS_TO_FROM: "Alias -> From",
    ACTION_COMMENTS_TO_SOURCE: "Comments -> Source",
    ACTION_CLEAN_BIOGRAPHY: "Clean up Biography Text",
    ACTION_GET_BIO: "Get Bio",
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


class MetadataMigrationWorker(QObject):
    finished = Signal(object, object)
    failed = Signal(str)

    def __init__(
        self,
        *,
        chart_ids: list[int],
        action: str,
        load_chart_by_id: Callable[[int], Any],
        update_chart_by_id: Callable[[int, Any], None],
        lookup_biography_by_name: Callable[[str], str] | None = None,
        random_delay_seconds_range: tuple[int, int] | None = None,
    ) -> None:
        super().__init__()
        self._chart_ids = list(chart_ids)
        self._action = action
        self._load_chart_by_id = load_chart_by_id
        self._update_chart_by_id = update_chart_by_id
        self._lookup_biography_by_name = lookup_biography_by_name
        self._random_delay_seconds_range = random_delay_seconds_range

    def run(self) -> None:
        try:
            outcome, changed_ids = run_metadata_migration(
                chart_ids=self._chart_ids,
                action=self._action,
                load_chart_by_id=self._load_chart_by_id,
                update_chart_by_id=self._update_chart_by_id,
                lookup_biography_by_name=self._lookup_biography_by_name,
                random_delay_seconds_range=self._random_delay_seconds_range,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(outcome, changed_ids)


def launch_metadata_migration_worker(
    *,
    chart_ids: list[int],
    action: str,
    load_chart_by_id: Callable[[int], Any],
    update_chart_by_id: Callable[[int, Any], None],
    on_finished: Callable[[MetadataMigrationOutcome, set[int]], None],
    on_failed: Callable[[str], None],
    lookup_biography_by_name: Callable[[str], str] | None = None,
    random_delay_seconds_range: tuple[int, int] | None = None,
) -> QThread:
    thread = QThread()
    worker = MetadataMigrationWorker(
        chart_ids=chart_ids,
        action=action,
        load_chart_by_id=load_chart_by_id,
        update_chart_by_id=update_chart_by_id,
        lookup_biography_by_name=lookup_biography_by_name,
        random_delay_seconds_range=random_delay_seconds_range,
    )
    worker.moveToThread(thread)
    thread.started.connect(worker.run)

    def _handle_finished(outcome: object, changed_ids: object) -> None:
        on_finished(outcome, changed_ids)
        thread.quit()

    def _handle_failed(message: str) -> None:
        on_failed(message)
        thread.quit()

    worker.finished.connect(_handle_finished)
    worker.failed.connect(_handle_failed)
    worker.finished.connect(worker.deleteLater)
    worker.failed.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread


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


def fetch_astrotheme_biography_by_name(chart_name: str) -> str:
    normalized_name = str(chart_name or "").strip()
    if not normalized_name:
        raise ValueError("Chart has no name to search.")
    profile_url = search_astrotheme_profile_url(normalized_name)
    if not profile_url:
        raise ValueError("No matching Astrotheme profile was found.")
    profile_data = parse_astrotheme_profile(profile_url)
    biography_text = str(profile_data.get("biography", "") or "").strip()
    if not biography_text:
        raise ValueError("Astrotheme profile did not include biography text.")
    return biography_text


def import_biography_from_lookup(
    chart: Any,
    *,
    lookup_biography_by_name: Callable[[str], str],
) -> bool:
    biography_value = str(getattr(chart, "biography", "") or getattr(chart, "bio", "") or "").strip()
    if biography_value:
        return False
    chart_name = str(getattr(chart, "name", "") or "").strip()
    biography_text = lookup_biography_by_name(chart_name)
    if hasattr(chart, "biography"):
        chart.biography = biography_text
    if hasattr(chart, "bio"):
        chart.bio = biography_text
    return True


def run_metadata_migration(
    *,
    chart_ids: list[int],
    action: str,
    load_chart_by_id: Callable[[int], Any],
    update_chart_by_id: Callable[[int, Any], None],
    lookup_biography_by_name: Callable[[str], str] | None = None,
    random_delay_seconds_range: tuple[int, int] | None = None,
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
            elif action == ACTION_GET_BIO:
                if lookup_biography_by_name is None:
                    raise ValueError("lookup_biography_by_name callback is required for get_bio action")
                if not import_biography_from_lookup(
                    chart,
                    lookup_biography_by_name=lookup_biography_by_name,
                ):
                    continue
                changed_unit_count += 1
            else:
                raise ValueError(f"Unsupported metadata migration action: {action}")

            update_chart_by_id(int(chart_id), chart)
            changed_chart_ids.add(int(chart_id))
        except Exception:
            error_count += 1
        if (
            action == ACTION_GET_BIO
            and random_delay_seconds_range is not None
            and chart_id != chart_ids[-1]
        ):
            minimum_delay, maximum_delay = random_delay_seconds_range
            lower_bound = max(0, min(int(minimum_delay), int(maximum_delay)))
            upper_bound = max(lower_bound, int(maximum_delay))
            time.sleep(random.randint(lower_bound, upper_bound))

    outcome = MetadataMigrationOutcome(
        selected_count=len(chart_ids),
        updated_chart_count=len(changed_chart_ids),
        changed_unit_count=changed_unit_count,
        error_count=error_count,
    )
    return outcome, changed_chart_ids
