# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.
"""Database View Rankings panel helpers.

This module keeps the Rankings left-panel UI and ranking refresh logic outside
``app.py`` so the central Database View file stays focused on window wiring.
"""

from __future__ import annotations

import html
from typing import Any

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.core import db
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
from ephemeraldaddy.gui.features.charts.sign_dominance_ranking import (
    least_house_priority,
    resolve_complete_sign_weights,
)
from ephemeraldaddy.gui.style import (
    COLLAPSIBLE_HEADER_LEVEL_PARENT,
    DROPDOWN_ACCENT_ITEM_TEXT_COLOR,
    DROPDOWN_MUTED_ITEM_TEXT_COLOR,
    set_dropdown_item_text_color,
)
from ephemeraldaddy.gui.tooltips import (
    sign_dominance_tooltip_html,
    set_link_hover_tooltip,
)


class _RankingsTraitWorker(QObject):
    """Populate one ranking trait's chart cache outside the GUI thread."""

    progress = Signal(object, float)
    finished = Signal(object, object)
    failed = Signal(object, str)

    def __init__(
        self,
        owner: Any,
        token: object,
        chart_uids: tuple[str, ...],
        trait_items: list[dict[str, Any]],
        trait_signature: tuple[tuple[str, str, str], ...],
    ) -> None:
        super().__init__()
        self._owner = owner
        self._token = token
        self._chart_uids = chart_uids
        self._trait_items = trait_items
        self._trait_signature = trait_signature

    @Slot()
    def run(self) -> None:
        try:
            result = self._owner._collect_traits_distribution_analytics_by_uids(
                self._chart_uids,
                trait_items=self._trait_items,
                trait_signature=self._trait_signature,
                time_budget_seconds=None,
                progress_callback=lambda percent: self.progress.emit(
                    self._token, percent
                ),
                should_cancel=QThread.currentThread().isInterruptionRequested,
            )
        except Exception as exc:
            self.failed.emit(self._token, str(exc))
            return
        self.finished.emit(self._token, result)


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
        self._rankings_trait_visible_limits: dict[str, int] = {}
        self._rankings_traits_sorted_order_cache: dict[
            tuple[object, ...], tuple[int, tuple[dict[str, Any], ...]]
        ] = {}
        self._rankings_traits_last_parsed_percent = 0.0
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
            "color: #d8d8d8; padding: 2px 0 6px 0; background: transparent;"
        )
        self.rankings_traits_scroll = QScrollArea()
        self.rankings_traits_scroll.setWidgetResizable(True)
        self.rankings_traits_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.rankings_traits_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.rankings_traits_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )
        self.rankings_traits_scroll.viewport().setStyleSheet("background: transparent;")
        self.rankings_traits_scroll.setFixedHeight(24)
        self.rankings_traits_scroll.setWidget(self.rankings_traits_label)
        traits_layout.addWidget(self.rankings_traits_scroll)

        trait_more_row = QWidget()
        trait_more_row_layout = QHBoxLayout(trait_more_row)
        trait_more_row_layout.setContentsMargins(0, 0, 0, 0)
        trait_more_row_layout.setSpacing(6)
        trait_more_row_layout.addStretch(1)
        self.rankings_traits_more_button = QPushButton("show next 10")
        self.rankings_traits_more_button.setToolTip(
            "Append the next 10 already-scored charts to this trait ranking."
        )
        self.rankings_traits_more_button.clicked.connect(
            self._on_rankings_traits_show_next_clicked
        )
        self.rankings_traits_more_button.setVisible(False)
        trait_more_row_layout.addWidget(self.rankings_traits_more_button)
        traits_layout.addWidget(trait_more_row)

        signs_layout = self._add_left_panel_collapsible_section(
            panel,
            layout,
            "♏ Sign Dominance",
            expanded=True,
            nested=True,
            hierarchy_level=COLLAPSIBLE_HEADER_LEVEL_PARENT,
            on_toggled=lambda expanded: self._on_rankings_section_toggled(
                "sign_dominance", expanded
            ),
        )
        most_sign_layout = self._add_left_panel_collapsible_section(
            panel,
            signs_layout,
            "Most Dominant Sign",
            expanded=True,
            on_toggled=lambda expanded: (
                self._refresh_rankings_panel({"sign_dominance"}) if expanded else None
            ),
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
            lambda _index: self._refresh_rankings_panel({"sign_dominance"})
        )
        sign_row_layout.addWidget(self.rankings_sign_combo, 1)
        most_sign_layout.addWidget(sign_row)
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
        most_sign_layout.addWidget(self.rankings_signs_label)

        least_sign_layout = self._add_left_panel_collapsible_section(
            panel,
            signs_layout,
            "Least Dominant Sign",
            expanded=True,
            on_toggled=lambda expanded: (
                self._refresh_rankings_panel({"sign_dominance"}) if expanded else None
            ),
        )
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
        least_sign_layout.addWidget(least_sign_row)
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
        least_sign_layout.addWidget(self.rankings_least_signs_label)
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

    def _rankings_trait_visible_limit(self, trait_name: str) -> int:
        trait_name = str(trait_name or "").strip()
        if not trait_name:
            return 10
        limits = getattr(self, "_rankings_trait_visible_limits", None)
        if not isinstance(limits, dict):
            limits = {}
            self._rankings_trait_visible_limits = limits
        try:
            current_limit = int(limits.get(trait_name, 10))
        except (TypeError, ValueError):
            current_limit = 10
        current_limit = max(10, current_limit)
        limits[trait_name] = current_limit
        return current_limit

    def _sync_rankings_traits_scroll_height(self) -> None:
        scroll = getattr(self, "rankings_traits_scroll", None)
        label = getattr(self, "rankings_traits_label", None)
        if not isinstance(scroll, QScrollArea) or not isinstance(label, QLabel):
            return
        viewport_width = max(1, int(scroll.viewport().width()))
        label.setMinimumHeight(0)
        try:
            content_height = int(label.heightForWidth(viewport_width))
        except (TypeError, ValueError):
            content_height = int(label.sizeHint().height())
        if content_height <= 0:
            content_height = int(label.sizeHint().height())
        content_height = max(24, content_height + 6)
        label.setMinimumHeight(content_height)
        scroll.setFixedHeight(min(400, content_height))

    def _set_rankings_traits_html(self, rendered_html: str, *, has_more: bool) -> None:
        label = getattr(self, "rankings_traits_label", None)
        if not isinstance(label, QLabel):
            return
        scroll = getattr(self, "rankings_traits_scroll", None)
        previous_scroll_value = 0
        if isinstance(scroll, QScrollArea):
            previous_scroll_value = int(scroll.verticalScrollBar().value())
        label.setText(rendered_html)
        more_button = getattr(self, "rankings_traits_more_button", None)
        if isinstance(more_button, QPushButton):
            more_button.setVisible(bool(has_more))

        def _finish_layout() -> None:
            self._sync_rankings_traits_scroll_height()
            current_scroll = getattr(self, "rankings_traits_scroll", None)
            if isinstance(current_scroll, QScrollArea):
                bar = current_scroll.verticalScrollBar()
                bar.setValue(min(previous_scroll_value, int(bar.maximum())))

        QTimer.singleShot(0, _finish_layout)

    def _rankings_traits_sorted_cache_key(
        self,
        *,
        chart_uids: tuple[str, ...],
        trait_signature: tuple[tuple[str, str, str], ...],
        selected_trait_name: str,
        database_average_pct: float,
    ) -> tuple[object, ...]:
        hidden_chart_uids = tuple(
            sorted(
                self._normalize_rankings_chart_uid(chart_uid)
                for chart_uid in getattr(self, "_hidden_chart_uids", set())
                if self._normalize_rankings_chart_uid(chart_uid)
            )
        )
        return (
            int(getattr(self, "_database_metrics_cache_revision", 0)),
            trait_signature,
            selected_trait_name,
            chart_uids,
            hidden_chart_uids,
            float(database_average_pct),
        )

    def _rankings_traits_chart_rankings(
        self,
        *,
        chart_uids: list[str] | set[str] | tuple[str, ...],
        trait_signature: tuple[tuple[str, str, str], ...],
        selected_trait_name: str,
        database_values: dict[str, float],
        limit: int | None,
        cache_complete: bool,
    ) -> list[dict[str, Any]]:
        """Return ranked cached trait scores without recalculating chart likelihoods."""
        if not selected_trait_name:
            return []
        normalized_chart_uids = tuple(
            sorted(
                {
                    self._normalize_rankings_chart_uid(chart_uid)
                    for chart_uid in chart_uids
                    if self._normalize_rankings_chart_uid(chart_uid)
                }
            )
        )
        db_average_pct = float(database_values.get(selected_trait_name, 0.0)) * 100.0
        cache_key = self._rankings_traits_sorted_cache_key(
            chart_uids=normalized_chart_uids,
            trait_signature=trait_signature,
            selected_trait_name=selected_trait_name,
            database_average_pct=db_average_pct,
        )
        sorted_cache = getattr(self, "_rankings_traits_sorted_order_cache", None)
        if not isinstance(sorted_cache, dict):
            sorted_cache = {}
            self._rankings_traits_sorted_order_cache = sorted_cache

        cached_rows: tuple[dict[str, Any], ...] | None = None
        changed_chart_uids: set[str] | None = None
        if cache_complete:
            cached_entry = sorted_cache.get(cache_key)
            if (
                isinstance(cached_entry, tuple)
                and len(cached_entry) == 2
                and isinstance(cached_entry[0], int)
                and isinstance(cached_entry[1], tuple)
            ):
                cached_sequence = int(cached_entry[0])
                cached_rows = cached_entry[1]
                try:
                    journal_changes = db.chart_changes_since(cached_sequence)
                    latest_sequence = db.latest_chart_change_sequence()
                except Exception:
                    journal_changes = None
                    latest_sequence = cached_sequence
                if journal_changes is not None:
                    normalized_scope_uids = set(normalized_chart_uids)
                    changed_chart_uids = {
                        self._normalize_rankings_chart_uid(change.get("chart_uid", ""))
                        for change in journal_changes
                        if bool(change.get("astro_data_changed", False))
                        and self._normalize_rankings_chart_uid(change.get("chart_uid", ""))
                        in normalized_scope_uids
                    }
                    if not changed_chart_uids:
                        if latest_sequence != cached_sequence:
                            sorted_cache[cache_key] = (latest_sequence, cached_rows)
                        if limit is None:
                            return list(cached_rows)
                        return list(cached_rows[: max(0, int(limit))])

        chart_ids_by_uid = get_chart_ids_by_uid(normalized_chart_uids)
        cache_revision = int(getattr(self, "_database_metrics_cache_revision", 0))
        likelihood_cache = getattr(
            self, "_traits_distribution_chart_likelihood_cache", None
        )
        if not isinstance(likelihood_cache, dict):
            return []
        selected_trait_key = next(
            (
                trait_key
                for trait_key in trait_signature
                if trait_key[0] == selected_trait_name
            ),
            None,
        )
        if selected_trait_key is None:
            return []
        individual_cache = getattr(
            self, "_traits_distribution_individual_likelihood_cache", None
        )
        profile_cache = getattr(
            self, "_traits_distribution_individual_profile_likelihood_cache", None
        )
        profile_token_cache = getattr(
            self, "_traits_distribution_individual_profile_token_cache", None
        )
        chart_tokens: dict[str, str] | None = None
        chart_uid_by_id = self._traits_distribution_chart_uid_by_id()
        hidden_chart_uids = {
            self._normalize_rankings_chart_uid(chart_uid)
            for chart_uid in getattr(self, "_hidden_chart_uids", set())
        }
        if cached_rows is not None and changed_chart_uids:
            rows = [
                dict(row)
                for row in cached_rows
                if self._normalize_rankings_chart_uid(row.get("chart_uid", ""))
                not in changed_chart_uids
            ]
            ranking_chart_uids = tuple(
                chart_uid
                for chart_uid in normalized_chart_uids
                if chart_uid in changed_chart_uids
            )
        else:
            rows: list[dict[str, Any]] = []
            ranking_chart_uids = normalized_chart_uids
        for chart_uid in ranking_chart_uids:
            if chart_uid in hidden_chart_uids:
                continue
            chart_id = chart_ids_by_uid.get(chart_uid)
            if chart_id is None:
                continue
            chart = self._get_chart_for_filter(int(chart_id))
            if chart is None or self._is_placeholder_chart(chart):
                continue
            resolved_chart_uid = chart_uid_by_id.get(int(chart_id), "")
            if not resolved_chart_uid or resolved_chart_uid != chart_uid:
                continue
            chart_cache_key = (cache_revision, trait_signature, chart_uid)
            likelihoods = likelihood_cache.get(chart_cache_key)
            cached_likelihood: object | None = None
            if isinstance(likelihoods, dict):
                cached_likelihood = likelihoods.get(selected_trait_name)
            if cached_likelihood is None and isinstance(individual_cache, dict):
                cached_likelihood = individual_cache.get((selected_trait_key, chart_uid))
            if (
                cached_likelihood is None
                and isinstance(profile_cache, dict)
                and isinstance(profile_token_cache, dict)
            ):
                profile_cache_key = (selected_trait_key[2], chart_uid)
                cached_chart_token = str(
                    profile_token_cache.get(profile_cache_key, "") or ""
                )
                if chart_tokens is None:
                    chart_tokens = self._traits_distribution_chart_tokens()
                current_chart_token = chart_tokens.get(chart_uid)
                if cached_chart_token and cached_chart_token == current_chart_token:
                    cached_likelihood = profile_cache.get(profile_cache_key)
            if cached_likelihood is None:
                continue
            try:
                likelihood = float(cached_likelihood)
            except (TypeError, ValueError):
                continue
            chart_name = str(
                getattr(chart, "name", "") or f"Chart {chart_uid or chart_id}"
            ).strip()
            rows.append(
                {
                    "chart_uid": chart_uid,
                    "name": chart_name or f"Chart {chart_uid or chart_id}",
                    "likelihood": likelihood,
                    "deviation": likelihood - db_average_pct,
                }
            )
        rows.sort(
            key=lambda row: (
                -float(row["likelihood"]),
                -float(row["deviation"]),
                str(row["name"]).casefold(),
            )
        )
        if cache_complete:
            try:
                cache_sequence = db.latest_chart_change_sequence()
            except Exception:
                cache_sequence = 0
            sorted_cache[cache_key] = (cache_sequence, tuple(rows))
            while len(sorted_cache) > 16:
                sorted_cache.pop(next(iter(sorted_cache)))
        if limit is None:
            return rows
        return rows[: max(0, int(limit))]

    def _rankings_traits_rows_for_display(
        self,
        *,
        chart_uids: list[str] | set[str] | tuple[str, ...],
        trait_signature: tuple[tuple[str, str, str], ...],
        selected_trait_name: str,
        database_values: dict[str, float],
        cache_complete: bool,
    ) -> tuple[list[dict[str, Any]], bool]:
        visible_limit = self._rankings_trait_visible_limit(selected_trait_name)
        candidate_rows = self._rankings_traits_chart_rankings(
            chart_uids=chart_uids,
            trait_signature=trait_signature,
            selected_trait_name=selected_trait_name,
            database_values=database_values,
            limit=visible_limit + 1,
            cache_complete=cache_complete,
        )
        return candidate_rows[:visible_limit], len(candidate_rows) > visible_limit

    def _render_rankings_traits_html(
        self,
        selected_trait_name: str | None,
        rankings: list[dict[str, Any]],
        *,
        cache_warmed: bool,
        parsed_percent: float | None,
    ) -> str:
        rendered = self._render_traits_distribution_rankings_html(
            selected_trait_name,
            rankings,
            scope_label="the database",
            cache_warmed=cache_warmed,
            parsed_percent=parsed_percent,
        )
        if selected_trait_name and rankings and len(rankings) != 10:
            rendered = rendered.replace(
                "Top 10 <b>", f"Top {len(rankings)} <b>", 1
            )
        return rendered

    def _on_rankings_traits_show_next_clicked(self) -> None:
        combo = getattr(self, "rankings_trait_combo", None)
        if not isinstance(combo, QComboBox):
            return
        selected_trait_name = str(combo.currentData() or "").strip()
        if not selected_trait_name:
            return
        limits = getattr(self, "_rankings_trait_visible_limits", None)
        if not isinstance(limits, dict):
            limits = {}
            self._rankings_trait_visible_limits = limits
        limits[selected_trait_name] = (
            self._rankings_trait_visible_limit(selected_trait_name) + 10
        )

        active_job = getattr(self, "_rankings_traits_active_job", None)
        token = getattr(self, "_rankings_traits_worker_token", None)
        if active_job is not None and token is not None:
            active_thread = active_job[0]
            if (
                isinstance(active_thread, QThread)
                and active_thread.isRunning()
                and str(token[0]) == selected_trait_name
            ):
                self._rankings_traits_last_live_progress_key = None
                self._on_rankings_trait_progress(
                    token,
                    float(
                        getattr(self, "_rankings_traits_last_parsed_percent", 0.0)
                        or 0.0
                    ),
                )
                return
        self._refresh_rankings_panel({"traits"})

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
        self._set_rankings_traits_html(
            self._render_rankings_traits_html(
                None,
                [],
                cache_warmed=True,
                parsed_percent=100.0,
            ),
            has_more=False,
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

    def _start_rankings_trait_worker(
        self,
        selected_trait_name: str,
        database_chart_uids: tuple[str, ...],
        trait_items: list[dict[str, Any]],
        trait_signature: tuple[tuple[str, str, str], ...],
        snapshot_database_values: dict[str, float],
    ) -> None:
        """Run the formerly timer-sliced scoring collector in one worker thread."""
        chart_tokens = self._traits_distribution_chart_tokens()
        authoritative_chart_state = tuple(
            (chart_uid, str(chart_tokens.get(chart_uid, "") or ""))
            for chart_uid in database_chart_uids
        )
        norm_state = tuple(sorted(snapshot_database_values.items()))
        job_key = (
            selected_trait_name,
            int(getattr(self, "_database_metrics_cache_revision", 0)),
            database_chart_uids,
            authoritative_chart_state,
            trait_signature,
            norm_state,
        )
        active_job = getattr(self, "_rankings_traits_active_job", None)
        if active_job is not None:
            active_thread, _active_worker, active_token = active_job
            if isinstance(active_thread, QThread) and active_thread.isRunning():
                if active_token[:-1] == job_key and not active_thread.isInterruptionRequested():
                    self._rankings_traits_worker_token = active_token
                    self._rankings_traits_worker_context = dict(snapshot_database_values)
                    return
                sequence = int(getattr(self, "_rankings_traits_worker_sequence", 0)) + 1
                self._rankings_traits_worker_sequence = sequence
                token = (*job_key, sequence)
                self._rankings_traits_worker_token = token
                self._rankings_traits_pending_job = (
                    token,
                    database_chart_uids,
                    trait_items,
                    trait_signature,
                    snapshot_database_values,
                )
                active_thread.requestInterruption()
                return
            self._on_rankings_trait_thread_stopped()
            if getattr(self, "_rankings_traits_active_job", None) is not None:
                return

        sequence = int(getattr(self, "_rankings_traits_worker_sequence", 0)) + 1
        self._rankings_traits_worker_sequence = sequence
        token = (*job_key, sequence)
        self._rankings_traits_worker_token = token
        self._rankings_traits_worker_context = dict(snapshot_database_values)
        self._rankings_traits_last_parsed_percent = 0.0
        self._launch_rankings_trait_worker(
            token, database_chart_uids, trait_items, trait_signature
        )

    def _launch_rankings_trait_worker(
        self,
        token: object,
        database_chart_uids: tuple[str, ...],
        trait_items: list[dict[str, Any]],
        trait_signature: tuple[tuple[str, str, str], ...],
    ) -> None:
        thread = QThread(self if isinstance(self, QObject) else None)
        worker = _RankingsTraitWorker(
            self, token, database_chart_uids, trait_items, trait_signature
        )
        self._rankings_traits_active_job = (thread, worker, token)
        jobs = getattr(self, "_rankings_traits_worker_jobs", None)
        if not isinstance(jobs, list):
            jobs = []
            self._rankings_traits_worker_jobs = jobs
        jobs.append((thread, worker, token))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_rankings_trait_progress, Qt.QueuedConnection)
        worker.finished.connect(self._on_rankings_trait_finished, Qt.QueuedConnection)
        worker.failed.connect(self._on_rankings_trait_failed, Qt.QueuedConnection)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(self._on_rankings_trait_thread_stopped, Qt.QueuedConnection)
        thread.start()

    @Slot()
    def _on_rankings_trait_thread_stopped(self) -> None:
        active_job = getattr(self, "_rankings_traits_active_job", None)
        if active_job is None:
            return
        thread, _worker, _token = active_job
        if thread.isRunning():
            return
        jobs = getattr(self, "_rankings_traits_worker_jobs", [])
        if active_job in jobs:
            jobs.remove(active_job)
        self._rankings_traits_active_job = None
        thread.deleteLater()
        pending = getattr(self, "_rankings_traits_pending_job", None)
        self._rankings_traits_pending_job = None
        if pending is None:
            return
        token, chart_uids, trait_items, trait_signature, snapshot_values = pending
        if token != getattr(self, "_rankings_traits_worker_token", None):
            return
        self._rankings_traits_worker_context = dict(snapshot_values)
        self._rankings_traits_last_parsed_percent = 0.0
        self._launch_rankings_trait_worker(
            token, chart_uids, trait_items, trait_signature
        )

    def _stop_rankings_trait_worker(self, wait_msecs: int | None = None) -> None:
        """Stop cache population before the Database View owner is destroyed."""
        self._rankings_traits_worker_token = None
        self._rankings_traits_pending_job = None
        jobs = list(getattr(self, "_rankings_traits_worker_jobs", []))
        for thread, _worker, _token in jobs:
            if isinstance(thread, QThread) and thread.isRunning():
                thread.requestInterruption()
                thread.quit()
        for thread, _worker, _token in jobs:
            if not isinstance(thread, QThread) or not thread.isRunning():
                continue
            if wait_msecs is None:
                thread.wait()
            else:
                thread.wait(max(0, int(wait_msecs)))

    def _rankings_trait_snapshot_database_values(
        self,
        *,
        selected_trait_name: str,
    ) -> dict[str, float]:
        """Return the selected stored DB norm used by the active ranking worker."""
        snapshot_values = getattr(self, "_rankings_traits_worker_context", {})
        if isinstance(snapshot_values, dict) and selected_trait_name in snapshot_values:
            try:
                return {selected_trait_name: float(snapshot_values[selected_trait_name])}
            except (TypeError, ValueError):
                return {}
        return {}

    @Slot(object, float)
    def _on_rankings_trait_progress(self, token: object, parsed_percent: float) -> None:
        if token != getattr(self, "_rankings_traits_worker_token", None):
            return
        try:
            parsed_value = max(0.0, min(100.0, float(parsed_percent)))
        except (TypeError, ValueError):
            parsed_value = 0.0
        self._rankings_traits_last_parsed_percent = parsed_value
        progress_key = (token, int(parsed_value))
        if (
            progress_key
            == getattr(self, "_rankings_traits_last_live_progress_key", None)
            and parsed_value < 100.0
        ):
            return

        trait_name = str(token[0])
        chart_uids = tuple(token[2])
        trait_signature = token[4]
        database_values = self._rankings_trait_snapshot_database_values(
            selected_trait_name=trait_name,
        )
        if trait_name not in database_values:
            safe_trait = html.escape(trait_name)
            self._set_rankings_traits_html(
                "<span style='color:#ffb3b3;'>Stored DB norm unavailable for "
                f"<b>{safe_trait}</b>. Generate or refresh this trait's DB Norms in Settings before ranking.</span>",
                has_more=False,
            )
            return
        rankings, has_more = self._rankings_traits_rows_for_display(
            chart_uids=chart_uids,
            trait_signature=trait_signature,
            selected_trait_name=trait_name,
            database_values=database_values,
            cache_complete=False,
        )
        if rankings:
            self._rankings_traits_last_live_progress_key = progress_key
            self._set_rankings_traits_html(
                self._render_rankings_traits_html(
                    trait_name,
                    rankings,
                    cache_warmed=False,
                    parsed_percent=parsed_value,
                ),
                has_more=has_more,
            )
            return

        safe_trait = html.escape(trait_name)
        self._set_rankings_traits_html(
            f"<span style='color:#9a9a9a;'>Calculating top chart matches for "
            f"<b>{safe_trait}</b>… {parsed_value:.0f}% of DB parsed.</span>",
            has_more=False,
        )

    @Slot(object, object)
    def _on_rankings_trait_finished(self, token: object, result: object) -> None:
        if token != getattr(self, "_rankings_traits_worker_token", None):
            return
        trait_name = str(token[0])
        trait_signature = token[4]
        database_values = self._rankings_trait_snapshot_database_values(
            selected_trait_name=trait_name,
        )
        if trait_name not in database_values:
            safe_trait = html.escape(trait_name)
            self._set_rankings_traits_html(
                "<span style='color:#ffb3b3;'>Stored DB norm unavailable for "
                f"<b>{safe_trait}</b>. Generate or refresh this trait's DB Norms in Settings before ranking.</span>",
                has_more=False,
            )
            return
        chart_uids = self._rankings_database_chart_uids()
        rankings, has_more = self._rankings_traits_rows_for_display(
            chart_uids=chart_uids,
            trait_signature=trait_signature,
            selected_trait_name=trait_name,
            database_values=database_values,
            cache_complete=True,
        )
        self._rankings_traits_last_parsed_percent = 100.0
        self._set_rankings_traits_html(
            self._render_rankings_traits_html(
                trait_name,
                rankings,
                cache_warmed=True,
                parsed_percent=100.0,
            ),
            has_more=has_more,
        )

    @Slot(object, str)
    def _on_rankings_trait_failed(self, token: object, message: str) -> None:
        if token != getattr(self, "_rankings_traits_worker_token", None):
            return
        self._set_rankings_traits_html(
            f"<span style='color:#ffb3b3;'>Trait ranking failed: {html.escape(message)}</span>",
            has_more=False,
        )

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
        # advance only a few charts. A one-trait signature is independently
        # cacheable; its comparison baseline always comes from stored DB Norms.
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
        cache_warmed = False
        parsed_percent: float | None = 100.0
        if selected_trait_name:
            try:
                snapshot_averages = trait_snapshot_averages(ranking_trait_items)
            except Exception:
                snapshot_averages = {}
            if selected_trait_name not in snapshot_averages:
                self._stop_rankings_trait_worker(wait_msecs=0)
                safe_trait = html.escape(selected_trait_name)
                self._set_rankings_traits_html(
                    "<span style='color:#ffb3b3;'>Stored DB norm unavailable for "
                    f"<b>{safe_trait}</b>. Generate or refresh this trait's DB Norms in Settings before ranking.</span>",
                    has_more=False,
                )
                if "sign_dominance" in requested_sections:
                    self._refresh_sign_dominance_rankings(database_chart_ids)
                return
            database_values = {
                selected_trait_name: float(snapshot_averages[selected_trait_name]) / 100.0
            }
            if not isinstance(
                getattr(self, "_traits_distribution_chart_likelihood_cache", None),
                dict,
            ):
                self._load_traits_distribution_likelihood_cache()
            cache_warmed = self._rankings_trait_likelihood_cache_complete(
                chart_uids_by_id=self._traits_distribution_chart_uid_by_id(),
                trait_signature=trait_signature,
                selected_trait_name=selected_trait_name,
            )
            if not cache_warmed:
                parsed_percent = 0.0
                self._start_rankings_trait_worker(
                    selected_trait_name,
                    tuple(sorted(database_chart_uids)),
                    ranking_trait_items,
                    trait_signature,
                    dict(database_values),
                )
                self._on_rankings_trait_progress(
                    getattr(self, "_rankings_traits_worker_token", None), 0.0
                )
                if "sign_dominance" in requested_sections:
                    self._refresh_sign_dominance_rankings(database_chart_ids)
                return
            self._stop_rankings_trait_worker(wait_msecs=0)
        else:
            self._stop_rankings_trait_worker(wait_msecs=0)
        database_chart_uids = tuple(
            sorted(
                str(chart_uid).strip().upper()
                for chart_uid in get_chart_uid_map(database_chart_ids).values()
                if str(chart_uid or "").strip()
            )
        )
        trait_rankings, has_more = self._rankings_traits_rows_for_display(
            chart_uids=database_chart_uids,
            trait_signature=trait_signature,
            selected_trait_name=selected_trait_name or "",
            database_values=database_values,
            cache_complete=cache_warmed,
        )
        self._set_rankings_traits_html(
            self._render_rankings_traits_html(
                selected_trait_name,
                trait_rankings,
                cache_warmed=cache_warmed,
                parsed_percent=parsed_percent,
            ),
            has_more=has_more,
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

    def _sign_dominance_chart_name_style(
        self, chart: Any, selected_sign: str, *, least: bool = False
    ) -> str:
        sun_matches = self._rankings_chart_body_sign(chart, "Sun") == selected_sign
        moon_matches = self._rankings_chart_body_sign(chart, "Moon") == selected_sign
        rising_matches = (
            bool(chart_uses_houses(chart))
            and self._rankings_chart_body_sign(chart, "AS") == selected_sign
        )
        css_parts = ["text-decoration:none"]
        if not sun_matches:
            css_parts.append("font-style:italic")
        if least and sun_matches:
            css_parts.append("color:#ffd966")
        elif sun_matches and moon_matches:
            css_parts.append("color:#39ff14")
        elif moon_matches and not sun_matches:
            css_parts.append("color:#5dade2")
        else:
            css_parts.append("color:#f0f0f0")
        if sun_matches and moon_matches and rising_matches:
            css_parts.append("font-weight:700")
        return "; ".join(css_parts)

    @staticmethod
    def _sign_dominance_key_html(selected_sign: str, *, least: bool = False) -> str:
        """Return the visual key for chart-name styling in dominance rankings."""
        safe_sign = html.escape(selected_sign)
        sun_color = "#ffd966" if least else "#39ff14"
        entries = (
            (f"font-weight:700; color:{sun_color}", f"Sun/Moon/AS all in {safe_sign}"),
            (f"color:{sun_color}", f"Sun/Moon in {safe_sign}"),
            ("font-style:italic; color:#f0f0f0", f"AS in {safe_sign}"),
            (f"color:{sun_color}", f"Sun in {safe_sign}"),
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
            weights, recalculated = resolve_complete_sign_weights(
                stored_weights.get(int(chart_id)),
                getattr(chart, "dominant_sign_weights", None),
                ZODIAC_NAMES,
                lambda chart=chart: _calculate_dominant_sign_weights(chart),
            )
            if weights is None:
                continue
            if recalculated:
                chart.dominant_sign_weights = dict(weights)
            try:
                value = float(weights[selected_sign])
            except (KeyError, TypeError, ValueError):
                continue
            chart_total_weight = sum(
                float(weights.get(sign, 0.0) or 0.0) for sign in ZODIAC_NAMES
            )
            # A zero-total map is invalid dominance data, not a legitimate
            # zero-percent sign score. Never let it enter the ranking pool.
            if chart_total_weight <= 0.0:
                continue
            normalized_value = (
                value / chart_total_weight if chart_total_weight > 0.0 else 0.0
            )
            uses_houses = bool(chart_uses_houses(chart))
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
                    "value": normalized_value if least else value,
                    "total_weight": chart_total_weight,
                    "weights": weights,
                    "uses_houses": uses_houses,
                    "name_style": self._sign_dominance_chart_name_style(
                        chart, selected_sign, least=least
                    ),
                }
            )
            if chart_uid:
                tooltip_html = sign_dominance_tooltip_html(
                    chart_name=str(getattr(chart, "name", "") or "This chart"),
                    selected_sign=selected_sign,
                    sun_sign=self._rankings_chart_body_sign(chart, "Sun"),
                    moon_sign=self._rankings_chart_body_sign(chart, "Moon"),
                    ascendant_sign=(
                        self._rankings_chart_body_sign(chart, "AS")
                        if uses_houses
                        else None
                    ),
                )
                if least and not uses_houses:
                    tooltip_html += (
                        "<br><span style='color:#ffd966;'>🏠❓ "
                        "birthtime unknown = houses unknown = "
                        f"{html.escape(selected_sign)} weight unknown</span>"
                    )
                dominance_tooltips[f"chart:{chart_uid}"] = tooltip_html
        tooltip_attribute = (
            "_rankings_least_sign_dominance_tooltips"
            if least
            else "_rankings_most_sign_dominance_tooltips"
        )
        setattr(self, tooltip_attribute, dominance_tooltips)
        if least and db_count:
            # Least-mode rows are normalized per chart, so compare them against
            # the mean of those same normalized values rather than the aggregate
            # raw-weight cache ratio.
            db_average = sum(float(row["value"]) for row in rows) / float(db_count)
        elif not db_average and db_count:
            db_average = sum(float(row["value"]) for row in rows) / float(db_count)
        value_direction = 1.0 if least else -1.0
        rows.sort(
            key=lambda row: (
                least_house_priority(
                    least=least,
                    uses_houses=row.get("uses_houses"),
                ),
                value_direction * float(row["value"]),
                str(row["name"]).casefold(),
            )
        )
        sign_glyphs = dict(zip(ZODIAC_NAMES, ZODIAC_SIGNS, strict=False))
        for sign in ZODIAC_NAMES:
            sign_ranked_rows = sorted(
                rows,
                key=lambda row, sign=sign: (
                    least_house_priority(
                        least=least,
                        uses_houses=row.get("uses_houses"),
                    ),
                    value_direction
                    * (
                        float((row.get("weights") or {}).get(sign, 0.0) or 0.0)
                        / float(row.get("total_weight") or 1.0)
                        if least
                        else float((row.get("weights") or {}).get(sign, 0.0) or 0.0)
                    ),
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
            display_limit = min(20, len(rows))

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
            chart_weights = row.get("weights") or {}
            chart_total_weight = float(row.get("total_weight") or 0.0)
            chart_average = (
                sum(
                    float(chart_weights.get(sign, 0.0) or 0.0)
                    for sign in ZODIAC_NAMES
                )
                / chart_total_weight
                / len(ZODIAC_NAMES)
                if least and chart_total_weight > 0.0
                else sum(
                    float(chart_weights.get(sign, 0.0) or 0.0)
                    for sign in ZODIAC_NAMES
                )
                / len(ZODIAC_NAMES)
            )
            show_glyphs = not least or float(row["value"]) > chart_average
            if show_glyphs and len(shared_signs) >= 2:
                glyph_html = " " + "".join(
                    f"<span style='color:{html.escape(str(SIGN_COLORS.get(sign, '#d8d8d8')))};'>{html.escape(sign_glyphs.get(sign, ''))}</span>"
                    for sign in shared_signs
                    if sign_glyphs.get(sign)
                )
            if least and not bool(row.get("uses_houses")):
                glyph_html += " <span style='color:#ffd966;'>🏠❓</span>"
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
            f"<div style='padding-bottom:3px;'>{f'Bottom {display_limit} charts by <b>{safe_sign}</b> dominance' if least else f'Top {display_limit} charts by <b>{safe_sign}</b> dominance'} in the database.</div>"
            f"{self._sign_dominance_key_html(selected_sign, least=least)}"
            "<table cellspacing='0' cellpadding='0' style='width:100%;'>"
            "<tr><th style='padding:1px 8px 2px 0; color:#f5f5f5; text-align:right;'>#</th>"
            "<th style='padding:1px 8px 2px 0; color:#f5f5f5; text-align:left;'>chart</th>"
            "<th style='padding:1px 8px 2px 0; color:#f5f5f5; text-align:right;'>score</th>"
            "<th style='padding:1px 0 2px 0; color:#f5f5f5; text-align:right;'>vs DB</th></tr>"
            f"{''.join(table_rows)}</table>"
        )
