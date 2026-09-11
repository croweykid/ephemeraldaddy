"""UID-first state and coordination for Database View chart selection."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


def normalize_chart_uid(chart_uid: object) -> str | None:
    normalized = str(chart_uid or "").strip().upper()
    return normalized or None


def _ordered_unique_uids(chart_uids: Iterable[object]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw_uid in chart_uids:
        chart_uid = normalize_chart_uid(raw_uid)
        if chart_uid is None or chart_uid in seen:
            continue
        seen.add(chart_uid)
        ordered.append(chart_uid)
    return ordered


@dataclass
class DatabaseSelectionModel:
    """Own logical selection independently from list visibility and Qt indexes."""

    selected_uids: list[str] = field(default_factory=list)
    anchor_uid: str | None = None
    prior_single_selection: str | None = None

    @property
    def selected_uid_set(self) -> set[str]:
        return set(self.selected_uids)

    def replace(
        self,
        chart_uids: Iterable[object],
        *,
        remember_deselection: bool = False,
    ) -> None:
        replacement = _ordered_unique_uids(chart_uids)
        if remember_deselection and len(self.selected_uids) == 1 and not replacement:
            self.prior_single_selection = self.selected_uids[0]
        elif replacement:
            self.prior_single_selection = None
        self.selected_uids = replacement

    def reconcile(self, valid_uids: Iterable[object]) -> bool:
        valid = set(_ordered_unique_uids(valid_uids))
        reconciled = [uid for uid in self.selected_uids if uid in valid]
        if reconciled == self.selected_uids:
            if self.anchor_uid not in valid:
                self.anchor_uid = None
            return False
        self.replace(reconciled, remember_deselection=False)
        if not reconciled:
            self.prior_single_selection = None
        if self.anchor_uid not in valid:
            self.anchor_uid = None
        return True

    def restore_prior_single_selection(self) -> list[str] | None:
        if self.prior_single_selection is None:
            return None
        restored = [self.prior_single_selection]
        self.prior_single_selection = None
        self.replace(restored)
        return restored


class DatabaseSelectionController:
    """Apply visible-list changes while preserving filtered logical selection."""

    def __init__(self, model: DatabaseSelectionModel | None = None) -> None:
        self.model = model or DatabaseSelectionModel()

    def merge_visible_selection(
        self,
        *,
        visible_uids: Iterable[object],
        selected_visible_uids: Iterable[object],
        replace: bool,
    ) -> list[str]:
        selected_visible = _ordered_unique_uids(selected_visible_uids)
        if replace:
            self.model.replace(selected_visible, remember_deselection=True)
            return list(self.model.selected_uids)

        visible = set(_ordered_unique_uids(visible_uids))
        selected_visible_set = set(selected_visible)
        merged = [
            uid
            for uid in self.model.selected_uids
            if uid not in visible or uid in selected_visible_set
        ]
        merged_set = set(merged)
        for uid in selected_visible:
            if uid not in merged_set:
                merged.append(uid)
                merged_set.add(uid)
        self.model.replace(merged, remember_deselection=True)
        return list(self.model.selected_uids)
