"""Database View Rankings panel helpers.

This module keeps the Rankings left-panel UI and ranking refresh logic outside
``app.py`` so the central Database View file stays focused on window wiring.
"""

from __future__ import annotations

import html
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ephemeraldaddy.core.interpretations import ZODIAC_NAMES
from ephemeraldaddy.core.db import load_dominant_sign_weights
from ephemeraldaddy.gui.features.settings.traits import list_traits
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_sign_weights as _calculate_dominant_sign_weights,
)


class RankingsPanelMixin:
    """Mixin that builds and refreshes the Database View Rankings panel."""

    def _build_rankings_panel(self) -> QWidget:
        """Build the Database View Rankings left panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QLabel("🏆 Rankings")
        header.setObjectName("rankings_panel_header_label")
        header.setStyleSheet("font-weight: 700; color: #f5f5f5; font-size: 12pt;")
        layout.addWidget(header)

        traits_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "🧬Traits",
            expanded=True,
        )
        trait_row = QWidget()
        trait_row_layout = QHBoxLayout(trait_row)
        trait_row_layout.setContentsMargins(0, 0, 0, 0)
        trait_row_layout.setSpacing(6)
        trait_label = QLabel("Top charts for trait:")
        trait_label.setStyleSheet("color: #cfcfcf; font-size: 8pt;")
        trait_row_layout.addWidget(trait_label)
        self.rankings_trait_combo = QComboBox()
        self.rankings_trait_combo.setMinimumContentsLength(22)
        self.rankings_trait_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.rankings_trait_combo.currentIndexChanged.connect(
            lambda _index: self._refresh_rankings_panel()
        )
        trait_row_layout.addWidget(self.rankings_trait_combo, 1)
        traits_layout.addWidget(trait_row)
        self.rankings_traits_label = QLabel("")
        self.rankings_traits_label.setTextFormat(Qt.RichText)
        self.rankings_traits_label.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
        self.rankings_traits_label.setOpenExternalLinks(False)
        self.rankings_traits_label.linkActivated.connect(
            self._on_traits_distribution_rank_chart_link_activated
        )
        self.rankings_traits_label.setWordWrap(True)
        self.rankings_traits_label.setStyleSheet("color: #d8d8d8; padding: 2px 0 6px 0;")
        traits_layout.addWidget(self.rankings_traits_label)

        signs_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "♏ Sign Dominance",
            expanded=True,
        )
        sign_row = QWidget()
        sign_row_layout = QHBoxLayout(sign_row)
        sign_row_layout.setContentsMargins(0, 0, 0, 0)
        sign_row_layout.setSpacing(6)
        sign_label = QLabel("Most dominant sign:")
        sign_label.setStyleSheet("color: #cfcfcf; font-size: 8pt;")
        sign_row_layout.addWidget(sign_label)
        self.rankings_sign_combo = QComboBox()
        self.rankings_sign_combo.addItems(list(ZODIAC_NAMES))
        self.rankings_sign_combo.currentIndexChanged.connect(
            lambda _index: self._refresh_rankings_panel()
        )
        sign_row_layout.addWidget(self.rankings_sign_combo, 1)
        signs_layout.addWidget(sign_row)
        self.rankings_signs_label = QLabel("")
        self.rankings_signs_label.setTextFormat(Qt.RichText)
        self.rankings_signs_label.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
        self.rankings_signs_label.setOpenExternalLinks(False)
        self.rankings_signs_label.linkActivated.connect(
            self._on_traits_distribution_rank_chart_link_activated
        )
        self.rankings_signs_label.setWordWrap(True)
        self.rankings_signs_label.setStyleSheet("color: #d8d8d8; padding: 2px 0 6px 0;")
        signs_layout.addWidget(self.rankings_signs_label)
        layout.addStretch(1)
        return panel

    def _rankings_database_chart_ids(self) -> set[int]:
        cache = getattr(self, "_database_metrics_cache", None)
        if isinstance(cache, dict) and cache.get("chart_ids"):
            return {int(chart_id) for chart_id in cache.get("chart_ids", set())}
        ids: set[int] = set()
        normalize_chart_row = getattr(self, "_normalize_chart_row", None)
        for row in getattr(self, "_chart_rows", []) or []:
            chart_id: int | None = None
            if callable(normalize_chart_row):
                normalized = normalize_chart_row(row)
                if normalized is not None:
                    chart_id = int(normalized[0])
            if chart_id is None:
                try:
                    chart_id = int(row[0])
                except (TypeError, ValueError, IndexError):
                    continue
            chart = self._get_chart_for_filter(chart_id)
            if chart is not None and not self._is_placeholder_chart(chart):
                ids.add(chart_id)
        return ids

    def _sync_rankings_trait_combo(self) -> str | None:
        combo = getattr(self, "rankings_trait_combo", None)
        if not isinstance(combo, QComboBox):
            return None
        trait_items = list_traits(active_only=True)
        active_traits = [
            trait
            for trait in trait_items
            if str(trait.get("name", "")).strip() and not bool(trait.get("archived", False))
        ]
        current_name = str(combo.currentData() or getattr(self, "_rankings_trait_name", "") or "")
        combo.blockSignals(True)
        try:
            combo.clear()
            if not active_traits:
                combo.addItem("No active traits", "")
                combo.setEnabled(False)
                self._rankings_trait_name = ""
                return None
            combo.setEnabled(True)
            combo.addItem("select a trait!", "")
            for trait in active_traits:
                name = str(trait.get("name", "")).strip()
                combo.addItem(name, name)
            selected_index = combo.findData(current_name) if current_name else 0
            combo.setCurrentIndex(selected_index if selected_index >= 0 else 0)
            selected_name = combo.currentData()
            self._rankings_trait_name = selected_name if isinstance(selected_name, str) else ""
            return self._rankings_trait_name or None
        finally:
            combo.blockSignals(False)

    def _refresh_rankings_panel(self) -> None:
        if not hasattr(self, "rankings_traits_label"):
            return
        database_chart_ids = self._rankings_database_chart_ids()
        selected_trait_name = self._sync_rankings_trait_combo()
        trait_items = list_traits(active_only=True)
        trait_signature = self._traits_distribution_signature(trait_items)
        database_values: dict[str, float] = {}
        cache_warmed = False
        parsed_percent: float | None = 100.0
        if selected_trait_name:
            database_analytics = self._collect_traits_distribution_analytics(
                database_chart_ids,
                trait_items=trait_items,
                trait_signature=trait_signature,
            )
            database_count = max(0, int(database_analytics.get("chart_count", 0)))
            totals = database_analytics.get("totals", {})
            names = list(database_analytics.get("trait_names", []))
            database_values = {
                name: (float(totals.get(name, 0.0)) / float(database_count) if database_count else 0.0)
                for name in names
            }
            cache_warmed = database_count > 0 and not bool(database_analytics.get("partial", False))
            parsed_percent = database_analytics.get("parsed_percent", 100.0)
        trait_rankings = self._traits_distribution_chart_rankings(
            chart_ids=database_chart_ids,
            trait_signature=trait_signature,
            selected_trait_name=selected_trait_name or "",
            database_values=database_values,
        )
        self.rankings_traits_label.setText(
            self._render_traits_distribution_rankings_html(
                selected_trait_name,
                trait_rankings,
                scope_label="the database",
                cache_warmed=cache_warmed,
                parsed_percent=parsed_percent,
            )
        )
        self._refresh_sign_dominance_rankings(database_chart_ids)

    def _refresh_sign_dominance_rankings(self, database_chart_ids: set[int]) -> None:
        combo = getattr(self, "rankings_sign_combo", None)
        label = getattr(self, "rankings_signs_label", None)
        if not isinstance(combo, QComboBox) or not isinstance(label, QLabel):
            return
        selected_sign = str(combo.currentText() or "").strip()
        if selected_sign not in ZODIAC_NAMES:
            label.setText("<span style='color:#9a9a9a;'>Select a sign to rank chart dominance.</span>")
            return
        normalized_chart_ids = tuple(sorted({int(chart_id) for chart_id in database_chart_ids}))
        stored_weights = load_dominant_sign_weights(list(normalized_chart_ids))
        rows: list[dict[str, Any]] = []
        hidden_chart_ids = {int(chart_id) for chart_id in getattr(self, "_hidden_chart_ids", set())}
        db_average = 0.0
        db_count = 0
        cache = getattr(self, "_database_metrics_cache", None)
        if isinstance(cache, dict):
            total_weight = float(cache.get("dominant_sign_total_weight", 0.0) or 0.0)
            totals = cache.get("dominant_sign_totals", {})
            if total_weight:
                db_average = float(totals.get(selected_sign, 0.0)) / total_weight
        for chart_id in normalized_chart_ids:
            if int(chart_id) in hidden_chart_ids:
                continue
            chart = self._get_chart_for_filter(int(chart_id))
            if chart is None or self._is_placeholder_chart(chart):
                continue
            weights = stored_weights.get(int(chart_id)) or getattr(chart, "dominant_sign_weights", None)
            if not isinstance(weights, dict):
                weights = _calculate_dominant_sign_weights(chart)
                chart.dominant_sign_weights = weights
            try:
                value = float(weights.get(selected_sign, 0.0))
            except (TypeError, ValueError):
                continue
            db_count += 1
            rows.append(
                {
                    "chart_id": int(chart_id),
                    "name": str(getattr(chart, "name", "") or f"Chart {chart_id}"),
                    "value": value,
                }
            )
        if not db_average and db_count:
            db_average = sum(float(row["value"]) for row in rows) / float(db_count)
        rows.sort(key=lambda row: (-float(row["value"]), str(row["name"]).casefold()))
        table_rows = []
        for rank, row in enumerate(rows[:10], start=1):
            chart_id = int(row["chart_id"])
            name = html.escape(str(row["name"]))
            value = float(row["value"]) * 100.0
            deviation = value - (db_average * 100.0)
            deviation_color = "#90ee90" if deviation >= 0 else "#ffb3b3"
            table_rows.append(
                "<tr>"
                f"<td style='padding:1px 8px 1px 0; color:#9a9a9a; text-align:right;'>{rank}</td>"
                f"<td style='padding:1px 8px 1px 0;'><a href='chart:{chart_id}' style='color:#f0f0f0; text-decoration:none;'>{name}</a></td>"
                f"<td style='padding:1px 8px 1px 0; color:#d8d8d8; text-align:right;'>{value:.1f}%</td>"
                f"<td style='padding:1px 0; color:{deviation_color}; text-align:right;'>{deviation:+.1f}</td>"
                "</tr>"
            )
        safe_sign = html.escape(selected_sign)
        if not table_rows:
            label.setText(
                f"<span style='color:#9a9a9a;'>No charts are available to rank for <b>{safe_sign}</b>.</span>"
            )
            return
        label.setText(
            f"<div style='padding-bottom:3px;'>Top 10 charts by <b>{safe_sign}</b> dominance in the database.</div>"
            "<table cellspacing='0' cellpadding='0' style='width:100%;'>"
            "<tr><th style='padding:1px 8px 2px 0; color:#f5f5f5; text-align:right;'>#</th>"
            "<th style='padding:1px 8px 2px 0; color:#f5f5f5; text-align:left;'>chart</th>"
            "<th style='padding:1px 8px 2px 0; color:#f5f5f5; text-align:right;'>score</th>"
            "<th style='padding:1px 0 2px 0; color:#f5f5f5; text-align:right;'>vs DB</th></tr>"
            f"{''.join(table_rows)}</table>"
        )
