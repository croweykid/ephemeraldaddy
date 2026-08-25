# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.
"""Database View Rankings panel helpers.

This module keeps the Rankings left-panel UI and ranking refresh logic outside
``app.py`` so the central Database View file stays focused on window wiring.
"""

from __future__ import annotations

import html
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ephemeraldaddy.core.interpretations import (
    SIGN_COLORS,
    ZODIAC_NAMES,
    ZODIAC_SIGNS,
)
from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.core.db import (
    get_chart_ids_by_uid,
    get_chart_uid_map,
    load_dominant_sign_weights,
)
from ephemeraldaddy.gui.features.settings.traits import list_traits
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_sign_weights as _calculate_dominant_sign_weights,
)
from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import (
    trait_snapshot_averages,
)
from ephemeraldaddy.gui.features.charts.presentation import sign_for_longitude
from ephemeraldaddy.gui.style import (
    DROPDOWN_ACCENT_ITEM_TEXT_COLOR,
    DROPDOWN_MUTED_ITEM_TEXT_COLOR,
    set_dropdown_item_text_color,
)
from ephemeraldaddy.gui.tooltips import (
    sign_dominance_tooltip_html,
    set_link_hover_tooltip,
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

        self._rankings_section_expanded = {"traits": True, "sign_dominance": True}
        # Rankings are derived from the complete database row set rather than
        # the filtered/ordered rows rendered by ``_populate_list``.  Keep the
        # initial refresh pending until the panel is actually visible.
        self._rankings_data_dirty = True
        traits_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "🧬Traits",
            expanded=True,
            on_toggled=lambda expanded: self._on_rankings_section_toggled(
                "traits", expanded
            ),
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
            lambda _index: self._refresh_rankings_panel({"traits"})
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
        self.rankings_traits_label.setStyleSheet(
            "color: #d8d8d8; padding: 2px 0 6px 0;"
        )
        traits_layout.addWidget(self.rankings_traits_label)

        signs_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "♏ Sign Dominance",
            expanded=True,
            on_toggled=lambda expanded: self._on_rankings_section_toggled(
                "sign_dominance", expanded
            ),
        )
        most_sign_heading = QLabel("Most Dominant Sign")
        most_sign_heading.setStyleSheet(
            "font-weight: 700; color: #f5f5f5; font-size: 9pt;"
        )
        signs_layout.addWidget(most_sign_heading)
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
            lambda _index: self._refresh_rankings_panel({"sign_dominance"})
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
        self.rankings_signs_label.linkHovered.connect(
            lambda link: set_link_hover_tooltip(
                self.rankings_signs_label,
                link,
                getattr(self, "_rankings_most_sign_dominance_tooltips", {}),
            )
        )
        self.rankings_signs_label.setWordWrap(True)
        self.rankings_signs_label.setStyleSheet("color: #d8d8d8; padding: 2px 0 6px 0;")
        signs_layout.addWidget(self.rankings_signs_label)

        least_sign_heading = QLabel("Least Dominant Sign")
        least_sign_heading.setStyleSheet(
            "font-weight: 700; color: #f5f5f5; font-size: 9pt;"
        )
        signs_layout.addWidget(least_sign_heading)
        least_sign_row = QWidget()
        least_sign_row_layout = QHBoxLayout(least_sign_row)
        least_sign_row_layout.setContentsMargins(0, 0, 0, 0)
        least_sign_row_layout.setSpacing(6)
        least_sign_label = QLabel("Least dominant sign:")
        least_sign_label.setStyleSheet("color: #cfcfcf; font-size: 8pt;")
        least_sign_row_layout.addWidget(least_sign_label)
        self.rankings_least_sign_combo = QComboBox()
        self.rankings_least_sign_combo.addItems(list(ZODIAC_NAMES))
        self.rankings_least_sign_combo.currentIndexChanged.connect(
            lambda _index: self._refresh_rankings_panel({"sign_dominance"})
        )
        least_sign_row_layout.addWidget(self.rankings_least_sign_combo, 1)
        signs_layout.addWidget(least_sign_row)
        self.rankings_least_signs_label = QLabel("")
        self.rankings_least_signs_label.setTextFormat(Qt.RichText)
        self.rankings_least_signs_label.setTextInteractionFlags(
            Qt.LinksAccessibleByMouse
        )
        self.rankings_least_signs_label.setOpenExternalLinks(False)
        self.rankings_least_signs_label.linkActivated.connect(
            self._on_traits_distribution_rank_chart_link_activated
        )
        self.rankings_least_signs_label.linkHovered.connect(
            lambda link: set_link_hover_tooltip(
                self.rankings_least_signs_label,
                link,
                getattr(self, "_rankings_least_sign_dominance_tooltips", {}),
            )
        )
        self.rankings_least_signs_label.setWordWrap(True)
        self.rankings_least_signs_label.setStyleSheet(
            "color: #d8d8d8; padding: 2px 0 6px 0;"
        )
        signs_layout.addWidget(self.rankings_least_signs_label)
        layout.addStretch(1)
        return panel

    def _on_rankings_section_toggled(self, section: str, expanded: bool) -> None:
        """Refresh a Rankings section only when it becomes visible."""
        self._rankings_section_expanded[section] = expanded
        if not expanded:
            return
        if getattr(self, "_active_left_panel", None) != "rankings":
            return
        if not getattr(self, "_left_panel_visible", False):
            return
        is_collapsed = getattr(self, "_is_left_panel_collapsed", None)
        if callable(is_collapsed) and is_collapsed():
            return
        self._refresh_rankings_panel({section})

    def _refresh_visible_rankings_sections(self) -> None:
        """Refresh expanded Rankings content when changed data is visible."""
        if not getattr(self, "_rankings_data_dirty", True):
            return
        if getattr(self, "_active_left_panel", None) != "rankings":
            return
        if not getattr(self, "_left_panel_visible", False):
            return
        is_collapsed = getattr(self, "_is_left_panel_collapsed", None)
        if callable(is_collapsed) and is_collapsed():
            return
        expanded = {
            section
            for section, is_expanded in getattr(
                self, "_rankings_section_expanded", {}
            ).items()
            if is_expanded
        }
        if expanded:
            self._refresh_rankings_panel(expanded)
            self._rankings_data_dirty = False

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
                chart_uid = self._normalize_rankings_chart_uid(
                    getattr(chart, "chart_uid", "")
                )
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

    def _refresh_rankings_after_hidden_chart_change(
        self, changed_chart_uids: set[str] | None = None
    ) -> None:
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
            if str(trait.get("name", "")).strip()
            and not bool(trait.get("archived", False))
        ]
        active_traits.sort(
            key=lambda trait: str(trait.get("name", "")).strip().casefold()
        )
        current_name = str(
            combo.currentData() or getattr(self, "_rankings_trait_name", "") or ""
        )
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
                name_color = (
                    DROPDOWN_MUTED_ITEM_TEXT_COLOR
                    if bool(trait.get("bundled", False))
                    else DROPDOWN_ACCENT_ITEM_TEXT_COLOR
                )
                set_dropdown_item_text_color(combo, combo.count() - 1, name_color)
            selected_index = combo.findData(current_name) if current_name else 0
            combo.setCurrentIndex(selected_index if selected_index >= 0 else 0)
            selected_name = combo.currentData()
            self._rankings_trait_name = (
                selected_name if isinstance(selected_name, str) else ""
            )
            return self._rankings_trait_name or None
        finally:
            combo.blockSignals(False)

    def _refresh_rankings_trait_choices_after_archive(
        self,
        *,
        trait_name: str,
        archived: bool,
    ) -> None:
        """Splice an archived Trait choice without touching ranking caches."""
        combo = getattr(self, "rankings_trait_combo", None)
        if not isinstance(combo, QComboBox):
            return
        if not archived:
            self._sync_rankings_trait_combo()
            return

        trait_index = combo.findData(str(trait_name or "").strip())
        if trait_index < 0:
            return
        archived_trait_was_selected = combo.currentIndex() == trait_index
        combo.blockSignals(True)
        try:
            combo.removeItem(trait_index)
            if archived_trait_was_selected:
                combo.setCurrentIndex(0 if combo.count() else -1)
                self._rankings_trait_name = ""
        finally:
            combo.blockSignals(False)
        if not archived_trait_was_selected or not hasattr(
            self, "rankings_traits_label"
        ):
            return
        self.rankings_traits_label.setText(
            self._render_traits_distribution_rankings_html(
                None,
                [],
                scope_label="the database",
                cache_warmed=True,
                parsed_percent=100.0,
            )
        )

    def _rankings_trait_likelihood_cache_complete(
        self,
        *,
        chart_uids_by_id: dict[int, str],
        trait_signature: tuple[tuple[str, str, str], ...],
        selected_trait_name: str,
    ) -> bool:
        """Return whether cached per-chart UID trait scores can rank the selected trait."""
        if not selected_trait_name:
            return False
        selected_trait_key = next(
            (
                trait_key
                for trait_key in trait_signature
                if trait_key[0] == selected_trait_name
            ),
            None,
        )
        if selected_trait_key is None:
            return False

        cache_revision = int(getattr(self, "_database_metrics_cache_revision", 0))
        likelihood_cache = getattr(
            self, "_traits_distribution_chart_likelihood_cache", None
        )
        individual_cache = getattr(
            self, "_traits_distribution_individual_likelihood_cache", None
        )
        profile_cache = getattr(
            self, "_traits_distribution_individual_profile_likelihood_cache", None
        )
        profile_token_cache = getattr(
            self, "_traits_distribution_individual_profile_token_cache", None
        )
        if not (
            isinstance(likelihood_cache, dict)
            or isinstance(individual_cache, dict)
            or isinstance(profile_cache, dict)
        ):
            return False

        hidden_chart_uids = {
            self._normalize_rankings_chart_uid(chart_uid)
            for chart_uid in getattr(self, "_hidden_chart_uids", set())
        }
        journal_backed_cache = bool(
            int(
                getattr(
                    self, "_traits_distribution_likelihood_cache_change_sequence", 0
                )
                or 0
            )
        )
        chart_tokens: dict[str, str] | None = None
        for chart_id, chart_uid in sorted(chart_uids_by_id.items()):
            chart_uid = self._normalize_rankings_chart_uid(chart_uid)
            if not chart_uid or chart_uid in hidden_chart_uids:
                continue
            chart_cache_key = (cache_revision, trait_signature, chart_uid)
            if isinstance(likelihood_cache, dict):
                likelihoods = likelihood_cache.get(chart_cache_key)
                if isinstance(likelihoods, dict) and selected_trait_name in likelihoods:
                    continue

            if (
                isinstance(individual_cache, dict)
                and (selected_trait_key, chart_uid) in individual_cache
            ):
                continue

            if isinstance(profile_cache, dict) and isinstance(
                profile_token_cache, dict
            ):
                profile_cache_key = (selected_trait_key[2], chart_uid)
                if journal_backed_cache and profile_cache_key in profile_cache:
                    continue
                cached_chart_token = str(
                    profile_token_cache.get(profile_cache_key, "") or ""
                )
                if chart_tokens is None:
                    chart_tokens = self._traits_distribution_chart_tokens()
                current_chart_token = chart_tokens.get(chart_uid)
                if (
                    cached_chart_token
                    and cached_chart_token == current_chart_token
                    and profile_cache_key in profile_cache
                ):
                    continue

            chart = self._get_chart_for_filter(chart_id)
            if chart is None or self._is_placeholder_chart(chart):
                continue
            return False
        return True

    def _schedule_rankings_traits_continuation(self, selected_trait_name: str) -> None:
        """Continue an incomplete trait ranking without blocking the UI thread.

        The analytics collector deliberately observes a time budget.  A Rankings
        refresh used to consume one budget and then simply leave the partial
        result on screen forever.  Keep asking it for another small slice; the
        per-chart cache makes every slice resume at the first missing chart.
        """
        token = (
            str(selected_trait_name or ""),
            int(getattr(self, "_database_metrics_cache_revision", 0)),
        )
        self._rankings_traits_continuation_token = token

        def continue_ranking() -> None:
            if getattr(self, "_rankings_traits_continuation_token", None) != token:
                return
            combo = getattr(self, "rankings_trait_combo", None)
            if (
                not isinstance(combo, QComboBox)
                or str(combo.currentData() or "") != token[0]
            ):
                return
            rankings_visible = getattr(
                self, "_active_left_panel", None
            ) == "rankings" and bool(getattr(self, "_left_panel_visible", False))
            is_collapsed = getattr(self, "_is_left_panel_collapsed", None)
            if callable(is_collapsed) and is_collapsed():
                rankings_visible = False
            if not rankings_visible:
                # The queued callback is the only continuation for this partial
                # pass.  Preserve it as dirty work so showing Rankings again
                # restarts warmup through _refresh_visible_rankings_sections.
                self._rankings_data_dirty = True
                return
            self._refresh_rankings_panel({"traits"})

        QTimer.singleShot(0, continue_ranking)

    def _refresh_rankings_panel(self, sections: set[str] | None = None) -> None:
        if not hasattr(self, "rankings_traits_label"):
            return
        requested_sections = sections or {"traits", "sign_dominance"}
        expanded_sections = getattr(self, "_rankings_section_expanded", {})
        requested_sections = {
            section
            for section in requested_sections
            if expanded_sections.get(section, False)
        }
        if not requested_sections:
            return
        database_chart_uids = self._rankings_database_chart_uids()
        database_chart_ids = self._rankings_database_legacy_chart_ids(
            database_chart_uids
        )
        if "traits" not in requested_sections:
            self._refresh_sign_dominance_rankings(database_chart_ids)
            return
        selected_trait_name = self._sync_rankings_trait_combo()
        trait_items = list_traits(active_only=True)
        # Ranking one trait must not warm every active trait for every chart.
        # Besides doing unnecessary work, that made an 8-second partial pass
        # advance only a few charts.  A one-trait signature is independently
        # cacheable and is sufficient both for ranking and its DB comparison.
        ranking_trait_items = (
            [
                trait
                for trait in trait_items
                if str(trait.get("name", "")).strip() == selected_trait_name
            ]
            if selected_trait_name
            else []
        )
        trait_signature = self._traits_distribution_signature(ranking_trait_items)
        database_values: dict[str, float] = {}
        snapshot_database_values: dict[str, float] = {}
        cache_warmed = False
        parsed_percent: float | None = 100.0
        if selected_trait_name:
            requested_trait_names = {selected_trait_name}
            try:
                snapshot_averages = trait_snapshot_averages(ranking_trait_items)
            except Exception:
                snapshot_averages = {}
            if requested_trait_names and requested_trait_names.issubset(
                set(snapshot_averages)
            ):
                database_values = {
                    name: float(snapshot_averages[name]) / 100.0
                    for name in requested_trait_names
                }
                snapshot_database_values = dict(database_values)
                cache_warmed = True
                parsed_percent = 100.0
                if not isinstance(
                    getattr(self, "_traits_distribution_chart_likelihood_cache", None),
                    dict,
                ):
                    self._load_traits_distribution_likelihood_cache()
                if not self._rankings_trait_likelihood_cache_complete(
                    chart_uids_by_id=self._traits_distribution_chart_uid_by_id(),
                    trait_signature=trait_signature,
                    selected_trait_name=selected_trait_name,
                ):
                    database_values = {}
                    cache_warmed = False
            if not database_values:
                database_analytics = self._collect_traits_distribution_analytics(
                    database_chart_ids,
                    trait_items=ranking_trait_items,
                    trait_signature=trait_signature,
                    # Yield frequently so the progress text and the rest of the
                    # application remain responsive while a cold cache warms.
                    time_budget_seconds=0.1,
                )
                database_count = max(0, int(database_analytics.get("chart_count", 0)))
                totals = database_analytics.get("totals", {})
                names = list(database_analytics.get("trait_names", []))
                database_values = {
                    name: (
                        float(totals.get(name, 0.0)) / float(database_count)
                        if database_count
                        else 0.0
                    )
                    for name in names
                }
                # Norms define the comparison baseline.  The local collector is
                # invoked here only to populate missing per-chart scores.
                if snapshot_database_values:
                    database_values = snapshot_database_values
                cache_warmed = database_count > 0 and not bool(
                    database_analytics.get("partial", False)
                )
                parsed_percent = database_analytics.get("parsed_percent", 100.0)
                if bool(database_analytics.get("partial", False)):
                    self._schedule_rankings_traits_continuation(selected_trait_name)
                else:
                    self._rankings_traits_continuation_token = None
            else:
                self._rankings_traits_continuation_token = None
        database_chart_uids = tuple(
            sorted(
                str(chart_uid).strip().upper()
                for chart_uid in get_chart_uid_map(database_chart_ids).values()
                if str(chart_uid or "").strip()
            )
        )
        trait_rankings = self._traits_distribution_chart_rankings(
            chart_uids=database_chart_uids,
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
        if "sign_dominance" in requested_sections:
            self._refresh_sign_dominance_rankings(database_chart_ids)

    @staticmethod
    def _rankings_chart_body_sign(chart: Any, body: str) -> str | None:
        positions = getattr(chart, "positions", None) or {}
        longitude = positions.get(body)
        if longitude is None:
            return None
        try:
            return sign_for_longitude(float(longitude))
        except (TypeError, ValueError):
            return None

    def _sign_dominance_chart_name_style(self, chart: Any, selected_sign: str) -> str:
        sun_matches = self._rankings_chart_body_sign(chart, "Sun") == selected_sign
        moon_matches = self._rankings_chart_body_sign(chart, "Moon") == selected_sign
        rising_matches = (
            bool(chart_uses_houses(chart))
            and self._rankings_chart_body_sign(chart, "AS") == selected_sign
        )
        css_parts = ["text-decoration:none"]
        if not sun_matches:
            css_parts.append("font-style:italic")
        if sun_matches and moon_matches:
            css_parts.append("color:#39ff14")
        elif moon_matches and not sun_matches:
            css_parts.append("color:#5dade2")
        else:
            css_parts.append("color:#f0f0f0")
        if sun_matches and moon_matches and rising_matches:
            css_parts.append("font-weight:700")
        return "; ".join(css_parts)

    @staticmethod
    def _sign_dominance_key_html(selected_sign: str) -> str:
        """Return the visual key for chart-name styling in dominance rankings."""
        safe_sign = html.escape(selected_sign)
        entries = (
            ("font-weight:700; color:#39ff14", f"Sun/Moon/AS all in {safe_sign}"),
            ("color:#39ff14", f"Sun/Moon in {safe_sign}"),
            ("font-style:italic; color:#f0f0f0", f"AS in {safe_sign}"),
            ("color:#f0f0f0", f"Sun in {safe_sign}"),
            ("font-style:italic; color:#5dade2", f"Moon in {safe_sign}"),
        )
        return "<div style='padding:0 0 4px 8px;'>" + "<br>".join(
            f"<span style='color:#9a9a9a;'>•</span> <span style='{style};'>{text}</span>"
            for style, text in entries
        ) + "</div>"

    def _refresh_sign_dominance_rankings(self, database_chart_ids: set[int]) -> None:
        """Refresh both the most- and least-dominant sign rankings."""
        self._refresh_sign_dominance_ranking(database_chart_ids, least=False)
        self._refresh_sign_dominance_ranking(database_chart_ids, least=True)

    def _refresh_sign_dominance_ranking(
        self, database_chart_ids: set[int], *, least: bool
    ) -> None:
        combo_name = "rankings_least_sign_combo" if least else "rankings_sign_combo"
        label_name = "rankings_least_signs_label" if least else "rankings_signs_label"
        combo = getattr(self, combo_name, None)
        label = getattr(self, label_name, None)
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
        dominance_tooltips: dict[str, str] = {}
        sign_top_20_memberships: dict[str, list[str]] = {}
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
            weights = stored_weights.get(int(chart_id)) or getattr(
                chart, "dominant_sign_weights", None
            )
            if not isinstance(weights, dict):
                weights = _calculate_dominant_sign_weights(chart)
                chart.dominant_sign_weights = weights
            try:
                value = float(weights.get(selected_sign, 0.0))
            except (TypeError, ValueError):
                continue
            db_count += 1
            chart_uid = normalized_chart_uid or self._normalize_rankings_chart_uid(
                getattr(chart, "chart_uid", "")
            )
            rows.append(
                {
                    "chart_uid": chart_uid,
                    "name": str(
                        getattr(chart, "name", "") or f"Chart {chart_uid or chart_id}"
                    ),
                    "value": value,
                    "weights": weights,
                    "name_style": self._sign_dominance_chart_name_style(
                        chart, selected_sign
                    ),
                }
            )
            if chart_uid:
                dominance_tooltips[f"chart:{chart_uid}"] = sign_dominance_tooltip_html(
                    chart_name=str(getattr(chart, "name", "") or "This chart"),
                    selected_sign=selected_sign,
                    sun_sign=self._rankings_chart_body_sign(chart, "Sun"),
                    moon_sign=self._rankings_chart_body_sign(chart, "Moon"),
                    ascendant_sign=(
                        self._rankings_chart_body_sign(chart, "AS")
                        if chart_uses_houses(chart)
                        else None
                    ),
                )
        tooltip_attribute = (
            "_rankings_least_sign_dominance_tooltips"
            if least
            else "_rankings_most_sign_dominance_tooltips"
        )
        setattr(self, tooltip_attribute, dominance_tooltips)
        if not db_average and db_count:
            db_average = sum(float(row["value"]) for row in rows) / float(db_count)
        if least:
            rows = [
                row
                for row in rows
                if (row.get("weights") or {})
                and float(row["value"])
                == min(
                    float(value or 0.0) for value in (row.get("weights") or {}).values()
                )
            ]
        value_direction = 1.0 if least else -1.0
        rows.sort(
            key=lambda row: (
                value_direction * float(row["value"]),
                str(row["name"]).casefold(),
            )
        )
        sign_glyphs = dict(zip(ZODIAC_NAMES, ZODIAC_SIGNS, strict=False))
        for sign in ZODIAC_NAMES:
            sign_ranked_rows = sorted(
                rows,
                key=lambda row, sign=sign: (
                    value_direction
                    * float((row.get("weights") or {}).get(sign, 0.0) or 0.0),
                    str(row["name"]).casefold(),
                ),
            )
            for row in sign_ranked_rows[:20]:
                chart_key = str(row.get("chart_uid") or row.get("name") or "").strip()
                if chart_key:
                    sign_top_20_memberships.setdefault(chart_key, []).append(sign)

        selected_top_20_keys = [
            str(row.get("chart_uid") or row.get("name") or "").strip()
            for row in rows[:20]
        ]
        shared_top_20_ranks = [
            rank
            for rank, chart_key in enumerate(selected_top_20_keys, start=1)
            if len(sign_top_20_memberships.get(chart_key, ())) >= 2
        ]
        shared_top_20_count = len(shared_top_20_ranks)
        deepest_shared_rank = max(shared_top_20_ranks, default=0)
        display_limit = min(20, max(10 + shared_top_20_count, deepest_shared_rank))
        if least:
            display_limit = len(rows)

        table_rows = []
        for rank, row in enumerate(rows[:display_limit], start=1):
            chart_uid = html.escape(str(row.get("chart_uid", "") or ""))
            chart_key = str(row.get("chart_uid") or row.get("name") or "").strip()
            name = html.escape(str(row["name"]))
            name_style = html.escape(
                str(row.get("name_style") or "color:#f0f0f0; text-decoration:none"),
                quote=True,
            )
            glyph_html = ""
            shared_signs = sign_top_20_memberships.get(chart_key, [])
            if len(shared_signs) >= 2:
                glyph_html = " " + "".join(
                    f"<span style='color:{html.escape(str(SIGN_COLORS.get(sign, '#d8d8d8')))};'>{html.escape(sign_glyphs.get(sign, ''))}</span>"
                    for sign in shared_signs
                    if sign_glyphs.get(sign)
                )
            value = float(row["value"]) * 100.0
            deviation = value - (db_average * 100.0)
            deviation_color = (
                "#90ee90"
                if (deviation <= 0 if least else deviation >= 0)
                else "#ffb3b3"
            )
            table_rows.append(
                "<tr>"
                f"<td style='padding:1px 8px 1px 0; color:#9a9a9a; text-align:right;'>{rank}</td>"
                f"<td style='padding:1px 8px 1px 0;'><a href='chart:{chart_uid}' style='{name_style}'>{name}{glyph_html}</a></td>"
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
            f"<div style='padding-bottom:3px;'>{f'All charts whose least dominant sign is <b>{safe_sign}</b>' if least else f'Top {display_limit} charts by <b>{safe_sign}</b> dominance'} in the database.</div>"
            f"{self._sign_dominance_key_html(selected_sign)}"
            "<table cellspacing='0' cellpadding='0' style='width:100%;'>"
            "<tr><th style='padding:1px 8px 2px 0; color:#f5f5f5; text-align:right;'>#</th>"
            "<th style='padding:1px 8px 2px 0; color:#f5f5f5; text-align:left;'>chart</th>"
            "<th style='padding:1px 8px 2px 0; color:#f5f5f5; text-align:right;'>score</th>"
            "<th style='padding:1px 0 2px 0; color:#f5f5f5; text-align:right;'>vs DB</th></tr>"
            f"{''.join(table_rows)}</table>"
        )
