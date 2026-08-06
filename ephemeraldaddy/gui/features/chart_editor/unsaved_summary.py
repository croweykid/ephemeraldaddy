"""User-facing summaries for Chart Editor unsaved-change prompts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any


MAX_VISIBLE_UNSAVED_CHANGES = 8
RECALCULATION_NOTICE = (
    "Birth/time calculation fields changed; chart recalculation is required."
)


@dataclass(frozen=True, slots=True)
class ChartEditorDraftSummary:
    """Widget-independent values needed to describe a Chart Editor draft."""

    name: str
    alias: str
    from_whence: str
    birth_date: str
    birth_place: str
    birthtime_unknown: bool
    birth_time: str
    retcon_time_used: bool
    retcon_time: str
    rectification_range_used: bool
    rectification_range: str
    chart_type: object
    gender: object
    tags: tuple[str, ...]
    comments: str
    rectification_notes: str
    biography: str
    chart_data_source: str
    enneagram_type: tuple[str, str]
    tritype: tuple[int, int, int]
    mbti: tuple[str, str, str, str]


def _time_from_minutes(minutes: object) -> str:
    if not isinstance(minutes, int):
        return "blank"
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _saved_birth_date(chart: Any) -> str:
    month = getattr(chart, "birth_month", None)
    day = getattr(chart, "birth_day", None)
    year = getattr(chart, "birth_year", None)
    if month and day and year:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    dt = getattr(chart, "dt", None)
    return dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else "blank"


def _normalized_tags(tags: Iterable[object] | None) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_tag in tags or ():
        tag = str(raw_tag or "").strip()
        if tag and tag.casefold() not in seen:
            normalized.append(tag)
            seen.add(tag.casefold())
    return tuple(normalized)


def _enneagram_display(values: Iterable[object] | None) -> str:
    normalized = [str(value or "0") for value in (values or ())]
    primary, wing = (normalized + ["0", "0"])[:2]
    if primary == "0":
        return ""
    return primary if wing == "0" else f"{primary}w{wing}"


def _tritype_display(values: Iterable[object] | None) -> str:
    normalized = [int(value or 0) for value in (values or ())]
    populated = [str(value) for value in (normalized + [0, 0, 0])[:3] if value]
    return "-".join(populated)


def _mbti_display(values: Iterable[object] | None) -> str:
    normalized = [str(value or "?") for value in (values or ())]
    letters = (normalized + ["?", "?", "?", "?"])[:4]
    return "" if all(letter == "?" for letter in letters) else "".join(letters)


def summarize_chart_editor_draft_changes(
    saved_chart: Any,
    draft: ChartEditorDraftSummary,
    *,
    recalculation_required: bool,
) -> list[str]:
    """Compare a persisted chart with a typed, widget-free editor draft."""
    changes: list[str] = []

    def add(label: str, before: object, after: object) -> None:
        def display(value: object) -> str:
            if isinstance(value, bool):
                return "yes" if value else "no"
            return "" if value is None else str(value).strip()

        before_text = display(before)
        after_text = display(after)
        if before_text != after_text:
            changes.append(format_unsaved_change_line(label, before_text, after_text))

    saved_dt = getattr(saved_chart, "dt", None)
    saved_birth_time = (
        saved_dt.strftime("%H:%M") if hasattr(saved_dt, "strftime") else "blank"
    )
    saved_retcon_time = (
        f"{int(getattr(saved_chart, 'retcon_hour', 0) or 0):02d}:"
        f"{int(getattr(saved_chart, 'retcon_minute', 0) or 0):02d}"
    )
    saved_range = (
        f"{_time_from_minutes(getattr(saved_chart, 'rectification_range_start_minute', None))}"
        " to "
        f"{_time_from_minutes(getattr(saved_chart, 'rectification_range_end_minute', None))}"
    )

    add("Name", getattr(saved_chart, "name", ""), draft.name)
    add("Alias", getattr(saved_chart, "alias", ""), draft.alias)
    add("From", getattr(saved_chart, "from_whence", ""), draft.from_whence)
    add("Birth date", _saved_birth_date(saved_chart), draft.birth_date)
    add("Birth place", getattr(saved_chart, "birth_place", ""), draft.birth_place)
    add("Unknown birth time", bool(getattr(saved_chart, "birthtime_unknown", False)), draft.birthtime_unknown)
    if not draft.birthtime_unknown:
        add("Birth time", saved_birth_time, draft.birth_time)
    add("Use rectified time", bool(getattr(saved_chart, "retcon_time_used", False)), draft.retcon_time_used)
    add("Rectified time", saved_retcon_time, draft.retcon_time)
    add(
        "Use rectified range",
        bool(getattr(saved_chart, "rectification_range_used", False)),
        draft.rectification_range_used,
    )
    add("Rectified range", saved_range, draft.rectification_range)
    add("Chart type", getattr(saved_chart, "chart_type", ""), draft.chart_type)
    add("Gender", getattr(saved_chart, "gender", ""), draft.gender)
    add("Tags", ", ".join(_normalized_tags(getattr(saved_chart, "tags", None))), ", ".join(draft.tags))
    add("Notes", getattr(saved_chart, "comments", ""), draft.comments)
    add("Rectification notes", getattr(saved_chart, "rectification_notes", ""), draft.rectification_notes)
    add("Bio", getattr(saved_chart, "biography", ""), draft.biography)
    add("Source", getattr(saved_chart, "chart_data_source", ""), draft.chart_data_source)
    add(
        "Enneagram",
        _enneagram_display(getattr(saved_chart, "enneagram_type", None)),
        _enneagram_display(draft.enneagram_type),
    )
    add(
        "Tri-Type",
        _tritype_display(getattr(saved_chart, "tritype", None)),
        _tritype_display(draft.tritype),
    )
    add(
        "MBTI",
        _mbti_display(getattr(saved_chart, "mbti", None)),
        _mbti_display(draft.mbti),
    )
    if recalculation_required:
        changes.insert(0, RECALCULATION_NOTICE)
    return changes


def format_unsaved_change_line(label: str, before: object, after: object) -> str:
    """Return one compact before/after line for the leave-Chart-Editor prompt."""
    before_text = "blank" if before in (None, "") else str(before)
    after_text = "blank" if after in (None, "") else str(after)
    return f"{label}: {before_text} → {after_text}"


def build_unsaved_changes_prompt_details(changes: Iterable[str]) -> str:
    """Build bounded detailed text for a QMessageBox unsaved-change prompt."""
    change_list = [str(change).strip() for change in changes if str(change).strip()]
    if not change_list:
        return "Unsaved fields could not be summarized; saving will preserve the current Chart Editor draft."
    visible = change_list[:MAX_VISIBLE_UNSAVED_CHANGES]
    lines = ["Unsaved changes detected:", *[f"• {change}" for change in visible]]
    remaining = len(change_list) - len(visible)
    if remaining > 0:
        lines.append(f"• …and {remaining} more field(s).")
    return "\n".join(lines)
