"""Chart View Predictions integration for semantic Theme prominence.

This module is installed through the existing ``trait_predictions`` facade so
Themes can extend the established Predictions surface without adding more code
to ``app.py``.  The Themes section itself is independent after construction:
it has its own model, filter, render token, snapshot comparison, and stable
macrotheme key role.
"""

from __future__ import annotations

import math
from types import MethodType
from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QSortFilterProxyModel,
    QTimer,
    Qt,
)
try:
    from PySide6.QtGui import QColor, QFont, QPalette
except Exception:  # pragma: no cover - headless test environments may omit QtGui libs
    QColor = None  # type: ignore[assignment]
    QFont = None  # type: ignore[assignment]
    QPalette = None  # type: ignore[assignment]
try:
    from PySide6.QtWidgets import (
        QComboBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QSizePolicy,
        QStyledItemDelegate,
        QTableView,
        QWidget,
    )
except Exception:  # pragma: no cover - headless test environments may omit Qt widget libs
    class _MissingQtWidget:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("PySide6 QtWidgets are unavailable in this environment.")

    QComboBox = QHBoxLayout = QHeaderView = QLabel = QSizePolicy = QStyledItemDelegate = QTableView = QWidget = _MissingQtWidget  # type: ignore[misc,assignment]

from ephemeraldaddy.analysis.theme_prominence import (
    THEME_DEVIATION_ASSIGNMENT_THRESHOLD,
    calculate_theme_family_scores,
    calculate_theme_subtheme_scores,
    theme_family_snapshot_averages,
    theme_snapshot_unavailability_reason,
)
from ephemeraldaddy.core.theme_reference import THEME_FAMILIES
from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import (
    load_prediction_norms_snapshot,
)
from ephemeraldaddy.gui.features.charts.right_panel_state import (
    save_section_expanded,
    saved_section_expanded,
)
from ephemeraldaddy.gui.style import (
    CHART_DATA_HIGHLIGHT_COLOR,
    appwide_red_green_rgb_for_range,
    apply_shared_dropdown_style,
)


THEME_ROW_KEY_ROLE = Qt.UserRole + 31
THEME_ROW_DEVIATION_ROLE = Qt.UserRole + 32
THEME_ROW_DIRECTION_ROLE = Qt.UserRole + 33


def _format_signed_percentage(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.1f}%"


class _ThemePredictionRowsModel(QAbstractTableModel):
    """Qt row model for seven stable macrotheme/family predictions."""

    _HEADERS = ("Theme", "%", "vs DB")

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[dict[str, Any]] = []

    def set_rows(self, rows: list[dict[str, Any]]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:  # noqa: N802
        if orientation == Qt.Horizontal and role == Qt.DisplayRole and 0 <= section < len(self._HEADERS):
            return self._HEADERS[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        row = self._rows[index.row()]
        column = index.column()
        score = float(row.get("score", 0.0))
        deviation = float(row.get("deviation", 0.0))
        if role == Qt.DisplayRole:
            if column == 0:
                return str(row.get("label", row.get("key", "")))
            if column == 1:
                return f"{score:.1f}%"
            if column == 2:
                return _format_signed_percentage(deviation)
        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter if column == 0 else Qt.AlignRight | Qt.AlignVCenter
        if role == Qt.ForegroundRole and QColor is not None:
            if column == 0:
                return QColor(CHART_DATA_HIGHLIGHT_COLOR)
            minimum, maximum, value = (0.0, 100.0, score) if column == 1 else (-100.0, 100.0, deviation)
            red, green, blue = appwide_red_green_rgb_for_range(value, minimum, maximum)
            return QColor(red, green, blue)
        if role == Qt.ToolTipRole and column == 0:
            db_average = float(row.get("db_average", 0.0))
            return f"{row.get('label', row.get('key', ''))}\nDB average: {db_average:.1f}%"
        if role == THEME_ROW_KEY_ROLE:
            return str(row.get("key", ""))
        if role == THEME_ROW_DEVIATION_ROLE:
            return deviation
        if role == THEME_ROW_DIRECTION_ROLE:
            if deviation >= THEME_DEVIATION_ASSIGNMENT_THRESHOLD:
                return "above"
            if deviation <= -THEME_DEVIATION_ASSIGNMENT_THRESHOLD:
                return "below"
            return "neutral"
        return None


class _ThemePredictionFilterModel(QSortFilterProxyModel):
    """Expose only notably above- or below-norm macrothemes."""

    def __init__(self, owner: Any, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._owner = owner
        self.setDynamicSortFilter(True)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        source = self.sourceModel()
        if source is None:
            return False
        direction = source.data(source.index(source_row, 0, source_parent), THEME_ROW_DIRECTION_ROLE)
        combo = getattr(self._owner, "themes_prediction_mode_combo", None)
        mode = combo.currentData() if isinstance(combo, QComboBox) else "above"
        return direction == ("below" if mode == "below" else "above")

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:  # noqa: N802
        source = self.sourceModel()
        if source is None:
            return False
        left_deviation = float(source.data(source.index(left.row(), 0), THEME_ROW_DEVIATION_ROLE) or 0.0)
        right_deviation = float(source.data(source.index(right.row(), 0), THEME_ROW_DEVIATION_ROLE) or 0.0)
        return left_deviation < right_deviation


class _ThemePredictionColorDelegate(QStyledItemDelegate):
    def initStyleOption(self, option: Any, index: QModelIndex) -> None:  # noqa: N802
        super().initStyleOption(option, index)
        color = index.data(Qt.ForegroundRole)
        if QColor is not None and QPalette is not None and isinstance(color, QColor):
            option.palette.setColor(QPalette.ColorRole.Text, color)


def _resize_theme_prediction_table_to_contents(table: QTableView) -> None:
    table.resizeRowsToContents()
    model = table.model()
    row_count = model.rowCount() if model is not None else 0
    header_height = table.horizontalHeader().height() if table.horizontalHeader() is not None else 0
    rows_height = sum(table.rowHeight(row) for row in range(row_count))
    frame_height = table.frameWidth() * 2
    content_height = header_height + rows_height + frame_height + 2
    table.setMinimumHeight(content_height)
    table.setMaximumHeight(content_height)
    table.updateGeometry()


def _set_theme_status(owner: Any, message: str) -> None:
    label = getattr(owner, "themes_prediction_label", None)
    if isinstance(label, QLabel):
        label.setText(message)
        label.setVisible(bool(message))
        label.adjustSize()
        label.setMinimumHeight(label.sizeHint().height())


def _refresh_theme_prediction_filter(owner: Any) -> None:
    proxy = getattr(owner, "_themes_prediction_filter_model", None)
    if isinstance(proxy, QSortFilterProxyModel):
        proxy.invalidateFilter()
        combo = getattr(owner, "themes_prediction_mode_combo", None)
        mode = combo.currentData() if isinstance(combo, QComboBox) else "above"
        proxy.sort(2, Qt.AscendingOrder if mode == "below" else Qt.DescendingOrder)
    table = getattr(owner, "themes_prediction_table", None)
    if not isinstance(table, QTableView):
        return
    visible_rows = table.model().rowCount() if table.model() is not None else 0
    table.setVisible(visible_rows > 0)
    _resize_theme_prediction_table_to_contents(table)
    if getattr(owner, "_themes_prediction_unavailability_reason", ""):
        return
    if visible_rows == 0:
        combo = getattr(owner, "themes_prediction_mode_combo", None)
        mode = combo.currentData() if isinstance(combo, QComboBox) else "above"
        direction = "below" if mode == "below" else "above"
        _set_theme_status(
            owner,
            f"No themes are at least {THEME_DEVIATION_ASSIGNMENT_THRESHOLD:.0f}% {direction} the selected DB norm.",
        )
    else:
        _set_theme_status(owner, "")


def configure_theme_prediction_table(owner: Any, table: QTableView) -> None:
    model = _ThemePredictionRowsModel(table)
    proxy = _ThemePredictionFilterModel(owner, table)
    proxy.setSourceModel(model)
    table.setModel(proxy)
    table.setItemDelegate(_ThemePredictionColorDelegate(table))
    table.setSortingEnabled(True)
    table.sortByColumn(2, Qt.DescendingOrder)
    table.setSelectionBehavior(QTableView.SelectRows)
    table.setSelectionMode(QTableView.SingleSelection)
    table.setAlternatingRowColors(True)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(False)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    table.setColumnWidth(0, 220)
    for column in (1, 2):
        table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
    table.setStyleSheet(
        "QTableView { color: #f5f5f5; background: rgba(255,255,255,0.03); "
        "border: 1px solid rgba(255,255,255,0.12); gridline-color: rgba(255,255,255,0.08); }"
        "QHeaderView::section { color: #f5f5f5; background: rgba(255,255,255,0.08); "
        "border: 0; padding: 3px 6px; }"
        "QTableView::item { padding: 2px 6px; }"
    )
    owner._themes_prediction_rows_model = model
    owner._themes_prediction_filter_model = proxy
    combo = getattr(owner, "themes_prediction_mode_combo", None)
    if isinstance(combo, QComboBox) and not getattr(combo, "_ephemeraldaddy_theme_filter_connected", False):
        combo.currentIndexChanged.connect(lambda _index=0: _refresh_theme_prediction_filter(owner))
        combo._ephemeraldaddy_theme_filter_connected = True


def _theme_rows(
    family_scores: dict[str, float],
    db_averages: dict[str, float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family_key, family in THEME_FAMILIES.items():
        if family_key not in family_scores or family_key not in db_averages:
            continue
        score = max(0.0, min(100.0, float(family_scores[family_key])))
        db_average = max(0.0, min(100.0, float(db_averages[family_key])))
        rows.append(
            {
                "key": family_key,
                "label": str(family.get("label", family_key)),
                "score": score,
                "db_average": db_average,
                "deviation": score - db_average,
            }
        )
    return rows


def render_theme_predictions(owner: Any, chart: Any | None) -> None:
    """Render seven macrothemes against the selected static DB Norms snapshot."""
    model = getattr(owner, "_themes_prediction_rows_model", None)
    if not hasattr(model, "set_rows"):
        return
    owner._themes_prediction_unavailability_reason = ""
    owner._themes_prediction_chart = chart
    if chart is None or bool(getattr(owner, "_is_placeholder_chart", lambda _chart: False)(chart)):
        model.set_rows([])
        owner._themes_prediction_unavailability_reason = "Theme predictions are unavailable for this chart."
        _set_theme_status(owner, owner._themes_prediction_unavailability_reason)
        _refresh_theme_prediction_filter(owner)
        return

    snapshot = load_prediction_norms_snapshot()
    db_averages = theme_family_snapshot_averages(snapshot)
    if not db_averages:
        reason = theme_snapshot_unavailability_reason(snapshot)
        owner._themes_prediction_unavailability_reason = reason
        model.set_rows([])
        _set_theme_status(
            owner,
            f"{reason} Recalculate DB Norms to add current Theme baselines.",
        )
        _refresh_theme_prediction_filter(owner)
        return

    try:
        subtheme_scores = calculate_theme_subtheme_scores(chart)
        family_scores = calculate_theme_family_scores(chart, subtheme_scores=subtheme_scores)
    except Exception as exc:
        owner._themes_prediction_unavailability_reason = f"Theme scoring failed: {exc}"
        model.set_rows([])
        _set_theme_status(owner, owner._themes_prediction_unavailability_reason)
        _refresh_theme_prediction_filter(owner)
        return

    owner._theme_prediction_subtheme_scores = dict(subtheme_scores)
    owner._theme_prediction_family_scores = dict(family_scores)
    owner._theme_prediction_db_averages = dict(db_averages)
    model.set_rows(_theme_rows(family_scores, db_averages))
    _refresh_theme_prediction_filter(owner)


def _theme_predictions_have_rendered_content(owner: Any) -> bool:
    table = getattr(owner, "themes_prediction_table", None)
    if hasattr(table, "isVisible") and table.isVisible():
        return True
    label = getattr(owner, "themes_prediction_label", None)
    text = label.text().strip() if isinstance(label, QLabel) else ""
    return bool(text and "Loading theme predictions" not in text)


def _register_theme_section(owner: Any, section_layout: Any) -> None:
    widgets = getattr(owner, "_prediction_section_widgets", None)
    if not isinstance(widgets, dict):
        widgets = {}
        owner._prediction_section_widgets = widgets
    content_widget = section_layout.parentWidget()
    section_widget = content_widget.parentWidget() if content_widget is not None else None
    if section_widget is not None:
        widgets["themes"] = section_widget


def _ensure_theme_predictions_section(owner: Any, traits_table: QTableView) -> None:
    """Insert Themes immediately after Traits once the Traits table is parented."""
    if hasattr(owner, "themes_prediction_table"):
        return
    traits_content = traits_table.parentWidget()
    traits_section = traits_content.parentWidget() if traits_content is not None else None
    panel = traits_section.parentWidget() if traits_section is not None else None
    layout = panel.layout() if panel is not None else None
    add_section = getattr(owner, "_add_chart_analysis_collapsible_section", None)
    if panel is None or layout is None or not callable(add_section):
        return

    expanded = saved_section_expanded(owner, "predictions", "themes")
    expanded_state = getattr(owner, "_chart_analysis_section_expanded", None)
    if isinstance(expanded_state, dict):
        expanded_state["themes"] = expanded

    def on_toggled(is_expanded: bool) -> None:
        save_section_expanded(owner, "predictions", "themes", is_expanded)
        setter = getattr(owner, "_set_chart_analysis_section_expanded", None)
        if callable(setter):
            setter("themes", is_expanded)

    themes_layout = add_section(
        panel=panel,
        layout=layout,
        title="Themes",
        expanded=expanded,
        on_toggled=on_toggled,
        section_key="themes",
    )
    _register_theme_section(owner, themes_layout)

    header_row = QWidget()
    header_layout = QHBoxLayout(header_row)
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setSpacing(6)
    header_layout.addStretch(1)
    owner.themes_prediction_mode_combo = QComboBox()
    if QFont is not None:
        combo_font = QFont(owner.themes_prediction_mode_combo.font())
        combo_font.setCapitalization(QFont.AllUppercase)
        if combo_font.pointSize() > 0:
            combo_font.setPointSize(max(7, combo_font.pointSize() - 2))
        owner.themes_prediction_mode_combo.setFont(combo_font)
    owner.themes_prediction_mode_combo.setMinimumContentsLength(10)
    apply_shared_dropdown_style(owner.themes_prediction_mode_combo)
    owner.themes_prediction_mode_combo.addItem("ABOVE AVG", "above")
    owner.themes_prediction_mode_combo.addItem("BELOW AVG", "below")
    header_layout.addWidget(owner.themes_prediction_mode_combo, alignment=Qt.AlignRight)
    themes_layout.addWidget(header_row)

    owner.themes_prediction_label = QLabel("Loading theme predictions.")
    owner.themes_prediction_label.setTextFormat(Qt.RichText)
    owner.themes_prediction_label.setWordWrap(True)
    owner.themes_prediction_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
    owner.themes_prediction_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
    owner.themes_prediction_label.setMinimumHeight(owner.themes_prediction_label.sizeHint().height())
    themes_layout.addWidget(owner.themes_prediction_label)

    owner.themes_prediction_table = QTableView()
    owner.themes_prediction_table.setVisible(False)
    owner.themes_prediction_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    configure_theme_prediction_table(owner, owner.themes_prediction_table)
    themes_layout.addWidget(owner.themes_prediction_table)
    owner._render_theme_predictions = MethodType(
        lambda self, chart: render_theme_predictions(self, chart),
        owner,
    )


def _extend_right_panel_stack() -> None:
    """Make Themes independently visible/current in Predictions scheduling."""
    from ephemeraldaddy.gui.features.charts import cv_right_panel_stack as stack

    if getattr(stack, "_ephemeraldaddy_theme_predictions_installed", False):
        return

    original_sync_visibility = stack.sync_prediction_section_visibility
    original_placeholders = stack._show_predictions_panel_pending_placeholders
    original_has_content = stack._predictions_panel_has_rendered_content
    original_schedule = stack.schedule_chart_render_for_active_right_panel

    def sync_prediction_section_visibility(owner: Any) -> None:
        original_sync_visibility(owner)
        widgets = getattr(owner, "_prediction_section_widgets", {})
        widget = widgets.get("themes") if isinstance(widgets, dict) else None
        if widget is not None and hasattr(widget, "setVisible"):
            widget.setVisible(True)

    def show_pending_placeholders(owner: Any, chart: Any | None) -> None:
        original_placeholders(owner, chart)
        label = getattr(owner, "themes_prediction_label", None)
        if isinstance(label, QLabel):
            label.setText("Loading theme predictions.")
            label.setVisible(True)
        model = getattr(owner, "_themes_prediction_rows_model", None)
        if hasattr(model, "set_rows"):
            model.set_rows([])
        table = getattr(owner, "themes_prediction_table", None)
        if hasattr(table, "setVisible"):
            table.setVisible(False)

    def predictions_panel_has_rendered_content(owner: Any) -> bool:
        if not original_has_content(owner):
            return False
        return _theme_predictions_have_rendered_content(owner)

    def schedule_chart_render_for_active_right_panel(owner: Any) -> None:
        original_schedule(owner)
        state = getattr(owner, "_chart_right_panel_state", None)
        if getattr(state, "active_tab", None) != "predictions":
            return
        chart = getattr(owner, "_latest_chart", None)
        render = getattr(owner, "_render_theme_predictions", None)
        if chart is None or not callable(render):
            return
        try:
            render_token = stack._chart_right_panel_prediction_render_token(owner, chart)
        except Exception:
            render_token = ""
        last_token = str(getattr(owner, "_theme_prediction_last_render_chart_token", "") or "")
        if render_token and last_token == render_token and _theme_predictions_have_rendered_content(owner):
            return
        render(chart)
        setattr(owner, "_theme_prediction_last_render_chart_token", render_token)

    stack.sync_prediction_section_visibility = sync_prediction_section_visibility
    stack._show_predictions_panel_pending_placeholders = show_pending_placeholders
    stack._predictions_panel_has_rendered_content = predictions_panel_has_rendered_content
    stack.schedule_chart_render_for_active_right_panel = schedule_chart_render_for_active_right_panel
    stack._ephemeraldaddy_theme_predictions_installed = True


def install_theme_predictions(trait_core: Any) -> None:
    """Install Themes through the existing modular Trait Predictions facade."""
    if getattr(trait_core, "_ephemeraldaddy_theme_predictions_installed", False):
        return
    original_configure = trait_core.configure_traits_prediction_table

    def configure_traits_prediction_table(owner: Any, table: QTableView) -> None:
        original_configure(owner, table)
        # Chart View adds the Traits table to its section immediately after this
        # configurator returns. Defer one event-loop turn so parent/layout lookup
        # is valid before inserting the sibling Themes section.
        QTimer.singleShot(
            0,
            lambda owner=owner, table=table: _ensure_theme_predictions_section(owner, table),
        )

    trait_core.configure_traits_prediction_table = configure_traits_prediction_table
    trait_core._ephemeraldaddy_theme_predictions_installed = True
    _extend_right_panel_stack()
