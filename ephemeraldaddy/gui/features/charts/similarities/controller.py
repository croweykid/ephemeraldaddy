"""Controller for the Manage Charts Similarities Analysis feature.

The controller is the authoritative owner for Similarities Analysis panel state:
export sections, pair controls, chart lookup, DB baseline cache, info-panel
widgets/routing, and lifecycle entry points.  ``ManageChartsDialog`` delegates
panel construction and user-facing actions here while calculation-heavy helper
methods remain callable on the host during this extraction step.
"""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QCheckBox, QLabel, QLineEdit, QPushButton, QWidget

from ephemeraldaddy.gui.features.charts.similarities_analysis import (
    SimilaritiesDbBaselineCache,
)


class SimilaritiesController:
    """Own Similarities Analysis state and delegate host integration points."""

    _LEGACY_STATE_ATTRS = (
        "_similarities_export_sections",
        "_similarities_pair_button",
        "_dissimilarities_pair_button",
        "_similarities_pair_result_label",
        "_similarities_chart_lookup",
        "_similarities_first_chart_input",
        "_similarities_second_chart_input",
        "_similarities_first_use_checkbox",
        "_similarities_second_use_checkbox",
        "_similarities_db_baseline_cache",
    )

    def __init__(self, host: Any) -> None:
        self.host = host
        self.export_sections: list[tuple[str, list[tuple[Any, ...]]]] = []
        self.pair_button: QPushButton | None = None
        self.dissimilarity_pair_button: QPushButton | None = None
        self.pair_result_label: QLabel | None = None
        self.chart_lookup: dict[str, int] = {}
        self.first_chart_input: QLineEdit | None = None
        self.second_chart_input: QLineEdit | None = None
        self.first_use_checkbox: QCheckBox | None = None
        self.second_use_checkbox: QCheckBox | None = None
        self.db_baseline_cache = SimilaritiesDbBaselineCache()
        self.panel: QWidget | None = None
        self.panel_scroll: QWidget | None = None
        self.status_label: QLabel | None = None
        self.db_info_panel: QWidget | None = None

    def install_legacy_attributes(self) -> None:
        """Expose controller-owned state under historical host attr names.

        Existing similarity algorithms still read these names on the dialog.
        Keeping aliases here makes the controller authoritative without forcing a
        high-risk rewrite of every calculation helper in one change.
        """
        self.host._similarities_export_sections = self.export_sections
        self.host._similarities_pair_button = self.pair_button
        self.host._dissimilarities_pair_button = self.dissimilarity_pair_button
        self.host._similarities_pair_result_label = self.pair_result_label
        self.host._similarities_chart_lookup = self.chart_lookup
        self.host._similarities_first_chart_input = self.first_chart_input
        self.host._similarities_second_chart_input = self.second_chart_input
        self.host._similarities_first_use_checkbox = self.first_use_checkbox
        self.host._similarities_second_use_checkbox = self.second_use_checkbox
        self.host._similarities_db_baseline_cache = self.db_baseline_cache

    def capture_legacy_attributes(self) -> None:
        """Refresh controller references after legacy panel-building code runs."""
        self.export_sections = getattr(
            self.host, "_similarities_export_sections", self.export_sections
        )
        self.pair_button = getattr(self.host, "_similarities_pair_button", None)
        self.dissimilarity_pair_button = getattr(
            self.host, "_dissimilarities_pair_button", None
        )
        self.pair_result_label = getattr(self.host, "_similarities_pair_result_label", None)
        self.chart_lookup = getattr(
            self.host, "_similarities_chart_lookup", self.chart_lookup
        )
        self.first_chart_input = getattr(self.host, "_similarities_first_chart_input", None)
        self.second_chart_input = getattr(self.host, "_similarities_second_chart_input", None)
        self.first_use_checkbox = getattr(self.host, "_similarities_first_use_checkbox", None)
        self.second_use_checkbox = getattr(self.host, "_similarities_second_use_checkbox", None)
        self.db_baseline_cache = getattr(
            self.host, "_similarities_db_baseline_cache", self.db_baseline_cache
        )
        self.status_label = getattr(self.host, "similarities_status_label", None)
        self.db_info_panel = getattr(self.host, "similarities_db_info_panel", None)

    def build_panel(self, panel_builder: Callable[[], QWidget]) -> QWidget:
        """Build and retain the Similarities Analysis panel widget tree."""
        self.install_legacy_attributes()
        self.panel = panel_builder()
        self.capture_legacy_attributes()
        return self.panel

    def set_panel_scroll(self, panel_scroll: QWidget | None) -> None:
        self.panel_scroll = panel_scroll

    def refresh_chart_options(self) -> None:
        self.host._refresh_similarities_chart_options()
        self.capture_legacy_attributes()

    def update_analysis(self, chart_ids: list[int]) -> None:
        self.host._update_similarities_analysis(chart_ids)
        self.capture_legacy_attributes()

    def calculate_pair_similarity(self) -> None:
        self.host._calculate_pair_similarity_from_selection()
        self.capture_legacy_attributes()

    def calculate_pair_dissimilarity(self) -> None:
        self.host._calculate_pair_dissimilarity_from_selection()
        self.capture_legacy_attributes()

    def export_json(self) -> None:
        self.host._export_similarities_analysis_json()

    def export_csv(self) -> None:
        self.host._export_similarities_analysis_csv()

    def set_db_info_panel_visible(self, visible: bool) -> None:
        self.capture_legacy_attributes()
        info_panel = self.db_info_panel
        if info_panel is None:
            return
        info_panel.setVisible(bool(visible))
        if not visible:
            return
        panel_scroll = self.panel_scroll or getattr(
            self.host, "similarities_analysis_panel_scroll", None
        )
        if panel_scroll is not None:
            self.host._stabilize_left_scroll_panel_layout(panel_scroll)
            scrollbar = panel_scroll.verticalScrollBar()
            if scrollbar is not None:
                QTimer.singleShot(0, lambda sb=scrollbar: sb.setValue(sb.maximum()))
                QTimer.singleShot(120, lambda sb=scrollbar: sb.setValue(sb.maximum()))

    def toggle_db_info_panel(self) -> None:
        self.capture_legacy_attributes()
        info_panel = self.db_info_panel
        if info_panel is None:
            return
        self.set_db_info_panel_visible(not info_panel.isVisible())

    def handle_info_target_requested(self, target: str) -> None:
        self.capture_legacy_attributes()
        info_panel = self.db_info_panel
        if info_panel is None:
            return
        normalized_target = str(target or "").strip().lower()
        if not normalized_target:
            return
        self.set_db_info_panel_visible(True)
        target_output = info_panel.output

        def _render_target() -> None:
            if normalized_target.startswith("gate:"):
                gate_text = normalized_target.split(":", 1)[1]
                if gate_text.isdigit():
                    gate_number = int(gate_text)
                    if not self.host._invoke_db_info_renderer(
                        "_show_human_design_gate_line_info",
                        target_output,
                        gate_number,
                        None,
                    ):
                        self.host._render_db_gate_info_fallback(
                            target_output, gate_number
                        )
                    return
            if normalized_target.startswith("house:"):
                house_text = normalized_target.split(":", 1)[1]
                if house_text.isdigit():
                    house_number = int(house_text)
                    if not self.host._invoke_db_info_renderer(
                        "_show_house_keyword_info",
                        target_output,
                        house_number,
                    ):
                        self.host._render_db_house_info_fallback(target_output, house_number)
                    return
            target_output.setPlainText(
                "No DB info renderer is available for this item yet."
            )

        self.host._run_with_chart_info_output(target_output, _render_target)

    def clear_db_baseline_cache(self) -> None:
        self.db_baseline_cache.clear()
