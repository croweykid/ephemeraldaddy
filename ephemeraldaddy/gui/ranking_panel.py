# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.
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
from ephemeraldaddy.core.db import get_chart_ids_by_uid, get_chart_uid_map, load_dominant_sign_weights
from ephemeraldaddy.gui.features.settings.traits import list_traits
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_sign_weights as _calculate_dominant_sign_weights,
)
from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import trait_snapshot_averages


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

    @staticmethod
    def _normalize_rankings_chart_uid(raw_uid: object) -> str:
        return str(raw_uid or "").strip().upper()

    def _rankings_database_chart_uids(self) -> set[str]:
        """Return current database chart UIDs from live dialog rows, not stale metrics cache."""
        chart_uids: set[str] = set()
        normalize_chart_row = getattr(self, "_normalize_chart_row", None)
        pending_legacy_ids: list[int] = []
        for row in getattr(self, "_chart_rows", []) or []:
            chart_id: int | None = None
            chart_uid = ""
            if callable(normalize_chart_row):
                normalized = normalize_chart_row(row)
                if normalized is not None:
                    chart_id = int(normalized[0])
                    chart_uid = self._normalize_rankings_chart_uid(
                        normalized[30] if len(normalized) > 30 else ""
                    )
            if chart_id is None:
                try:
                    chart_id = int(row[0])
                except (TypeError, ValueError, IndexError):
                    continue
                try:
                    chart_uid = self._normalize_rankings_chart_uid(row[30])
                except (TypeError, IndexError):
                    chart_uid = ""
            chart = self._get_chart_for_filter(chart_id)
            if chart is None or self._is_placeholder_chart(chart):
                continue
            if not chart_uid:
                chart_uid = self._normalize_rankings_chart_uid(getattr(chart, "chart_uid", ""))
            if chart_uid:
                chart_uids.add(chart_uid)
            else:
                pending_legacy_ids.append(chart_id)
        if pending_legacy_ids:
            chart_uids.update(
                self._normalize_rankings_chart_uid(uid)
                for uid in get_chart_uid_map(pending_legacy_ids).values()
                if uid
            )
        return chart_uids

    def _rankings_database_legacy_chart_ids(self, chart_uids: set[str]) -> set[int]:
        """Resolve current Rankings chart UIDs to legacy IDs for existing scoring APIs."""
        return {int(chart_id) for chart_id in get_chart_ids_by_uid(chart_uids).values()}

    def _refresh_rankings_after_hidden_chart_change(self, changed_chart_uids: set[str] | None = None) -> None:
        """Refresh the visible Rankings panel after chart hide/unhide changes."""
        if getattr(self, "_active_left_panel", None) != "rankings":
            return
        if not getattr(self, "_left_panel_visible", False):
            return
        self._refresh_rankings_panel()

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

    def _rankings_trait_likelihood_cache_complete(
        self,
        *,
        chart_ids: set[int],
        trait_signature: tuple[tuple[str, str, str], ...],
        selected_trait_name: str,
    ) -> bool:
        """Return whether cached per-chart trait scores can rank the selected trait."""
        if not selected_trait_name:
            return False
        selected_trait_key = next(
            (trait_key for trait_key in trait_signature if trait_key[0] == selected_trait_name),
            None,
        )
        if selected_trait_key is None:
            return False

        cache_revision = int(getattr(self, "_database_metrics_cache_revision", 0))
        likelihood_cache = getattr(self, "_traits_distribution_chart_likelihood_cache", None)
        individual_cache = getattr(self, "_traits_distribution_individual_likelihood_cache", None)
        profile_cache = getattr(self, "_traits_distribution_individual_profile_likelihood_cache", None)
        profile_token_cache = getattr(self, "_traits_distribution_individual_profile_token_cache", None)
        if not (
            isinstance(likelihood_cache, dict)
            or isinstance(individual_cache, dict)
            or isinstance(profile_cache, dict)
        ):
            return False

        hidden_chart_ids = {int(chart_id) for chart_id in getattr(self, "_hidden_chart_ids", set())}
        chart_tokens = self._traits_distribution_chart_tokens()
        for chart_id in sorted({int(chart_id) for chart_id in chart_ids}):
            if chart_id in hidden_chart_ids:
                continue
            chart = self._get_chart_for_filter(chart_id)
            if chart is None or self._is_placeholder_chart(chart):
                continue

            chart_cache_key = (cache_revision, trait_signature, chart_id)
            if isinstance(likelihood_cache, dict):
                likelihoods = likelihood_cache.get(chart_cache_key)
                if isinstance(likelihoods, dict) and selected_trait_name in likelihoods:
                    continue

            if isinstance(individual_cache, dict) and (selected_trait_key, chart_id) in individual_cache:
                continue

            if isinstance(profile_cache, dict) and isinstance(profile_token_cache, dict):
                profile_cache_key = (selected_trait_key[2], chart_id)
                cached_chart_token = str(profile_token_cache.get(profile_cache_key, "") or "")
                current_chart_token = chart_tokens.get(chart_id)
                if (
                    cached_chart_token
                    and cached_chart_token == current_chart_token
                    and profile_cache_key in profile_cache
                ):
                    continue

            return False
        return True

    def _refresh_rankings_panel(self) -> None:
        if not hasattr(self, "rankings_traits_label"):
            return
        database_chart_uids = self._rankings_database_chart_uids()
        database_chart_ids = self._rankings_database_legacy_chart_ids(database_chart_uids)
        selected_trait_name = self._sync_rankings_trait_combo()
        trait_items = list_traits(active_only=True)
        trait_signature = self._traits_distribution_signature(trait_items)
        database_values: dict[str, float] = {}
        cache_warmed = False
        parsed_percent: float | None = 100.0
        if selected_trait_name:
            requested_trait_names = {name for name, _color, _profile in trait_signature}
            try:
                snapshot_averages = trait_snapshot_averages(trait_items)
            except Exception:
                snapshot_averages = {}
            if requested_trait_names and requested_trait_names.issubset(set(snapshot_averages)):
                database_values = {
                    name: float(snapshot_averages[name]) / 100.0
                    for name in requested_trait_names
                }
                cache_warmed = True
                parsed_percent = 100.0
                if not isinstance(getattr(self, "_traits_distribution_chart_likelihood_cache", None), dict):
                    self._load_traits_distribution_likelihood_cache()
                if not self._rankings_trait_likelihood_cache_complete(
                    chart_ids=database_chart_ids,
                    trait_signature=trait_signature,
                    selected_trait_name=selected_trait_name,
                ):
                    database_values = {}
                    cache_warmed = False
            if not database_values:
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
        trait_uid_map = get_chart_uid_map(row.get("chart_id") for row in trait_rankings)
        for row in trait_rankings:
            try:
                chart_uid = trait_uid_map.get(int(row.get("chart_id")))
            except (TypeError, ValueError):
                chart_uid = None
            if chart_uid:
                row["chart_uid"] = chart_uid
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
        chart_uids_by_id = get_chart_uid_map(normalized_chart_ids)
        rows: list[dict[str, Any]] = []
        hidden_chart_uids = {
            self._normalize_rankings_chart_uid(chart_uid)
            for chart_uid in getattr(self, "_hidden_chart_uids", set())
        }
        db_average = 0.0
        db_count = 0
        cache = getattr(self, "_database_metrics_cache", None)
        if isinstance(cache, dict):
            total_weight = float(cache.get("dominant_sign_total_weight", 0.0) or 0.0)
            totals = cache.get("dominant_sign_totals", {})
            if total_weight:
                db_average = float(totals.get(selected_sign, 0.0)) / total_weight
        for chart_id in normalized_chart_ids:
            chart_uid = chart_uids_by_id.get(int(chart_id), "")
            normalized_chart_uid = self._normalize_rankings_chart_uid(chart_uid)
            if normalized_chart_uid in hidden_chart_uids:
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
            chart_uid = normalized_chart_uid or self._normalize_rankings_chart_uid(getattr(chart, "chart_uid", ""))
            rows.append(
                {
                    "chart_uid": chart_uid,
                    "name": str(getattr(chart, "name", "") or f"Chart {chart_uid or chart_id}"),
                    "value": value,
                }
            )
        if not db_average and db_count:
            db_average = sum(float(row["value"]) for row in rows) / float(db_count)
        rows.sort(key=lambda row: (-float(row["value"]), str(row["name"]).casefold()))
        table_rows = []
        for rank, row in enumerate(rows[:10], start=1):
            chart_uid = html.escape(str(row.get("chart_uid", "") or ""))
            name = html.escape(str(row["name"]))
            value = float(row["value"]) * 100.0
            deviation = value - (db_average * 100.0)
            deviation_color = "#90ee90" if deviation >= 0 else "#ffb3b3"
            table_rows.append(
                "<tr>"
                f"<td style='padding:1px 8px 1px 0; color:#9a9a9a; text-align:right;'>{rank}</td>"
                f"<td style='padding:1px 8px 1px 0;'><a href='chart:{chart_uid}' style='color:#f0f0f0; text-decoration:none;'>{name}</a></td>"
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
