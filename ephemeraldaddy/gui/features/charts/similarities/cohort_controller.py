"""Cohort provenance extension for the Similarities Analysis controller.

The legacy calculation entry points still live on ManageChartsDialog.  This
controller keeps cohort policy out of ``app.py`` and passes export metadata
explicitly into the reusable Trait export path.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from PySide6.QtWidgets import QPushButton

from ephemeraldaddy.core import db
from ephemeraldaddy.gui.features.charts.exporters import (
    export_similarities_analysis_json_dialog,
)
from ephemeraldaddy.gui.features.charts.statistical_significance import (
    SIGNIFICANCE_CORRECTION_DEFAULT,
    load_significance_correction,
)

from .cohort_metadata import (
    build_gender_distribution,
    chart_uids_from_mapping,
)
from .controller import SimilaritiesController as _BaseSimilaritiesController


_PYTHON_EXPORT_TOOLTIP = "Export Similarities Analysis data as Python"


class SimilaritiesController(_BaseSimilaritiesController):
    """Similarities controller with trait-cohort provenance and gender analysis."""

    def __init__(self, host: Any, **kwargs: Any) -> None:
        self._cohort_chart_uids: list[str] = []
        self._cohort_gender_distribution: Mapping[str, Any] | None = None
        self.gender_distribution_toggle: Any | None = None
        self.gender_distribution_list: Any | None = None
        super().__init__(host, **kwargs)

    def build_panel(self):
        panel = super().build_panel()
        self._wire_python_export_button(panel)
        layout = panel.layout()
        if layout is None:
            return panel

        trailing_item = layout.takeAt(layout.count() - 1) if layout.count() else None
        toggle, section_list = self.add_collapsible_section(
            layout,
            "Gender Distribution",
            min_height=100,
            list_style=(
                "QListWidget {"
                "  background-color: #151515;"
                "  border: 1px solid #333333;"
                "}"
                "QListWidget::item { padding: 4px 6px; }"
            ),
        )
        self.gender_distribution_toggle = toggle
        self.gender_distribution_list = section_list
        self.host.similarities_gender_distribution_toggle = toggle
        self.host.similarities_gender_distribution_list = section_list
        toggle.setVisible(False)
        section_list.setVisible(False)
        if trailing_item is not None:
            layout.addItem(trailing_item)
        return panel

    def _wire_python_export_button(self, panel: Any) -> None:
        """Route the Python data button to the cohort-aware export entry point."""
        for button in panel.findChildren(QPushButton):
            if button.toolTip() != _PYTHON_EXPORT_TOOLTIP:
                continue
            button.clicked.disconnect()
            button.clicked.connect(self.export_json)
            return

    def _guarded_update_analysis(self, chart_ids: list[int]) -> None:
        if not self.autocalculate_enabled and not self._force_calculation:
            super()._guarded_update_analysis(chart_ids)
            return
        super()._guarded_update_analysis(chart_ids)
        self.capture_legacy_attributes()
        self._refresh_cohort_metadata(chart_ids)

    def calculate_pair_similarity(self) -> None:
        super().calculate_pair_similarity()
        self._refresh_cohort_metadata(self.host._selected_local_row_ids())

    def export_json(self) -> None:
        """Export reusable Trait data with its source cohort metadata."""
        self.capture_legacy_attributes()
        export_similarities_analysis_json_dialog(
            self.host,
            self.export_sections,
            sample_uids=self._cohort_chart_uids,
            gender_distribution=self._cohort_gender_distribution,
            reactivate_callback=getattr(self.host, "_reactivate_database_view", None),
        )

    def _selected_cohort_ids(self, chart_ids: list[int]) -> list[int]:
        exclude_placeholders = getattr(
            self.host, "_exclude_similarities_placeholder_local_row_ids", None
        )
        if callable(exclude_placeholders):
            return list(exclude_placeholders(chart_ids))
        return list(chart_ids)

    def _selected_charts(self, chart_ids: list[int]) -> list[Any]:
        chart_loader = getattr(self.host, "_get_chart_for_filter", None)
        if not callable(chart_loader):
            return []
        return [
            chart
            for chart_id in chart_ids
            if (chart := chart_loader(chart_id)) is not None
        ]

    @staticmethod
    def _row_chart_uid(row: Any) -> str:
        if isinstance(row, Mapping):
            return str(row.get("chart_uid") or row.get("Chart UID") or "").strip().upper()
        try:
            return str(row[30] or "").strip().upper() if len(row) > 30 else ""
        except (TypeError, IndexError):
            return ""

    def _database_charts(self) -> list[Any]:
        try:
            rows = list(db.list_charts())
        except Exception:
            return []
        chart_uids = sorted(
            {uid for row in rows if (uid := self._row_chart_uid(row))}
        )
        if not chart_uids:
            return []
        try:
            charts_by_uid = db.load_charts_by_uids(chart_uids)
        except Exception:
            return []
        is_placeholder = getattr(self.host, "_is_placeholder_chart", None)
        charts: list[Any] = []
        for chart_uid in chart_uids:
            chart = charts_by_uid.get(chart_uid)
            if chart is None:
                chart = charts_by_uid.get(chart_uid.upper())
            if chart is None:
                continue
            if callable(is_placeholder) and is_placeholder(chart):
                continue
            charts.append(chart)
        return charts

    def _significance_correction(self) -> str:
        settings = getattr(self.host, "settings", None)
        if settings is None:
            settings = getattr(self.host, "_settings", None)
        if settings is None or not hasattr(settings, "value"):
            return SIGNIFICANCE_CORRECTION_DEFAULT
        return load_significance_correction(settings)

    def _refresh_cohort_metadata(self, chart_ids: list[int]) -> None:
        selected_ids = self._selected_cohort_ids(chart_ids)
        uid_map = self.host._chart_uids_by_local_row_id(selected_ids)
        self._cohort_chart_uids = chart_uids_from_mapping(uid_map)
        selected_charts = self._selected_charts(selected_ids)
        self._cohort_gender_distribution = build_gender_distribution(
            selected_charts,
            self._database_charts(),
            correction=self._significance_correction(),
        )
        self._render_gender_distribution()

    def _render_gender_distribution(self) -> None:
        toggle = self.gender_distribution_toggle
        section_list = self.gender_distribution_list
        if toggle is None or section_list is None:
            return
        distribution = self._cohort_gender_distribution
        significant = bool(
            isinstance(distribution, Mapping)
            and distribution.get("statisticallySignificant")
        )
        toggle.setVisible(significant)
        section_list.setVisible(significant and bool(toggle.isChecked()))
        section_list.clear()
        if not significant or not isinstance(distribution, Mapping):
            return

        counts = distribution.get("counts", {})
        percentages = distribution.get("percentages", {})
        database_percentages = distribution.get("databasePercentages", {})
        significance = distribution.get("significance", {})
        if not isinstance(counts, Mapping):
            return
        for label in counts:
            selected_percent = float(percentages.get(label, 0.0)) if isinstance(percentages, Mapping) else 0.0
            database_percent = (
                float(database_percentages.get(label, 0.0))
                if isinstance(database_percentages, Mapping)
                else 0.0
            )
            result = significance.get(label, {}) if isinstance(significance, Mapping) else {}
            marker = " *" if isinstance(result, Mapping) and result.get("significant") else ""
            section_list.addItem(
                f"{label}: {selected_percent:.1f}% (DB {database_percent:.1f}%, "
                f"{selected_percent - database_percent:+.1f} pp){marker}"
            )
        section_list.setToolTip("* statistically significant after the configured multiple-testing correction")
