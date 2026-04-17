from __future__ import annotations

import re
import random
import time
from dataclasses import dataclass
from typing import Callable
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from ephemeraldaddy.analysis.country_lookup import resolve_country
from ephemeraldaddy.analysis.us_state_lookup import normalize_us_state
from ephemeraldaddy.gui.astrotheme_search import (
    parse_astrotheme_profile,
    search_astrotheme_profile_url,
)
from ephemeraldaddy.io.geocode import search_locations

HTTP_URL_PATTERN = re.compile(r"Astrotheme profile: https://\S+", re.IGNORECASE)
BIOGRAPHY_CUTOFF_MARKER = "Astrological Profile of"

ACTION_ALIAS_TO_FROM = "alias_to_from"
ACTION_COMMENTS_TO_SOURCE = "comments_to_source"
ACTION_CLEAN_BIOGRAPHY = "clean_biography"
ACTION_GET_BIO = "get_bio"
ACTION_CLEAN_BIRTHPLACE = "clean_birthplace"

MIGRATION_ACTION_LABELS: dict[str, str] = {
    ACTION_ALIAS_TO_FROM: "Alias -> From",
    ACTION_COMMENTS_TO_SOURCE: "Comments -> Source",
    ACTION_CLEAN_BIOGRAPHY: "Clean up Biography Text",
    ACTION_GET_BIO: "Get Bio",
    ACTION_CLEAN_BIRTHPLACE: "Clean up Birthplace",
}

_POSTAL_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9\- ]{2,}$", re.IGNORECASE)
_STREET_NUMBER_PREFIX_PATTERN = re.compile(r"^\d+[A-Z]?(?:\s*[-/]\s*\d+)?$")
_STREET_KEYWORDS = (
    "street",
    "st.",
    "st ",
    "avenue",
    "ave",
    "boulevard",
    "blvd",
    "road",
    "rd",
    "lane",
    "ln",
    "drive",
    "dr",
    "court",
    "ct",
    "highway",
    "hwy",
    "route",
    "rte",
    "way",
)
_NOISE_KEYWORDS = (
    "post office",
    "county",
    "township",
    "district",
    "neighborhood",
    "neighbourhood",
    "ward",
    "zip",
)


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
        lookup_location_label: Callable[[str], str | None] | None = None,
        random_delay_seconds_range: tuple[int, int] | None = None,
    ) -> None:
        super().__init__()
        self._chart_ids = list(chart_ids)
        self._action = action
        self._load_chart_by_id = load_chart_by_id
        self._update_chart_by_id = update_chart_by_id
        self._lookup_biography_by_name = lookup_biography_by_name
        self._lookup_location_label = lookup_location_label
        self._random_delay_seconds_range = random_delay_seconds_range

    def run(self) -> None:
        try:
            outcome, changed_ids = run_metadata_migration(
                chart_ids=self._chart_ids,
                action=self._action,
                load_chart_by_id=self._load_chart_by_id,
                update_chart_by_id=self._update_chart_by_id,
                lookup_biography_by_name=self._lookup_biography_by_name,
                lookup_location_label=self._lookup_location_label,
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
    lookup_location_label: Callable[[str], str | None] | None = None,
    random_delay_seconds_range: tuple[int, int] | None = None,
) -> QThread:
    thread = QThread()
    worker = MetadataMigrationWorker(
        chart_ids=chart_ids,
        action=action,
        load_chart_by_id=load_chart_by_id,
        update_chart_by_id=update_chart_by_id,
        lookup_biography_by_name=lookup_biography_by_name,
        lookup_location_label=lookup_location_label,
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
    existing_biography = str(getattr(chart, "biography", "") or getattr(chart, "bio", "") or "").strip()
    if biography_text.strip() == existing_biography:
        return False
    chart_name = str(getattr(chart, "name", "") or "").strip()
    biography_text = lookup_biography_by_name(chart_name)
    if hasattr(chart, "biography"):
        chart.biography = biography_text
    if hasattr(chart, "bio"):
        chart.bio = biography_text
    return True


def lookup_gazetteer_label(query: str) -> str | None:
    cleaned_query = str(query or "").strip()
    if not cleaned_query:
        return None
    try:
        matches = search_locations(cleaned_query, limit=1)
    except Exception:
        return None
    if not matches:
        return None
    label = str(matches[0][0] or "").strip()
    return label or None


def _looks_like_street_or_postal_token(token: str) -> bool:
    lowered = token.lower()
    if any(keyword in lowered for keyword in _STREET_KEYWORDS):
        return True
    if _STREET_NUMBER_PREFIX_PATTERN.match(token):
        return True
    compact = token.replace(" ", "")
    if any(char.isdigit() for char in compact) and _POSTAL_CODE_PATTERN.match(token):
        return True
    return False


def _is_noise_location_token(token: str) -> bool:
    lowered = token.lower().strip()
    if not lowered:
        return True
    if _looks_like_street_or_postal_token(token):
        return True
    return any(keyword in lowered for keyword in _NOISE_KEYWORDS)


def _choose_city_token(
    candidates: list[str],
    *,
    prefer_last: bool,
    keep_city_of_prefix: bool,
) -> str | None:
    def _normalize_city_label(token: str) -> str:
        lowered = token.lower()
        if not keep_city_of_prefix and lowered.startswith("city of "):
            return token[8:].strip()
        return token

    preferred_candidates = [token for token in candidates if token.lower().startswith("city of ")]
    if preferred_candidates:
        chosen = preferred_candidates[-1] if prefer_last else preferred_candidates[0]
        return _normalize_city_label(chosen)
    filtered = [
        token
        for token in candidates
        if not token.lower().startswith("greater ")
        and " region" not in token.lower()
    ]
    if filtered:
        chosen = filtered[-1] if prefer_last else filtered[0]
        return _normalize_city_label(chosen)
    if not candidates:
        return None
    chosen = candidates[-1] if prefer_last else candidates[0]
    return _normalize_city_label(chosen)


def _extract_birthplace_query(raw_birth_place: str) -> str | None:
    raw_parts = [part.strip() for part in str(raw_birth_place or "").split(",") if part.strip()]
    if not raw_parts:
        return None

    country_index = None
    country_iso2 = None
    for index in range(len(raw_parts) - 1, -1, -1):
        country_meta = resolve_country(raw_parts[index])
        if country_meta:
            country_index = index
            country_iso2 = str(country_meta.get("alpha_2", "")).strip().upper() or None
            break

    if country_index is None:
        country_index = len(raw_parts) - 1
        country_token = raw_parts[country_index]
    else:
        country_token = country_iso2 or raw_parts[country_index]

    local_parts = raw_parts[:country_index]
    if not local_parts:
        return f"{country_token}" if country_token else None

    meaningful_parts = [token for token in local_parts if not _is_noise_location_token(token)]
    if not meaningful_parts:
        meaningful_parts = [token for token in local_parts if token]
    if not meaningful_parts:
        return f"{country_token}" if country_token else None

    if (country_iso2 or "").upper() == "US":
        state_token = None
        state_index = -1
        for index in range(len(meaningful_parts) - 1, -1, -1):
            normalized = normalize_us_state(meaningful_parts[index])
            if normalized:
                state_token = normalized
                state_index = index
                break
        city_candidates = meaningful_parts[:state_index] if state_index >= 0 else meaningful_parts
        city_token = _choose_city_token(
            city_candidates,
            prefer_last=True,
            keep_city_of_prefix=False,
        )
        if city_token and state_token:
            return f"{city_token}, {state_token}, US"
        if city_token:
            return f"{city_token}, US"
        return f"{country_token}" if country_token else None

    city_token = _choose_city_token(
        meaningful_parts,
        prefer_last=False,
        keep_city_of_prefix=True,
    )
    if city_token and country_token:
        return f"{city_token}, {country_token}"
    return city_token or country_token


def cleanup_birthplace_text(
    chart: Any,
    *,
    lookup_location_label: Callable[[str], str | None] | None = None,
) -> bool:
    original_birth_place = str(getattr(chart, "birth_place", "") or "").strip()
    if not original_birth_place:
        return False
    query = _extract_birthplace_query(original_birth_place)
    if not query:
        return False
    normalized_birth_place = None
    if lookup_location_label is not None:
        normalized_birth_place = lookup_location_label(query)
    if not normalized_birth_place:
        normalized_birth_place = query
    normalized_birth_place = str(normalized_birth_place or "").strip()
    if not normalized_birth_place or normalized_birth_place == original_birth_place:
        return False
    chart.birth_place = normalized_birth_place
    return True


def run_metadata_migration(
    *,
    chart_ids: list[int],
    action: str,
    load_chart_by_id: Callable[[int], Any],
    update_chart_by_id: Callable[[int, Any], None],
    lookup_biography_by_name: Callable[[str], str] | None = None,
    lookup_location_label: Callable[[str], str | None] | None = None,
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
            elif action == ACTION_CLEAN_BIRTHPLACE:
                if not cleanup_birthplace_text(
                    chart,
                    lookup_location_label=lookup_location_label,
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
