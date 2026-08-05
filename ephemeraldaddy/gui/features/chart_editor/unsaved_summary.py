"""User-facing summaries for Chart Editor unsaved-change prompts."""

from __future__ import annotations

from collections.abc import Iterable


MAX_VISIBLE_UNSAVED_CHANGES = 8


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
