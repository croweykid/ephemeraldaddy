"""Scope shared Trait completions to the current Analytics ranking."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from PySide6.QtCore import QObject
from ephemeraldaddy.gui.features.predictions.trait_updates import TraitRefreshRelay


class TraitRankingsRefreshRelay(TraitRefreshRelay):
    """Filter GUI-thread notifications using explicit chart and Trait UIDs."""

    def __init__(self, parent: QObject, refresh: Callable[[], None]) -> None:
        self._chart_uids: frozenset[str] = frozenset()
        self._trait_uid = ""
        self._refresh = refresh
        super().__init__(parent, self._scope_completed)

    def set_scope(self, chart_uids: Iterable[str], trait_uid: str) -> None:
        self._chart_uids = frozenset(str(uid).strip().upper() for uid in chart_uids)
        self._trait_uid = trait_uid

    def _scope_completed(self, chart_uids: frozenset[str], trait_uids: frozenset[str]) -> None:
        if self._trait_uid in trait_uids and self._chart_uids.intersection(chart_uids):
            self._refresh()
