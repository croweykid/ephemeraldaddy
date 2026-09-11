"""Window-independent state for one Chart Editor create/edit lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

ChangeKind = Literal["authoritative", "lightweight"]


def _normalize_chart_uid(chart_uid: str | None) -> str | None:
    normalized = str(chart_uid or "").strip().upper()
    return normalized or None


@dataclass(frozen=True, slots=True)
class ChartSaveResult:
    """Describe the downstream impact of one successful chart save."""

    changed_fields: frozenset[str] | None
    recalculated: bool
    changed_chart_data: bool
    prediction_flush_required: bool


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
    authoritative_dirty_fields: set[str] = field(default_factory=set)
    last_save_result: ChartSaveResult | None = None
    saved_changes_since_load: bool = False
    prediction_flush_pending: bool = False

    def __post_init__(self) -> None:
        self.active_chart_uid = _normalize_chart_uid(self.active_chart_uid)
        self.authoritative_values = dict(self.authoritative_values)
        self.draft_values = dict(self.draft_values or self.authoritative_values)
        self.dirty_fields = set(self.dirty_fields)
        self.authoritative_dirty_fields = set(self.authoritative_dirty_fields)

    @property
    def is_dirty(self) -> bool:
        return bool(self.dirty_fields)

    @property
    def recalculation_required(self) -> bool:
        return bool(self.authoritative_dirty_fields)

    @property
    def last_changed_fields(self) -> frozenset[str] | None:
        """Return the latest save change set, preserving unknown classification."""
        if self.last_save_result is None:
            return None
        return self.last_save_result.changed_fields

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
        self.authoritative_dirty_fields.clear()
        self.last_save_result = None
        self.saved_changes_since_load = False
        self.prediction_flush_pending = False

    def set_active_chart_uid(self, chart_uid: str | None) -> None:
        """Update only the persisted identity while preserving draft state."""
        self.active_chart_uid = _normalize_chart_uid(chart_uid)

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
            self.authoritative_dirty_fields.add(normalized_field)

    def require_recalculation(self, required: bool) -> None:
        """Bridge legacy dirty notifications until all fields use typed drafts."""
        legacy_reason = "legacy-unspecified"
        if required:
            self.authoritative_dirty_fields.add(legacy_reason)
        else:
            self.authoritative_dirty_fields.clear()

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
            self.authoritative_dirty_fields.discard(normalized_field)
        else:
            self.mark_dirty(normalized_field, kind=kind)

    def mark_clean(self) -> None:
        """Accept the current draft as saved and clear pending impact."""
        self.authoritative_values = dict(self.draft_values)
        self.dirty_fields.clear()
        self.authoritative_dirty_fields.clear()

    def record_successful_save(
        self,
        *,
        changed_fields: set[str] | frozenset[str] | None,
        recalculated: bool,
        changed_chart_data: bool,
        prediction_flush_required: bool,
    ) -> ChartSaveResult:
        """Record a save result and accumulate lifecycle-level refresh state."""
        result = ChartSaveResult(
            changed_fields=(
                None if changed_fields is None else frozenset(changed_fields)
            ),
            recalculated=bool(recalculated),
            changed_chart_data=bool(changed_chart_data),
            prediction_flush_required=bool(prediction_flush_required),
        )
        self.last_save_result = result
        self.saved_changes_since_load |= result.changed_chart_data
        self.prediction_flush_pending |= result.prediction_flush_required
        self.mark_clean()
        return result

    def mark_prediction_flush_complete(self) -> None:
        """Clear pending prediction work after a successful synchronous flush."""
        self.prediction_flush_pending = False

    def discard(self) -> None:
        """Restore the authoritative snapshot and clear pending impact."""
        self.draft_values = dict(self.authoritative_values)
        self.dirty_fields.clear()
        self.authoritative_dirty_fields.clear()
