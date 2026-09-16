"""Layout/presentation adapter for the Chart View Themes Predictions section."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QTableView,
    QToolButton,
)

from ephemeraldaddy.analysis.theme_prominence import THEME_DEVIATION_ASSIGNMENT_THRESHOLD
from ephemeraldaddy.gui.style import configure_share_export_icon_button


_CHART_MODE = "chart"
_DB_MODE = "db"


class _ThemeChartDominanceProxy(QSortFilterProxyModel):
    """Expose every Theme row and sort it by its share of the current chart."""

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:  # noqa: N802
        source = self.sourceModel()
        if source is None:
            return False
        return _displayed_percent(source, left.row(), 1) < _displayed_percent(
            source, right.row(), 1
        )


class _ThemeDbDirectionProxy(QSortFilterProxyModel):
    """Expose one DB-comparison direction without changing the shared source rows."""

    def __init__(
        self,
        theme_predictions: Any,
        direction: str,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._theme_predictions = theme_predictions
        self._direction = direction
        self.setDynamicSortFilter(True)

    def filterAcceptsRow(  # noqa: N802
        self,
        source_row: int,
        source_parent: QModelIndex,
    ) -> bool:
        source = self.sourceModel()
        if source is None:
            return False
        index = source.index(source_row, 0, source_parent)
        direction = source.data(
            index,
            self._theme_predictions.THEME_ROW_DIRECTION_ROLE,
        )
        return str(direction or "") == self._direction

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:  # noqa: N802
        source = self.sourceModel()
        if source is None:
            return False
        percentile_role = getattr(
            self._theme_predictions,
            "THEME_ROW_PERCENTILE_ROLE",
            None,
        )
        if percentile_role is not None:
            left_percentile = source.data(
                source.index(left.row(), 0),
                percentile_role,
            )
            right_percentile = source.data(
                source.index(right.row(), 0),
                percentile_role,
            )
            if left_percentile is not None and right_percentile is not None:
                return float(left_percentile) < float(right_percentile)
        deviation_role = self._theme_predictions.THEME_ROW_DEVIATION_ROLE
        left_deviation = float(
            source.data(source.index(left.row(), 0), deviation_role) or 0.0
        )
        right_deviation = float(
            source.data(source.index(right.row(), 0), deviation_role) or 0.0
        )
        return left_deviation < right_deviation


def _displayed_percent(source: Any, row: int, column: int) -> float:
    text = str(source.data(source.index(row, column), Qt.DisplayRole) or "")
    try:
        return float(text.replace("%", "").strip())
    except ValueError:
        return 0.0


def _share_icon_path() -> str | None:
    icon_path = Path(__file__).resolve().parents[3] / "graphics" / "share_icon2.png"
    return str(icon_path) if icon_path.exists() else None


def _set_caption_style(label: QLabel) -> None:
    font = QFont(label.font())
    font.setItalic(True)
    label.setFont(font)
    label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
    label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    label.setStyleSheet("color: rgba(230, 230, 230, 0.66); background: transparent;")
    label.setContentsMargins(0, 0, 0, 0)


def _configure_table_columns(table: QTableView) -> None:
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(0, QHeaderView.Stretch)
    header.setSectionResizeMode(1, QHeaderView.Fixed)
    header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
    metrics = table.fontMetrics()
    percent_width = max(
        metrics.horizontalAdvance("% of chart"),
        metrics.horizontalAdvance("0000000000"),
    )
    table.setColumnWidth(1, percent_width + 12)


def _clone_theme_table(
    theme_predictions: Any,
    source_model: Any,
    proxy: QSortFilterProxyModel,
    parent: Any,
) -> QTableView:
    table = QTableView(parent)
    proxy.setParent(table)
    proxy.setSourceModel(source_model)
    table.setModel(proxy)
    table.setItemDelegate(theme_predictions._ThemePredictionColorDelegate(table))
    table.setSortingEnabled(True)
    table.setSelectionBehavior(QTableView.SelectRows)
    table.setSelectionMode(QTableView.SingleSelection)
    table.setAlternatingRowColors(True)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.verticalHeader().setVisible(False)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    table.setStyleSheet(
        "QTableView { color: #f5f5f5; background: rgba(255,255,255,0.03); "
        "border: 1px solid rgba(255,255,255,0.12); "
        "gridline-color: rgba(255,255,255,0.08); }"
        "QHeaderView::section { color: #f5f5f5; background: rgba(255,255,255,0.08); "
        "border: 0; padding: 3px 6px; }"
        "QTableView::item { padding: 2px 6px; }"
    )
    _configure_table_columns(table)
    return table


def _connect_chart_info(table: QTableView, owner: Any, theme_predictions: Any) -> None:
    from ephemeraldaddy.gui.features.charts.theme_chart_info import (
        _handle_theme_prediction_row_clicked,
    )

    table.clicked.connect(
        lambda index: _handle_theme_prediction_row_clicked(
            owner,
            index,
            theme_predictions,
        )
    )


def _mode(owner: Any) -> str:
    combo = getattr(owner, "themes_prediction_mode_combo", None)
    if not isinstance(combo, QComboBox):
        return _CHART_MODE
    return str(combo.currentData() or _CHART_MODE)


def _fallback_caption(owner: Any) -> str:
    fallback = set(getattr(owner, "_theme_prediction_fallback_directions", set()) or set())
    threshold = float(THEME_DEVIATION_ASSIGNMENT_THRESHOLD)
    if fallback == {"above", "below"}:
        return (
            f"No themes are at least {threshold:.0f}% above or below the selected DB norm; "
            "showing the five closest differences in each table."
        )
    if "above" in fallback:
        return (
            f"No themes are at least {threshold:.0f}% above the selected DB norm; "
            "showing the five closest differences."
        )
    if "below" in fallback:
        return (
            f"No themes are at least {threshold:.0f}% below the selected DB norm; "
            "showing the five closest differences."
        )
    return "Themes compared with the selected DB norm."


def _set_caption(owner: Any, message: str) -> None:
    label = getattr(owner, "themes_prediction_label", None)
    if not isinstance(label, QLabel):
        return
    label.setText(message)
    label.setVisible(True)
    label.adjustSize()
    label.setMinimumHeight(label.sizeHint().height())


def _resize_visible_table(theme_predictions: Any, table: QTableView) -> None:
    theme_predictions._resize_theme_prediction_table_to_contents(table)


def _refresh_theme_section(theme_predictions: Any, owner: Any) -> None:
    chart_proxy = getattr(owner, "_themes_chart_dominance_proxy", None)
    above_proxy = getattr(owner, "_themes_db_above_proxy", None)
    below_proxy = getattr(owner, "_themes_db_below_proxy", None)
    for proxy in (chart_proxy, above_proxy, below_proxy):
        if isinstance(proxy, QSortFilterProxyModel):
            proxy.invalidateFilter()

    if isinstance(chart_proxy, QSortFilterProxyModel):
        chart_proxy.sort(1, Qt.DescendingOrder)
    if isinstance(above_proxy, QSortFilterProxyModel):
        above_proxy.sort(2, Qt.DescendingOrder)
    if isinstance(below_proxy, QSortFilterProxyModel):
        below_proxy.sort(2, Qt.AscendingOrder)

    chart_table = getattr(owner, "themes_prediction_table", None)
    above_table = getattr(owner, "themes_prediction_above_table", None)
    below_table = getattr(owner, "themes_prediction_below_table", None)
    above_label = getattr(owner, "themes_prediction_above_label", None)
    below_label = getattr(owner, "themes_prediction_below_label", None)

    unavailable = str(getattr(owner, "_themes_prediction_unavailability_reason", "") or "")
    if unavailable:
        for widget in (chart_table, above_table, below_table, above_label, below_label):
            if hasattr(widget, "setVisible"):
                widget.setVisible(False)
        current = getattr(owner, "themes_prediction_label", None)
        current_text = current.text().strip() if isinstance(current, QLabel) else ""
        if not current_text:
            _set_caption(owner, unavailable)
        return

    if _mode(owner) == _DB_MODE:
        if isinstance(chart_table, QTableView):
            chart_table.setVisible(False)
        above_count = above_proxy.rowCount() if isinstance(above_proxy, QSortFilterProxyModel) else 0
        below_count = below_proxy.rowCount() if isinstance(below_proxy, QSortFilterProxyModel) else 0
        if isinstance(above_label, QLabel):
            above_label.setVisible(above_count > 0)
        if isinstance(above_table, QTableView):
            above_table.setVisible(above_count > 0)
            _resize_visible_table(theme_predictions, above_table)
        if isinstance(below_label, QLabel):
            below_label.setVisible(below_count > 0)
        if isinstance(below_table, QTableView):
            below_table.setVisible(below_count > 0)
            _resize_visible_table(theme_predictions, below_table)
        _set_caption(owner, _fallback_caption(owner))
        return

    for widget in (above_table, below_table, above_label, below_label):
        if hasattr(widget, "setVisible"):
            widget.setVisible(False)
    chart_count = chart_proxy.rowCount() if isinstance(chart_proxy, QSortFilterProxyModel) else 0
    if isinstance(chart_table, QTableView):
        chart_table.setVisible(chart_count > 0)
        _resize_visible_table(theme_predictions, chart_table)
    _set_caption(
        owner,
        "Themes ranked by their share of this chart's total semantic Theme activation.",
    )


def _proxy_rows(proxy: QSortFilterProxyModel) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in range(proxy.rowCount()):
        rows.append(
            [
                str(proxy.data(proxy.index(row, column), Qt.DisplayRole) or "")
                for column in range(3)
            ]
        )
    return rows


def _export_themes(owner: Any) -> None:
    chart_proxy = getattr(owner, "_themes_chart_dominance_proxy", None)
    above_proxy = getattr(owner, "_themes_db_above_proxy", None)
    below_proxy = getattr(owner, "_themes_db_below_proxy", None)
    if _mode(owner) == _DB_MODE:
        sections = [
            ("Above DB Avg", above_proxy),
            ("Below DB Avg", below_proxy),
        ]
        default_name = "themes-dominant-vs-db.csv"
    else:
        sections = [("Dominant in Chart", chart_proxy)]
        default_name = "themes-dominant-in-chart.csv"

    if not any(
        isinstance(proxy, QSortFilterProxyModel) and proxy.rowCount() > 0
        for _title, proxy in sections
    ):
        return

    path, _selected_filter = QFileDialog.getSaveFileName(
        owner,
        "Export Themes",
        default_name,
        "CSV File (*.csv)",
    )
    if not path:
        return
    if not path.lower().endswith(".csv"):
        path = f"{path}.csv"

    with open(path, "w", encoding="utf-8", newline="") as export_file:
        writer = csv.writer(export_file)
        for section_index, (title, proxy) in enumerate(sections):
            if not isinstance(proxy, QSortFilterProxyModel) or proxy.rowCount() <= 0:
                continue
            if section_index:
                writer.writerow([])
            writer.writerow([title])
            writer.writerow(["Theme", "% of chart", "vs DB"])
            writer.writerows(_proxy_rows(proxy))


def _upgrade_theme_section(theme_predictions: Any, owner: Any) -> None:
    if getattr(owner, "_ephemeraldaddy_theme_section_layout_upgraded", False):
        return

    combo = getattr(owner, "themes_prediction_mode_combo", None)
    caption = getattr(owner, "themes_prediction_label", None)
    chart_table = getattr(owner, "themes_prediction_table", None)
    source_model = getattr(owner, "_themes_prediction_rows_model", None)
    if not isinstance(combo, QComboBox) or not isinstance(caption, QLabel):
        return
    if not isinstance(chart_table, QTableView) or source_model is None:
        return

    content = chart_table.parentWidget()
    layout = content.layout() if content is not None else None
    header_row = combo.parentWidget()
    if layout is None or header_row is None:
        return

    combo.blockSignals(True)
    combo.clear()
    combo.addItem("DOMINANT IN CHART", _CHART_MODE)
    combo.addItem("DOMINANT VS DB", _DB_MODE)
    combo.setCurrentIndex(0)
    combo.setMinimumContentsLength(17)
    combo.blockSignals(False)

    _set_caption_style(caption)
    layout.removeWidget(caption)
    layout.removeWidget(header_row)
    layout.insertWidget(0, caption)
    layout.insertWidget(1, header_row)

    export_button = QToolButton(header_row)
    configure_share_export_icon_button(
        export_button,
        share_icon_path=_share_icon_path(),
        tooltip="Export the visible Themes table data as CSV",
    )
    export_button.clicked.connect(lambda: _export_themes(owner))
    header_row.layout().addWidget(export_button, alignment=Qt.AlignRight)
    owner.themes_prediction_export_button = export_button

    chart_proxy = _ThemeChartDominanceProxy(chart_table)
    chart_proxy.setDynamicSortFilter(True)
    chart_proxy.setSourceModel(source_model)
    chart_table.setModel(chart_proxy)
    chart_table.sortByColumn(1, Qt.DescendingOrder)
    _configure_table_columns(chart_table)
    owner._themes_chart_dominance_proxy = chart_proxy
    owner._themes_prediction_filter_model = chart_proxy

    above_label = QLabel("Above DB Avg", content)
    below_label = QLabel("Below DB Avg", content)
    for label in (above_label, below_label):
        font = QFont(label.font())
        font.setBold(True)
        label.setFont(font)
        label.setContentsMargins(0, 2, 0, 0)

    above_proxy = _ThemeDbDirectionProxy(theme_predictions, "above")
    below_proxy = _ThemeDbDirectionProxy(theme_predictions, "below")
    above_table = _clone_theme_table(
        theme_predictions,
        source_model,
        above_proxy,
        content,
    )
    below_table = _clone_theme_table(
        theme_predictions,
        source_model,
        below_proxy,
        content,
    )
    above_table.sortByColumn(2, Qt.DescendingOrder)
    below_table.sortByColumn(2, Qt.AscendingOrder)
    _connect_chart_info(above_table, owner, theme_predictions)
    _connect_chart_info(below_table, owner, theme_predictions)

    layout.addWidget(above_label)
    layout.addWidget(above_table)
    layout.addWidget(below_label)
    layout.addWidget(below_table)

    owner.themes_prediction_above_label = above_label
    owner.themes_prediction_above_table = above_table
    owner.themes_prediction_below_label = below_label
    owner.themes_prediction_below_table = below_table
    owner._themes_db_above_proxy = above_proxy
    owner._themes_db_below_proxy = below_proxy

    combo.currentIndexChanged.connect(
        lambda _index=0: _refresh_theme_section(theme_predictions, owner)
    )
    owner._ephemeraldaddy_theme_section_layout_upgraded = True
    _refresh_theme_section(theme_predictions, owner)


def install_theme_predictions_section_layout(theme_predictions: Any) -> None:
    """Install the two-mode Themes presentation without changing its scoring engine."""
    if getattr(
        theme_predictions,
        "_ephemeraldaddy_theme_section_layout_installed",
        False,
    ):
        return

    original_ensure = theme_predictions._ensure_theme_predictions_section

    def ensure_theme_predictions_section(owner: Any, traits_table: QTableView) -> None:
        original_ensure(owner, traits_table)
        _upgrade_theme_section(theme_predictions, owner)

    def refresh_theme_prediction_filter(owner: Any) -> None:
        _refresh_theme_section(theme_predictions, owner)

    theme_predictions._ensure_theme_predictions_section = ensure_theme_predictions_section
    theme_predictions._refresh_theme_prediction_filter = refresh_theme_prediction_filter
    theme_predictions._ephemeraldaddy_theme_section_layout_installed = True
