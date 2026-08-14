"""Window-independent state for one Chart Editor create/edit lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

ChangeKind = Literal["authoritative", "lightweight"]


def _normalize_chart_uid(chart_uid: str | None) -> str | None:
    normalized = str(chart_uid or "").strip().upper()
    return normalized or None


@dataclass(slots=True)
class ChartEditSession:
    """Own identity and dirty state without depending on Qt widgets.

    Draft values are deliberately generic during the incremental migration: the
    view still owns widget-to-value translation, while the session owns the
    authoritative snapshot and its current draft.
    """

    active_chart_uid: str | None = None
    authoritative_values: dict[str, Any] = field(default_factory=dict)
    draft_values: dict[str, Any] = field(default_factory=dict)
    dirty_fields: set[str] = field(default_factory=set)
    recalculation_required: bool = False

    def __post_init__(self) -> None:
        self.active_chart_uid = _normalize_chart_uid(self.active_chart_uid)
        self.authoritative_values = dict(self.authoritative_values)
        self.draft_values = dict(self.draft_values or self.authoritative_values)

    @property
    def is_dirty(self) -> bool:
        return bool(self.dirty_fields)

    def begin(
        self,
        *,
        chart_uid: str | None,
        authoritative_values: Mapping[str, Any] | None = None,
    ) -> None:
        """Start a clean persisted-chart or new-chart editing session."""
        values = dict(authoritative_values or {})
        self.active_chart_uid = _normalize_chart_uid(chart_uid)
        self.authoritative_values = values
        self.draft_values = dict(values)
        self.dirty_fields.clear()
        self.recalculation_required = False

    def mark_dirty(
        self,
        field_name: str = "legacy-unspecified",
        *,
        kind: ChangeKind = "lightweight",
    ) -> None:
        """Record a changed field and its recalculation impact."""
        normalized_field = str(field_name).strip()
        if not normalized_field:
            raise ValueError("A dirty field must have a non-empty name")
        self.dirty_fields.add(normalized_field)
        if kind == "authoritative":
            self.recalculation_required = True

    def set_draft_value(
        self,
        field_name: str,
        value: Any,
        *,
        kind: ChangeKind = "lightweight",
    ) -> None:
        """Update a draft value, clearing dirtiness when it matches the snapshot."""
        normalized_field = str(field_name).strip()
        if not normalized_field:
            raise ValueError("A draft field must have a non-empty name")
        self.draft_values[normalized_field] = value
        if self.authoritative_values.get(normalized_field) == value:
            self.dirty_fields.discard(normalized_field)
        else:
            self.mark_dirty(normalized_field, kind=kind)

    def mark_clean(self) -> None:
        """Accept the current draft as saved and clear pending impact."""
        self.authoritative_values = dict(self.draft_values)
        self.dirty_fields.clear()
        self.recalculation_required = False

    def discard(self) -> None:
        """Restore the authoritative snapshot and clear pending impact."""
        self.draft_values = dict(self.authoritative_values)
        self.dirty_fields.clear()
        self.recalculation_required = False
