# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.
"""Database View Rankings panel with Collection-scoped ranking support."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ephemeraldaddy.core.db import get_chart_ids_by_uid
from ephemeraldaddy.gui.features.charts.collections import (
    DEFAULT_COLLECTION_ALL,
    DEFAULT_COLLECTION_OPTIONS,
    chart_belongs_to_collection,
    normalize_collection_id,
)
from ephemeraldaddy.gui.ranking_panel_core import RankingsPanelMixin as _RankingsPanelMixin


class RankingsPanelMixin(_RankingsPanelMixin):
    """Add a collection selector and scope every Rankings population to it."""

    def _build_rankings_panel(self) -> QWidget:
        panel = super()._build_rankings_panel()
        layout = panel.layout()
        if not isinstance(layout, QVBoxLayout):
            return panel

        collection_row = QWidget(panel)
        collection_layout = QHBoxLayout(collection_row)
        collection_layout.setContentsMargins(0, 0, 0, 0)
        collection_layout.setSpacing(6)

        collection_label = QLabel("Collection:")
        collection_label.setStyleSheet("color: #cfcfcf; font-size: 8pt;")
        collection_layout.addWidget(collection_label)

        self.rankings_collection_combo = QComboBox()
        self.rankings_collection_combo.setObjectName("rankingsCollectionDropdown")
        self.rankings_collection_combo.setMinimumWidth(220)
        self.rankings_collection_combo.setMaximumWidth(320)
        self.rankings_collection_combo.setToolTip(
            "Rank only charts belonging to the selected collection."
        )
        collection_layout.addWidget(self.rankings_collection_combo, 1)
        self._sync_rankings_collection_combo()
        self.rankings_collection_combo.currentIndexChanged.connect(
            self._on_rankings_collection_changed
        )

        # Index 0 is the Rankings title. The selector belongs immediately below
        # it and above every collapsible ranking section.
        layout.insertWidget(1, collection_row)
        return panel

    def _rankings_custom_collections(self) -> dict[str, Any]:
        loader = getattr(self, "_load_custom_collections_from_settings", None)
        custom_collections = getattr(self, "_custom_collections", {})
        if callable(loader):
            try:
                custom_collections = loader()
            except Exception:
                pass
        if not isinstance(custom_collections, dict):
            custom_collections = {}
        self._custom_collections = custom_collections
        return custom_collections

    def _rankings_collection_options(self) -> list[tuple[str, str]]:
        options = list(DEFAULT_COLLECTION_OPTIONS)
        custom_collections = self._rankings_custom_collections()
        options.extend(
            (str(collection.name), str(collection.collection_id))
            for collection in sorted(
                custom_collections.values(),
                key=lambda item: str(getattr(item, "name", "")).casefold(),
            )
            if str(getattr(collection, "collection_id", "")).strip()
        )
        return options

    def _rankings_selected_collection_id(self) -> str:
        combo = getattr(self, "rankings_collection_combo", None)
        if isinstance(combo, QComboBox):
            combo_value = combo.currentData()
            if combo_value is not None:
                return normalize_collection_id(combo_value)
        return normalize_collection_id(
            getattr(self, "_rankings_collection_id", DEFAULT_COLLECTION_ALL)
        )

    def _sync_rankings_collection_combo(self) -> None:
        combo = getattr(self, "rankings_collection_combo", None)
        if not isinstance(combo, QComboBox):
            return
        current_id = self._rankings_selected_collection_id()
        options = self._rankings_collection_options()
        combo.blockSignals(True)
        try:
            combo.clear()
            for label, collection_id in options:
                combo.addItem(label, normalize_collection_id(collection_id))
            selected_index = combo.findData(current_id)
            if selected_index < 0:
                selected_index = combo.findData(DEFAULT_COLLECTION_ALL)
            combo.setCurrentIndex(selected_index if selected_index >= 0 else 0)
            self._rankings_collection_id = normalize_collection_id(
                combo.currentData() or DEFAULT_COLLECTION_ALL
            )
        finally:
            combo.blockSignals(False)

    def _on_rankings_collection_changed(self, _index: int) -> None:
        selected_id = self._rankings_selected_collection_id()
        if selected_id == getattr(
            self, "_rankings_collection_id", DEFAULT_COLLECTION_ALL
        ):
            return
        self._rankings_collection_id = selected_id
        self._rankings_trait_visible_limits = {}
        self._rankings_sign_visible_limits = {}
        sorted_cache = getattr(self, "_rankings_traits_sorted_order_cache", None)
        if isinstance(sorted_cache, dict):
            sorted_cache.clear()
        self._stop_rankings_trait_worker(wait_msecs=0)
        self._refresh_rankings_panel()

    def _refresh_rankings_panel(self, sections: set[str] | None = None) -> None:
        self._sync_rankings_collection_combo()
        super()._refresh_rankings_panel(sections)

    def _rankings_database_chart_uids(self) -> set[str]:
        chart_uids = super()._rankings_database_chart_uids()
        collection_id = self._rankings_selected_collection_id()
        if collection_id == DEFAULT_COLLECTION_ALL or not chart_uids:
            return chart_uids

        custom_collections = self._rankings_custom_collections()
        chart_ids_by_uid = get_chart_ids_by_uid(chart_uids)
        scoped_uids: set[str] = set()
        for chart_uid in chart_uids:
            chart_id = chart_ids_by_uid.get(chart_uid)
            if chart_id is None:
                continue
            chart = self._get_chart_for_filter(int(chart_id))
            if chart is None or self._is_placeholder_chart(chart):
                continue
            if chart_belongs_to_collection(
                collection_id,
                chart=chart,
                source=getattr(chart, "source", None),
                custom_collections=custom_collections,
                chart_id=int(chart_id),
                chart_uid=chart_uid,
            ):
                scoped_uids.add(chart_uid)
        return scoped_uids

    def _rankings_trait_likelihood_cache_complete(
        self,
        *,
        chart_uids_by_id: dict[int, str],
        trait_signature: tuple[tuple[str, str, str], ...],
        selected_trait_name: str,
    ) -> bool:
        allowed_uids = self._rankings_database_chart_uids()
        scoped_chart_uids_by_id = {
            int(chart_id): chart_uid
            for chart_id, chart_uid in chart_uids_by_id.items()
            if self._normalize_rankings_chart_uid(chart_uid) in allowed_uids
        }
        return super()._rankings_trait_likelihood_cache_complete(
            chart_uids_by_id=scoped_chart_uids_by_id,
            trait_signature=trait_signature,
            selected_trait_name=selected_trait_name,
        )
