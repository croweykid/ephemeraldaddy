# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.
"""Chart View custom trait prediction rendering helpers."""

from __future__ import annotations

import hashlib
import html
import json
import logging
import sys
import urllib.parse
from datetime import datetime
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QSortFilterProxyModel, QThread, QTimer, Qt, Signal, Slot
try:
    from PySide6.QtGui import QColor, QPalette
except Exception:  # pragma: no cover - headless test environments may omit QtGui libs
    QColor = None  # type: ignore[assignment]
    QPalette = None  # type: ignore[assignment]
try:
    from PySide6.QtWidgets import QLabel, QComboBox, QHeaderView, QMessageBox, QStyledItemDelegate, QTableView, QWidget
except Exception:  # pragma: no cover - headless test environments may omit Qt widget libs
    class _MissingQtWidget:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("PySide6 QtWidgets are unavailable in this environment.")

    class QLabel:  # type: ignore[no-redef]
        pass

    class QComboBox:  # type: ignore[no-redef]
        pass

    class QWidget:  # type: ignore[no-redef]
        pass

    class QHeaderView:  # type: ignore[no-redef]
        Stretch = 1
        ResizeToContents = 2

    class QTableView:  # type: ignore[no-redef]
        SelectRows = 1
        SingleSelection = 1

    class QMessageBox:  # type: ignore[no-redef]
        @staticmethod
        def information(*args: Any, **kwargs: Any) -> None:
            return None

    class QStyledItemDelegate:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def initStyleOption(self, option: Any, index: QModelIndex) -> None:  # noqa: N802
            return None

from ephemeraldaddy.analysis.trait_prediction_index import (
    TraitPredictionQuery,
    global_trait_prediction_index,
)
from ephemeraldaddy.analysis.traits import (
    DEFAULT_TRAIT_COLOR,
    calculate_trait_likelihoods,
    list_traits,
    normalize_trait_color,
    trait_sample_total,
    trait_uid_for_profile,
)
from ephemeraldaddy.analysis.weighted_chart_predictor import (
    matched_weighted_criteria,
    weighted_house_entries,
    weighted_string_entries,
)
from ephemeraldaddy.core import db
from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.gui.features.charts.database_norms_cache import (
    analytical_mapping_signature,
)
from ephemeraldaddy.gui.features.charts.prediction_loading_labels import (
    start_prediction_loading_blink,
    start_prediction_loading_ellipsis,
    stop_prediction_loading_blink,
    stop_prediction_loading_ellipsis,
)
from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import (
    load_prediction_norms_snapshot,
    missing_trait_norms,
    prospective_trait_snapshot_token,
    trait_snapshot_averages,
)
from ephemeraldaddy.gui.style import (
    CHART_DATA_HIGHLIGHT_COLOR,
    apply_chart_info_link_cursor,
    appwide_red_green_rgb_for_range,
    set_chart_info_html,
)


logger = logging.getLogger(__name__)

TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD = 5.0


TRAIT_ROW_NAME_ROLE = Qt.UserRole + 1
TRAIT_ROW_COLOR_ROLE = Qt.UserRole + 2
TRAIT_ROW_DEVIATION_ROLE = Qt.UserRole + 3
TRAIT_ROW_DIRECTION_ROLE = Qt.UserRole + 4


class _TraitPredictionRowsModel(QAbstractTableModel):
    """Qt row model for Chart View trait predictions."""

    _HEADERS = ("Trait", "%", "vs DB")

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
        if role == Qt.DisplayRole:
            if column == 0:
                return row.get("name", "")
            if column == 1:
                return f"{float(row.get('likelihood', 0.0)):.1f}%"
            if column == 2:
                return _format_signed_percentage(float(row.get("deviation", 0.0)))
        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter if column == 0 else Qt.AlignRight | Qt.AlignVCenter
        if role == Qt.ForegroundRole and QColor is not None:
            if column == 0:
                return QColor(str(row.get("color") or DEFAULT_TRAIT_COLOR))
            if column == 1:
                red, green, blue = appwide_red_green_rgb_for_range(float(row.get("likelihood", 0.0)), 0.0, 100.0)
                return QColor(red, green, blue)
            if column == 2:
                red, green, blue = appwide_red_green_rgb_for_range(float(row.get("deviation", 0.0)), -100.0, 100.0)
                return QColor(red, green, blue)
            return QColor("#f5f5f5")
        if role == Qt.ToolTipRole and column == 0:
            return str(row.get("name", ""))
        if role == TRAIT_ROW_NAME_ROLE:
            return row.get("name", "")
        if role == TRAIT_ROW_COLOR_ROLE:
            return row.get("color", DEFAULT_TRAIT_COLOR)
        if role == TRAIT_ROW_DEVIATION_ROLE:
            return float(row.get("deviation", 0.0))
        if role == TRAIT_ROW_DIRECTION_ROLE:
            deviation = float(row.get("deviation", 0.0))
            if deviation >= TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD:
                return "above"
            if deviation <= -TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD:
                return "below"
            return "neutral"
        return None


class _TraitPredictionFilterModel(QSortFilterProxyModel):
    """Filter above/below rows without regenerating rich text."""

    def __init__(self, owner: Any, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._owner = owner
        self.setDynamicSortFilter(True)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:  # noqa: N802
        source = self.sourceModel()
        if source is None:
            return False
        index = source.index(source_row, 0, source_parent)
        direction = source.data(index, TRAIT_ROW_DIRECTION_ROLE)
        combo = getattr(self._owner, "traits_prediction_mode_combo", None)
        mode = combo.currentData() if isinstance(combo, QComboBox) else "above"
        return direction == ("below" if mode == "below" else "above")

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:  # noqa: N802
        source = self.sourceModel()
        if source is None:
            return False
        left_deviation = float(source.data(source.index(left.row(), 0), TRAIT_ROW_DEVIATION_ROLE) or 0.0)
        right_deviation = float(source.data(source.index(right.row(), 0), TRAIT_ROW_DEVIATION_ROLE) or 0.0)
        return abs(left_deviation) < abs(right_deviation)


class _TraitPredictionColorDelegate(QStyledItemDelegate):
    """Apply trait colors at paint time instead of embedding per-row HTML."""

    def initStyleOption(self, option: Any, index: QModelIndex) -> None:  # noqa: N802
        super().initStyleOption(option, index)
        color = index.data(Qt.ForegroundRole)
        if QColor is not None and QPalette is not None and isinstance(color, QColor):
            option.palette.setColor(QPalette.ColorRole.Text, color)


def configure_traits_prediction_table(owner: Any, table: QTableView) -> None:
    model = _TraitPredictionRowsModel(table)
    proxy = _TraitPredictionFilterModel(owner, table)
    proxy.setSourceModel(model)
    table.setModel(proxy)
    table.setItemDelegate(_TraitPredictionColorDelegate(table))
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
    owner._traits_prediction_rows_model = model
    owner._traits_prediction_filter_model = proxy

    combo = getattr(owner, "traits_prediction_mode_combo", None)
    if isinstance(combo, QComboBox) and not getattr(combo, "_ephemeraldaddy_trait_filter_connected", False):
        combo.currentIndexChanged.connect(lambda _index=0: _refresh_traits_prediction_filter(owner))
        combo._ephemeraldaddy_trait_filter_connected = True
    if not getattr(table, "_ephemeraldaddy_trait_click_connected", False):
        table.clicked.connect(lambda index: _handle_trait_prediction_row_clicked(owner, index))
        table._ephemeraldaddy_trait_click_connected = True


def _handle_trait_prediction_row_clicked(owner: Any, index: QModelIndex) -> None:
    if not index.isValid():
        return
    model = index.model()
    if isinstance(model, QSortFilterProxyModel):
        source_index = model.mapToSource(index)
        name = source_index.data(TRAIT_ROW_NAME_ROLE)
    else:
        name = index.data(TRAIT_ROW_NAME_ROLE)
    if name:
        _show_trait_chart_info(owner, str(name))


def _refresh_traits_prediction_filter(owner: Any) -> None:
    proxy = getattr(owner, "_traits_prediction_filter_model", None)
    if isinstance(proxy, QSortFilterProxyModel):
        proxy.invalidateFilter()
        combo = getattr(owner, "traits_prediction_mode_combo", None)
        mode = combo.currentData() if isinstance(combo, QComboBox) else "above"
        proxy.sort(2, Qt.AscendingOrder if mode == "below" else Qt.DescendingOrder)
    table = getattr(owner, "traits_prediction_table", None)
    if isinstance(table, QTableView):
        _resize_traits_prediction_table_to_contents(table)


def _resize_traits_prediction_table_to_contents(table: QTableView) -> None:
    """Resize the Traits table to its generated row height so it never scrolls internally."""
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

TRAIT_DB_NORMS_CACHE_VERSION = 1


class MissingTraitNormCoverage(RuntimeError):
    """Raised when the selected static snapshot lacks requested trait profiles."""


def _predictions_debug_enabled(owner: Any) -> bool:
    return bool(getattr(owner, "_predictions_thread_debug", False))


def _predictions_debug(owner: Any, message: str, *args: object) -> None:
    """Emit terminal Predictions step logs when Settings > Dev Tools enables them."""
    if not _predictions_debug_enabled(owner):
        return
    rendered = message % args if args else message
    timestamp = datetime.now().isoformat(timespec="milliseconds")
    logger.info("[predictions-thread-debug][traits] %s", rendered)
    print(f"[predictions-thread-debug][{timestamp}][traits] {rendered}", file=sys.stderr, flush=True)


def _percentage_color(value: float, minimum: float, maximum: float) -> str:
    red, green, blue = appwide_red_green_rgb_for_range(value, minimum, maximum)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _format_signed_percentage(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.1f}%"


def _traits_table_header() -> str:
    return (
        "<tr>"
        "<th style='padding:1px 8px 2px 0; text-align:left; color:#f5f5f5;'>trait</th>"
        "<th style='padding:1px 8px 2px 0; text-align:right; color:#f5f5f5;'>%</th>"
        "<th style='padding:1px 0 2px 0; text-align:right; color:#f5f5f5;'>vs DB</th>"
        "</tr>"
    )


def _trait_rank_row(
    name: str,
    percentage: float,
    *,
    color: str,
    db_average: float,
    db_deviation: float,
) -> str:
    safe_name = html.escape(name)
    pct = max(0.0, min(100.0, percentage))
    safe_color = html.escape(normalize_trait_color(color))
    safe_href = html.escape(f"trait:{urllib.parse.quote(name, safe='')}", quote=True)
    difference_text = html.escape(_format_signed_percentage(db_deviation))
    percentage_color = _percentage_color(pct, 0.0, 100.0)
    difference_color = _percentage_color(db_deviation, -100.0, 100.0)
    safe_title = html.escape(f"DB average: {max(0.0, min(100.0, db_average)):.1f}%")
    return (
        "<tr>"
        f"<td style='padding:1px 8px 1px 0; white-space:nowrap; color:{safe_color};' title='{safe_title}'>"
        f"<a href='{safe_href}' style='color:{safe_color}; text-decoration:none;'>{safe_name}</a>"
        "</td>"
        f"<td style='padding:1px 8px 1px 0; text-align:right; color:{percentage_color};'>{pct:.1f}%</td>"
        f"<td style='padding:1px 0; text-align:right; color:{difference_color};'>{difference_text}</td>"
        "</tr>"
    )


def _trait_table(title: str, rows: list[tuple[str, float, float, float]], color_by_name: dict[str, str]) -> str:
    if rows:
        body = "".join(
            _trait_rank_row(
                name,
                pct,
                color=color_by_name.get(name, DEFAULT_TRAIT_COLOR),
                db_average=db_average,
                db_deviation=db_deviation,
            )
            for name, pct, db_average, db_deviation in rows
        )
    else:
        body = (
            "<tr><td colspan='3' style='padding:3px 0; color:#9a9a9a;'>"
            "No traits meet the 5% deviation threshold."
            "</td></tr>"
        )
    return (
        f"<div style='padding-bottom:3px;'><b>{html.escape(title)}</b></div>"
        "<table cellspacing='0' cellpadding='0' style='width:100%;'>"
        f"{_traits_table_header()}{body}"
        "</table>"
    )


def _trait_sample_count(trait: dict[str, Any]) -> int:
    samples = trait.get("samples")
    if samples is None and isinstance(trait.get("profile"), dict):
        samples = trait["profile"].get("samples")
    return trait_sample_total(samples, trait_name=str(trait.get("name", "")))


def _trait_info_html(trait: dict[str, Any], chart: Any | None = None) -> str:
    name = str(trait.get("name", "")).strip() or "Trait"
    color = normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR)))
    description = str(trait.get("description", "")).strip() or "no description provided"
    sample_count = _trait_sample_count(trait)
    evidence_html = ""
    if chart is not None:
        chart_name = str(getattr(chart, "name", "") or "").strip()
        matching_factors_header = (
            f"Matching factors in {html.escape(chart_name)}'s chart:"
            if chart_name
            else "Matching factors in this chart:"
        )
        matches = matched_weighted_criteria(chart, trait.get("profile", {}))
        positive = matches.get("positive", [])
        negative = matches.get("negative", [])

        def _dominance_labels(polarity: str) -> set[str]:
            prefix = "anti" if polarity == "negative" else ""
            labels = {
                str(value)
                for category in ("signs", "bodies", "nakshatras")
                for value in weighted_string_entries(trait.get("profile", {}).get(f"{prefix}{category}", {}))
            }
            labels.update(
                f"House {value}"
                for value in weighted_house_entries(trait.get("profile", {}).get(f"{prefix}houses", {}))
            )
            return labels

        def _factor_list(values: list[str], color: str, *, polarity: str) -> str:
            dominance_labels = _dominance_labels(polarity)
            return "".join(
                f"<li style='margin:2px 0; color:{color};'>"
                f"{html.escape(value)}{' above baseline in chart' if value in dominance_labels else ''}</li>" #note: above baseline doesn't mean "top 3 most dominant", nor does it mean "above average database wide" (i.e. 'a distinguishing factor'); would we get better trait results if we were scoring based on THAT, or matching 'dominance to dominance'?
                for value in values
            )

        evidence_html = (
            "<div style='height:12px;'></div>"
            f"<div style='font-size:12px; font-weight:700; color:{CHART_DATA_HIGHLIGHT_COLOR};'>"
            f"{matching_factors_header}</div>"
            "<div style='height:12px;'></div>"
        )
        if positive:
            evidence_html += (
                "<div style='font-size:12px; font-weight:700; color:#9fd6aa;'>Supporting:</div>"
                f"<ul style='margin:3px 0 5px 18px; padding:0;'>{_factor_list(positive, '#d9f2de', polarity='positive')}</ul>"
            )
        if negative:
            evidence_html += (
                "<div style='margin-top:5px; font-size:9px; color:#e1a1a1;'>COUNTER-FACTORS</div>"
                f"<ul style='margin:3px 0 5px 18px; padding:0;'>{_factor_list(negative, '#f0d3d3', polarity='negative')}</ul>"
            )
        if not positive and not negative:
            evidence_html += (
                "<div style='margin-top:5px; font-size:10px; color:#b8b8b8;'>"
                "No configured factors directly matched this chart.</div>"
            )
    return (
        f"<div style='font-size:18px; font-weight:700; color:{html.escape(color)};'>"
        f"{html.escape(name)}</div>"
        "<div style='height:6px;'></div>"
        "<div style='font-size:12px; color:#f5f5f5; font-style:italic; line-height:1.35;'>"
        f"{html.escape(description).replace(chr(10), '<br>')}"
        "</div>"
        "<div style='height:8px;'></div>"
        "<div style='font-size:9px; color:#b8b8b8; font-variant:small-caps; letter-spacing:0.8px;'>"
        f"based on aggregated data from {sample_count} charts"
        "</div>"
        f"{evidence_html}"
    )


def _show_trait_chart_info(owner: Any, trait_name: str) -> None:
    trait_lookup = getattr(owner, "_traits_prediction_trait_lookup", {}) or {}
    trait = trait_lookup.get(str(trait_name or "").casefold())
    if trait is None:
        return
    set_mode = getattr(owner, "_set_chart_info_panel_mode", None)
    if callable(set_mode):
        set_mode("chart_info")
    output = getattr(owner, "chart_info_output", None)
    if isinstance(output, QWidget) or hasattr(output, "setHtml") or hasattr(output, "setPlainText"):
        set_chart_info_html(output, _trait_info_html(trait, getattr(owner, "_traits_prediction_chart", None)))


def _on_trait_prediction_link_activated(owner: Any, target: str) -> None:
    if str(target or "") == "trait-predictions:calculate":
        _start_traits_prediction_calculation(owner)
        return
    if str(target or "") == "trait-predictions:failures":
        detail = str(getattr(owner, "_traits_prediction_failure_detail", "") or "")
        if detail:
            QMessageBox.information(owner, "Traits that failed to load", detail)
        return
    parts = str(target or "").split(":", 1)
    if len(parts) != 2 or parts[0] != "trait":
        return
    _show_trait_chart_info(owner, urllib.parse.unquote(parts[1]))


def _configure_traits_prediction_label(owner: Any, label: QLabel) -> None:
    label.setOpenExternalLinks(False)
    label.setTextFormat(Qt.RichText)
    label.setTextInteractionFlags(Qt.TextBrowserInteraction)
    apply_chart_info_link_cursor(label)
    if getattr(label, "_ephemeraldaddy_trait_links_connected", False):
        return
    label.linkActivated.connect(lambda target: _on_trait_prediction_link_activated(owner, target))
    label._ephemeraldaddy_trait_links_connected = True


def _stable_json_hash(value: Any) -> str:
    try:
        payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    except TypeError:
        payload = repr(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _database_cache_revision(owner: Any) -> tuple[int, int]:
    """Return the owner revision tokens that invalidate DB-wide trait helpers."""
    return (
        int(getattr(owner, "_database_metrics_cache_revision", 0) or 0),
        int(getattr(owner, "_prediction_norms_revision", 0) or 0),
    )


def _owner_memoized(owner: Any, attr_name: str, builder: Any) -> Any:
    revision = _database_cache_revision(owner)
    cached = getattr(owner, attr_name, None)
    if isinstance(cached, dict) and cached.get("revision") == revision:
        return cached.get("value")
    value = builder()
    try:
        setattr(owner, attr_name, {"revision": revision, "value": value})
    except Exception:
        pass
    return value


def _database_chart_rows(owner: Any) -> list[Any]:
    chart_rows = list(getattr(owner, "_chart_rows", []) or [])
    if chart_rows:
        return chart_rows
    try:
        return list(db.list_charts())
    except Exception as exc:
        logger.warning("Traits panel could not load database chart rows for DB averages: %s", exc, exc_info=True)
        return []


def _database_chart_uids(owner: Any) -> tuple[str, ...]:
    def _build() -> tuple[str, ...]:
        chart_rows = _database_chart_rows(owner)
        chart_uids: set[str] = set()
        for row in chart_rows:
            raw_uid = None
            try:
                if len(row) > 30:
                    raw_uid = row[30]
            except TypeError:
                raw_uid = None
            chart_uid = str(raw_uid or "").strip().upper()
            if chart_uid:
                chart_uids.add(chart_uid)
        return tuple(sorted(chart_uids))

    return _owner_memoized(owner, "_traits_prediction_database_chart_uids_cache", _build)


def _chart_uid_for_trait_metadata(chart: Any) -> str | None:
    chart_uid = str(getattr(chart, "chart_uid", "") or "").strip()
    return chart_uid or None


def _debug_chart_uid(chart: Any) -> str:
    chart_uid = _chart_uid_for_trait_metadata(chart)
    return chart_uid or "unavailable"


def _database_chart_uid_for_chart(chart: Any) -> str | None:
    """Resolve a chart object to its permanent persisted UID."""
    chart_uid = str(getattr(chart, "chart_uid", "") or "").strip().upper()
    return chart_uid or None


def _persisted_chart_signature_matches_current(chart_uid: str, chart: Any) -> bool:
    """Return whether the saved row for ``chart_uid`` has the same scoring signature as ``chart``."""
    try:
        persisted_chart = db.load_chart_by_uid(chart_uid)
    except Exception as exc:
        logger.warning("Traits panel could not load chart UID %s for cache freshness check: %s", chart_uid, exc, exc_info=True)
        return False
    if persisted_chart is None:
        return False
    return _chart_trait_metadata_signature(persisted_chart) == _chart_trait_metadata_signature(chart)


def trait_likelihoods_with_distribution_cache(
    owner: Any,
    chart: Any,
    traits: list[dict[str, Any]],
) -> dict[str, float]:
    """Score traits through the shared Database Analytics likelihood cache when possible.

    Database Analytics, Chart View Traits, and Fantasy RPG alignment traits all use this
    wrapper so persisted database charts are scored once per analytical profile.
    Draft/unsaved charts still fall back to direct scoring because they do not
    have stable database row tokens for the persisted cache.
    """
    if chart is None or not traits:
        return {}
    collect = getattr(owner, "_collect_traits_distribution_analytics_by_uids", None)
    signature_builder = getattr(owner, "_traits_distribution_signature", None)
    chart_uid = _database_chart_uid_for_chart(chart) or ""
    if (
        not callable(collect)
        or not callable(signature_builder)
        or not chart_uid
        or not _persisted_chart_signature_matches_current(chart_uid, chart)
    ):
        return calculate_trait_likelihoods(chart, traits)
    try:
        signature = signature_builder(traits)
        analytics = collect(
            [chart_uid],
            trait_items=traits,
            trait_signature=signature,
            time_budget_seconds=None,
        )
        chart_count = int(analytics.get("chart_count", 0) or 0)
        totals = analytics.get("totals", {})
        if chart_count > 0 and isinstance(totals, dict):
            return {
                str(name): round((float(totals.get(name, 0.0)) / float(chart_count)) * 100.0, 1)
                for name in analytics.get("trait_names", [])
            }
    except Exception as exc:
        logger.warning(
            "Trait likelihoods could not use shared distribution cache for chart %s: %s",
            getattr(chart, "chart_uid", getattr(chart, "name", "unknown")),
            exc,
            exc_info=True,
        )
    return calculate_trait_likelihoods(chart, traits)


def _chart_trait_metadata_signature(chart: Any) -> str:
    """Fingerprint only the birth-data inputs that should invalidate predictions.

    Trait/Fantasy RPG/Enneagram Predictions are persisted per permanent chart UID and
    should remain instantly reusable across Chart View opens.  This is the full
    staleness boundary for chart edits: only astro-data inputs belong here;
    nonastral/subjective metadata must not invalidate Traits.  Derived astrology
    payloads (positions, aspects, HD/BaZi weights, etc.) are intentionally not
    part of this signature: those values are recalculated from the essential
    birth data elsewhere, and including them here makes harmless serialization or
    lazy-loading differences look like a changed chart.
    """
    try:
        uses_houses = bool(chart_uses_houses(chart))
    except Exception:
        uses_houses = bool(getattr(chart, "use_birth_time_data", False))
    return _stable_json_hash(
        {
            "birth_date": getattr(chart, "birth_date", None),
            "birth_time": getattr(chart, "birth_time", None),
            "dt": getattr(chart, "dt", None),
            "dt_local": getattr(chart, "dt_local", None),
            "birth_place": getattr(chart, "birth_place", None),
            "datetime": getattr(chart, "datetime", None),
            "datetime_iso": getattr(chart, "datetime_iso", None),
            "lat": getattr(chart, "lat", None),
            "lon": getattr(chart, "lon", None),
            "birthtime_unknown": bool(getattr(chart, "birthtime_unknown", False)),
            "retcon_time_used": bool(getattr(chart, "retcon_time_used", False)),
            "retcon_hour": getattr(chart, "retcon_hour", None),
            "retcon_minute": getattr(chart, "retcon_minute", None),
            "rectification_range_used": bool(getattr(chart, "rectification_range_used", False)),
            "rectification_range_start_minute": getattr(chart, "rectification_range_start_minute", None),
            "rectification_range_end_minute": getattr(chart, "rectification_range_end_minute", None),
            "chart_uses_houses": uses_houses,
        }
    )


def _database_norm_chart_token_source(owner: Any) -> tuple[tuple[str, str], ...]:
    """Return stable tokens for the non-placeholder charts that define DB norms."""
    rows_provider = getattr(owner, "_prediction_norm_rows", None)
    normalize_row = getattr(owner, "_normalize_chart_row", None)
    rows: list[Any] = []
    if callable(rows_provider):
        try:
            rows = list(rows_provider())
        except Exception:
            rows = []
    if not rows:
        return tuple((uid, "") for uid in _database_chart_uids(owner))

    normalized_rows_by_uid: dict[str, Any] = {}
    for row in rows:
        normalized = normalize_row(row) if callable(normalize_row) else row
        if normalized is None:
            continue
        uid = str(normalized[30] or "").strip().upper() if isinstance(normalized, (list, tuple)) and len(normalized) > 30 else ""
        if uid:
            normalized_rows_by_uid[uid] = normalized

    tokens: list[tuple[str, str]] = []
    for uid, normalized in normalized_rows_by_uid.items():
        tokens.append((uid, _stable_json_hash(_database_norm_chart_token_payload(normalized, uid))))
    return tuple(sorted(tokens))


def _database_norm_chart_token_payload(row: Any, uid: str) -> dict[str, Any]:
    """Return only scoring-relevant chart fields for Traits DB norm invalidation.

    Trait likelihoods are derived from birth metadata and whether the chart can
    use houses.  User notes, tags, biography/source imports, subjective scores,
    and display-only cached analytics must not invalidate database norms or an
    import/save can trigger a full Predictions refresh for unrelated text edits.
    """
    values = tuple(row) if isinstance(row, (list, tuple)) else ()

    def _get(index: int, default: Any = None) -> Any:
        return values[index] if index < len(values) else default

    return {
        "uid": str(uid or "").strip().upper(),
        "datetime_iso": str(_get(4, "") or ""),
        "birth_place": str(_get(5, "") or ""),
        "birthtime_unknown": int(_get(8, 0) or 0),
        "retcon_time_used": int(_get(9, 0) or 0),
        "birth_month": _get(17),
        "birth_day": _get(18),
        "birth_year": _get(19),
        "retcon_hour": _get(20),
        "retcon_minute": _get(21),
    }

def _database_norm_state(owner: Any) -> dict[str, Any]:
    def _build() -> dict[str, Any]:
        tokens = _database_norm_chart_token_source(owner)
        return {
            "version": TRAIT_DB_NORMS_CACHE_VERSION,
            "chart_count": len(tokens),
            "chart_tokens": {uid: token for uid, token in tokens},
        }

    return _owner_memoized(owner, "_traits_prediction_database_norm_state_cache", _build)


def _database_norm_signature_from_state(state: dict[str, Any]) -> str:
    """Return the DB-norm generation used by per-chart metadata."""
    return _stable_json_hash(
        {
            "version": TRAIT_DB_NORMS_CACHE_VERSION,
            "scope": "database_statistics_threshold",
            "chart_count": int(state.get("chart_count", 0) or 0),
            "chart_tokens": state.get("chart_tokens", {}),
        }
    )


def _trait_definition_signature(trait: dict[str, Any]) -> str:
    trait_uid = str(trait.get("uid") or trait.get("trait_uid") or "").strip()
    scoring_profile = _trait_analytical_profile(trait.get("profile", {}), strip_uids=True)
    return _stable_json_hash(
        {
            "version": TRAIT_DB_NORMS_CACHE_VERSION,
            "uid": trait_uid,
            "profile": scoring_profile,
        }
    )


def _trait_uid_for_item(trait: dict[str, Any]) -> str:
    uid = str(trait.get("uid") or trait.get("trait_uid") or "").strip()
    if uid:
        return uid
    name = str(trait.get("name", "")).strip()
    return trait_uid_for_profile(name, trait.get("profile", {}) if isinstance(trait.get("profile"), dict) else {})


def _trait_uids_for_names(names: set[str], trait_uids_by_name: dict[str, str]) -> list[str]:
    return sorted(uid for name in names if (uid := str(trait_uids_by_name.get(name, "")).strip()))


def _trait_uid_mapping_for_names(values_by_name: dict[str, float], trait_uids_by_name: dict[str, str]) -> dict[str, float]:
    return {
        uid: value
        for name, value in values_by_name.items()
        if (uid := str(trait_uids_by_name.get(name, "")).strip())
    }


def _direction_for_deviation(deviation: float) -> str:
    threshold = TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD
    if deviation >= threshold:
        return "above"
    if deviation <= -threshold:
        return "below"
    return "neutral"


def _metadata_from_vectors(
    *,
    likelihoods: dict[str, float],
    database_averages: dict[str, float],
    stale_chart_vector: bool = False,
    stale_trait_definition: bool = False,
    stale_db_baseline: bool = False,
    updated_at: str = "",
    stale_trait_names: set[str] | None = None,
    full_staleness_reasons: list[str] | None = None,
) -> dict[str, Any]:
    deviations = {
        name: float(pct) - float(database_averages[name])
        for name, pct in likelihoods.items()
        if name in database_averages
    }
    above = {name for name, deviation in deviations.items() if deviation >= TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD}
    below = {name for name, deviation in deviations.items() if deviation <= -TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD}
    stale = bool(stale_chart_vector or stale_trait_definition or stale_db_baseline or stale_trait_names)
    stale_trait_names = set(stale_trait_names or set())
    full_staleness_reasons = list(full_staleness_reasons or [])
    if stale_chart_vector and "astro_data" not in full_staleness_reasons:
        full_staleness_reasons.append("astro_data")
    if stale_db_baseline and "database_norms" not in full_staleness_reasons:
        full_staleness_reasons.append("database_norms")
    if stale_trait_definition and not stale_trait_names and "all_traits" not in full_staleness_reasons:
        full_staleness_reasons.append("all_traits")
    staleness_kind = "fresh"
    if stale:
        staleness_kind = "full" if full_staleness_reasons else "partial"
    metadata: dict[str, Any] = {
        "above": above,
        "below": below,
        "deviations": deviations,
        "likelihoods": likelihoods,
        "database_averages": database_averages,
        "stale_chart_vector": bool(stale_chart_vector),
        "stale_trait_definition": bool(stale_trait_definition),
        "stale_db_baseline": bool(stale_db_baseline),
        "staleness_kind": staleness_kind,
        "stale_trait_names": sorted(stale_trait_names),
        "full_staleness_reasons": full_staleness_reasons,
    }
    if stale:
        metadata["stale"] = True
    if updated_at:
        metadata["updated_at"] = updated_at
    return metadata


def _apply_trait_metadata_to_chart(
    chart: Any,
    metadata: dict[str, Any],
    trait_uids_by_name: dict[str, str],
    signature: tuple[Any, ...],
) -> None:
    above = set(metadata.get("above", set()) or set())
    below = set(metadata.get("below", set()) or set())
    deviations = dict(metadata.get("deviations", {}) or {})
    likelihoods = dict(metadata.get("likelihoods", {}) or {})
    above_uids = _trait_uids_for_names(above, trait_uids_by_name)
    below_uids = _trait_uids_for_names(below, trait_uids_by_name)
    setattr(chart, "predicted_traits_above_avg", set(above))
    setattr(chart, "predicted_traits_below_avg", set(below))
    setattr(chart, "predicted_trait_deviations", dict(deviations))
    setattr(chart, "traits", list(above_uids))
    setattr(chart, "traits_above_average", list(above_uids))
    setattr(chart, "traits_below_average", list(below_uids))
    setattr(chart, "trait_likelihoods", _trait_uid_mapping_for_names(likelihoods, trait_uids_by_name))
    if not bool(metadata.get("stale")):
        setattr(chart, "_trait_prediction_metadata_cache", {"signature": signature, "metadata": metadata})


def _trait_analytical_profile(profile: Any, *, strip_uids: bool = False) -> dict[str, Any]:
    """Return only scoring-relevant trait factors, excluding display-only metadata."""
    return analytical_mapping_signature(profile, strip_uids=strip_uids)


def _trait_signature_payload(traits: list[dict[str, Any]], *, strip_uids: bool = False) -> dict[str, Any]:
    trait_payloads: list[dict[str, Any]] = []
    for trait in traits:
        profile = _trait_analytical_profile(trait.get("profile", {}), strip_uids=strip_uids)
        trait_payloads.append(
            {
                "uid": "" if strip_uids else str(trait.get("uid") or trait.get("trait_uid") or "").strip(),
                "profile": profile,
            }
        )
    return {"version": TRAIT_DB_NORMS_CACHE_VERSION, "traits": trait_payloads}


def _trait_display_signature_payload(traits: list[dict[str, Any]]) -> dict[str, Any]:
    """Return display-only fields that can make cached Traits HTML stale."""
    return {
        "version": TRAIT_DB_NORMS_CACHE_VERSION,
        "traits": [
            {
                "uid": str(trait.get("uid") or trait.get("trait_uid") or "").strip(),
                "name": str(trait.get("name", "")).strip(),
                "color": normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR))),
            }
            for trait in traits
        ],
    }


def _trait_snapshot_norm_signature(
    traits: list[dict[str, Any]], snapshot: dict[str, Any] | None = None
) -> str:
    """Return the current or deterministically pending static snapshot generation."""
    resolved_snapshot = snapshot if snapshot is not None else load_prediction_norms_snapshot()
    token = prospective_trait_snapshot_token(traits, resolved_snapshot)
    return f"prediction_norms_snapshot:{token}"


def _calculate_database_trait_averages_direct(
    owner: Any,
    chart_uids: tuple[str, ...],
    traits: list[dict[str, Any]],
) -> dict[str, float]:
    """Calculate DB trait averages by stable chart UID without Database Analytics caches."""
    if not chart_uids or not traits:
        return {}
    is_placeholder = getattr(owner, "_is_placeholder_chart", None)
    chart_count = 0
    totals: dict[str, float] = {str(trait.get("name", "")).strip(): 0.0 for trait in traits}
    totals = {name: total for name, total in totals.items() if name}
    if not totals:
        return {}
    try:
        charts_by_uid = db.load_charts_by_uids(chart_uids)
    except Exception as exc:
        logger.warning("Traits panel could not load chart UIDs while calculating DB trait averages: %s", exc, exc_info=True)
        charts_by_uid = {}
    for chart_uid in chart_uids:
        chart_uid = str(chart_uid or "").strip().upper()
        chart = charts_by_uid.get(chart_uid)
        if chart is None:
            continue
        if callable(is_placeholder) and is_placeholder(chart):
            continue
        try:
            likelihoods = calculate_trait_likelihoods(chart, traits)
        except Exception as exc:
            logger.warning(
                "Traits panel could not score chart UID %s while calculating DB trait averages: %s",
                chart_uid,
                exc,
                exc_info=True,
            )
            continue
        chart_count += 1
        for name in totals:
            try:
                totals[name] += float(likelihoods.get(name, 0.0))
            except (TypeError, ValueError):
                continue
    if not chart_count:
        return {}
    return {name: total / float(chart_count) for name, total in totals.items()}


def _database_trait_averages(
    owner: Any,
    traits: list[dict[str, Any]],
    *,
    force_refresh_stale: bool = False,
    allow_partial: bool = False,
) -> dict[str, float]:
    _predictions_debug(owner, "Trait DB averages requested traits=%s", len(traits))
    if not force_refresh_stale:
        snapshot = load_prediction_norms_snapshot()
        snapshot_averages = trait_snapshot_averages(traits, snapshot)
        missing_traits = missing_trait_norms(traits, snapshot)
        if missing_traits:
            missing_names = sorted(
                str(trait.get("name", "") or "").strip()
                for trait in missing_traits
                if str(trait.get("name", "") or "").strip()
            )
            reason = (
                "Static trait norms are missing or analytically outdated for: "
                + ", ".join(missing_names)
                + ". Add/edit those traits through Settings to calculate only those profiles, "
                "or use Reassess unavailable traits to repair only those profiles."
            )
            logger.warning("Traits panel bypassed unavailable profiles: %s", reason)
        requested_names = {
            str(trait.get("name", "") or "").strip()
            for trait in traits
            if str(trait.get("name", "") or "").strip()
        }
        unresolved = sorted(requested_names - set(snapshot_averages))
        if unresolved:
            logger.warning("Traits panel bypassed unresolved trait norm profiles: %s", ", ".join(unresolved))
        return {name: float(snapshot_averages[name]) for name in requested_names if name in snapshot_averages}
    chart_uids = _database_chart_uids(owner)
    collect = getattr(owner, "_collect_traits_distribution_analytics_by_uids", None)
    signature_builder = getattr(owner, "_traits_distribution_signature", None)
    if not chart_uids:
        raise RuntimeError("Trait norm generation requires at least one persisted chart UID.")
    if not callable(collect) or not callable(signature_builder):
        averages = _calculate_database_trait_averages_direct(owner, chart_uids, traits)
        if len(averages) != len(traits):
            raise RuntimeError("Trait norm generation did not score every requested trait.")
        return averages
    _predictions_debug(
        owner,
        "Trait DB averages calculating requested profiles=%s chart_uids=%s",
        len(traits),
        len(chart_uids),
    )
    analytics = collect(
        chart_uids,
        trait_items=traits,
        trait_signature=signature_builder(traits),
        time_budget_seconds=None,
    )
    chart_count = max(0, int(analytics.get("chart_count", 0)))
    if not chart_count:
        raise RuntimeError("Trait norm generation returned no scored database charts.")
    totals = analytics.get("totals", {})
    averages: dict[str, float] = {}
    for trait_name in analytics.get("trait_names", []):
        name = str(trait_name)
        averages[name] = (float(totals.get(name, 0.0)) / float(chart_count)) * 100.0
    requested_names = {
        str(trait.get("name", "") or "").strip()
        for trait in traits
        if str(trait.get("name", "") or "").strip()
    }
    if set(averages) != requested_names and not allow_partial:
        missing = sorted(requested_names - set(averages))
        raise RuntimeError("Trait norm generation omitted: " + ", ".join(missing))
    return averages


def trait_metadata_for_chart(
    owner: Any,
    chart: Any,
    *,
    cached_only: bool = False,
    traits: list[dict[str, Any]] | None = None,
    trait_signature: str | None = None,
    legacy_trait_signature: str | None = None,
    norm_signature: str | None = None,
    chart_signature: str | None = None,
) -> dict[str, Any] | None:
    """Return and attach derived trait metadata for a chart."""
    _predictions_debug(owner, "Trait metadata start chart_uid=%s", _debug_chart_uid(chart))
    traits = traits if traits is not None else list_traits(active_only=True)
    if chart is None or getattr(owner, "_is_placeholder_chart", lambda _chart: False)(chart) or not traits:
        metadata = {"above": set(), "below": set(), "deviations": {}, "likelihoods": {}}
        setattr(chart, "predicted_traits_above_avg", set())
        setattr(chart, "predicted_traits_below_avg", set())
        setattr(chart, "predicted_trait_deviations", {})
        setattr(chart, "traits", [])
        setattr(chart, "traits_above_average", [])
        setattr(chart, "traits_below_average", [])
        setattr(chart, "trait_likelihoods", {})
        return metadata

    trait_signature = trait_signature or _stable_json_hash(_trait_signature_payload(traits))
    legacy_trait_signature = legacy_trait_signature or _stable_json_hash(_trait_signature_payload(traits, strip_uids=True))
    norm_signature = norm_signature or _trait_snapshot_norm_signature(traits)
    chart_signature = chart_signature or _chart_trait_metadata_signature(chart)
    chart_uid = _chart_uid_for_trait_metadata(chart)
    signature = (TRAIT_DB_NORMS_CACHE_VERSION, chart_uid, trait_signature, norm_signature, chart_signature)
    cached = getattr(chart, "_trait_prediction_metadata_cache", None)
    if isinstance(cached, dict) and cached.get("signature") == signature:
        _predictions_debug(owner, "Trait metadata memory cache hit chart_uid=%s", _debug_chart_uid(chart))
        return dict(cached.get("metadata", {}))

    traits_by_name = {str(trait.get("name", "")).strip(): trait for trait in traits if str(trait.get("name", "")).strip()}
    trait_uids_by_name = {name: _trait_uid_for_item(trait) for name, trait in traits_by_name.items()}
    traits_by_uid = {uid: trait for name, trait in traits_by_name.items() if (uid := trait_uids_by_name.get(name))}
    names_by_uid = {uid: name for name, uid in trait_uids_by_name.items() if uid}
    active_trait_names = set(traits_by_name)
    if chart_uid:
        try:
            indexed_result = global_trait_prediction_index().read_cached(
                TraitPredictionQuery(
                    chart_uid=chart_uid,
                    chart_signature=chart_signature,
                    trait_signature=trait_signature,
                    norm_signature=norm_signature,
                ),
                traits,
            )
        except Exception as exc:
            logger.warning("Traits panel could not read from trait prediction index: %s", exc, exc_info=True)
            indexed_result = None
        if indexed_result is not None and not indexed_result.stale_db_baseline:
            metadata = _metadata_from_vectors(
                likelihoods=indexed_result.likelihoods,
                database_averages=indexed_result.database_averages,
                stale_chart_vector=indexed_result.stale_chart_vector,
                stale_trait_definition=indexed_result.stale_trait_definition,
                stale_db_baseline=indexed_result.stale_db_baseline,
                updated_at=indexed_result.updated_at,
            )
            _apply_trait_metadata_to_chart(chart, metadata, trait_uids_by_name, signature)
            return metadata
    baseline_rows_by_name: dict[str, dict[str, Any]] = {}
    try:
        baseline_rows = db.get_trait_baseline_snapshot(
            norm_signature=norm_signature,
            trait_signature=trait_signature,
        )
    except Exception as exc:
        logger.warning("Traits panel skipped cached DB baseline snapshot: %s", exc, exc_info=True)
        baseline_rows = []
    for row in baseline_rows:
        row_uid = str(row.get("trait_uid", "") or "").strip()
        name = names_by_uid.get(row_uid) if row_uid else str(row.get("trait_name", "")).strip()
        if name in traits_by_name:
            baseline_rows_by_name[name] = row
    snapshot_database_averages = {
        name: float(row.get("db_average", 0.0))
        for name, row in baseline_rows_by_name.items()
    }
    baseline_is_complete = bool(active_trait_names) and set(snapshot_database_averages) == active_trait_names
    cached_rows_by_name: dict[str, dict[str, Any]] = {}
    stale_rows_by_name: dict[str, dict[str, Any]] = {}
    stale_chart_rows_by_name: dict[str, dict[str, Any]] = {}
    stale_norm_rows_by_name: dict[str, dict[str, Any]] = {}
    cached_likelihood_rows_by_name: dict[str, dict[str, Any]] = {}
    stale_likelihood_rows_by_name: dict[str, dict[str, Any]] = {}
    stale_trait_definition_rows_by_name: dict[str, dict[str, Any]] = {}
    if chart_uid is not None:
        try:
            likelihood_rows = db.get_chart_trait_likelihoods(chart_uid)
        except Exception as exc:
            logger.warning(
                "Traits panel skipped cached chart-local trait likelihoods for chart UID %s: %s",
                chart_uid,
                exc,
                exc_info=True,
            )
            likelihood_rows = []
        for row in likelihood_rows:
            row_uid = str(row.get("trait_uid", "") or "").strip()
            name = names_by_uid.get(row_uid) if row_uid else str(row.get("trait_name", "")).strip()
            trait = traits_by_uid.get(row_uid) if row_uid else traits_by_name.get(name)
            if trait is None:
                continue
            row_trait_signature = str(row.get("trait_signature", ""))
            valid_trait_signature = row_trait_signature in {
                trait_signature,
                legacy_trait_signature,
                _trait_definition_signature(trait),
            }
            if valid_trait_signature and str(row.get("chart_signature", "")) == chart_signature:
                cached_likelihood_rows_by_name[name] = row
            elif valid_trait_signature:
                stale_likelihood_rows_by_name[name] = row
            else:
                stale_trait_definition_rows_by_name[name] = row
        if active_trait_names and set(cached_likelihood_rows_by_name) == active_trait_names and baseline_is_complete:
            latest_updated_at = max(
                (str(row.get("updated_at", "") or "") for row in [*cached_likelihood_rows_by_name.values(), *baseline_rows_by_name.values()]),
                default="",
            )
            metadata = _metadata_from_vectors(
                likelihoods={name: float(row.get("likelihood", 0.0)) for name, row in cached_likelihood_rows_by_name.items()},
                database_averages=snapshot_database_averages,
                updated_at=latest_updated_at,
            )
            _apply_trait_metadata_to_chart(chart, metadata, trait_uids_by_name, signature)
            return metadata
        if (
            cached_only
            and active_trait_names
            and set(stale_likelihood_rows_by_name) == active_trait_names
            and baseline_is_complete
        ):
            latest_updated_at = max(
                (str(row.get("updated_at", "") or "") for row in [*stale_likelihood_rows_by_name.values(), *baseline_rows_by_name.values()]),
                default="",
            )
            return _metadata_from_vectors(
                likelihoods={name: float(row.get("likelihood", 0.0)) for name, row in stale_likelihood_rows_by_name.items()},
                database_averages=snapshot_database_averages,
                stale_chart_vector=True,
                updated_at=latest_updated_at,
            )
        if (
            cached_only
            and active_trait_names
            and set(stale_trait_definition_rows_by_name) == active_trait_names
            and baseline_is_complete
        ):
            latest_updated_at = max(
                (str(row.get("updated_at", "") or "") for row in [*stale_trait_definition_rows_by_name.values(), *baseline_rows_by_name.values()]),
                default="",
            )
            return _metadata_from_vectors(
                likelihoods={name: float(row.get("likelihood", 0.0)) for name, row in stale_trait_definition_rows_by_name.items()},
                database_averages=snapshot_database_averages,
                stale_trait_definition=True,
                updated_at=latest_updated_at,
            )
        try:
            rows = db.get_chart_trait_metadata(chart_uid)
        except Exception as exc:
            logger.warning(
                "Traits panel skipped cached DB trait metadata for chart UID %s: %s",
                chart_uid,
                exc,
                exc_info=True,
            )
            rows = []
        for row in rows:
            row_uid = str(row.get("trait_uid", "") or "").strip()
            name = names_by_uid.get(row_uid) if row_uid else str(row.get("trait_name", "")).strip()
            trait = traits_by_uid.get(row_uid) if row_uid else traits_by_name.get(name)
            if trait is None:
                continue
            row_trait_signature = str(row.get("trait_signature", ""))
            valid_trait_signature = row_trait_signature in {
                trait_signature,
                legacy_trait_signature,
                _trait_definition_signature(trait),
            }
            if (
                valid_trait_signature
                and str(row.get("norm_signature", "")) == norm_signature
                and str(row.get("chart_signature", "")) == chart_signature
            ):
                cached_rows_by_name[name] = row
            elif valid_trait_signature:
                # cached_only callers are trying to paint *something* immediately.
                # If either chart astro-data or DB norms changed, the row is fully
                # stale, but it is still a better cached result than a misleading
                # "no data" placeholder while explicit recalculation remains available.
                stale_rows_by_name[name] = row
                if str(row.get("chart_signature", "")) != chart_signature:
                    stale_chart_rows_by_name[name] = row
                if str(row.get("norm_signature", "")) != norm_signature:
                    stale_norm_rows_by_name[name] = row
        if active_trait_names and set(cached_rows_by_name) == active_trait_names:
            _predictions_debug(owner, "Trait metadata DB row cache hit chart_uid=%s traits=%s", chart_uid, len(active_trait_names))
            above = {name for name, row in cached_rows_by_name.items() if row.get("direction") == "above"}
            below = {name for name, row in cached_rows_by_name.items() if row.get("direction") == "below"}
            deviations = {name: float(row.get("deviation", 0.0)) for name, row in cached_rows_by_name.items()}
            likelihoods = {name: float(row.get("likelihood", 0.0)) for name, row in cached_rows_by_name.items()}
            database_averages = {name: float(row.get("db_average", 0.0)) for name, row in cached_rows_by_name.items()}
            metadata = {
                "above": above,
                "below": below,
                "deviations": deviations,
                "likelihoods": likelihoods,
                "database_averages": database_averages,
            }
            above_uids = _trait_uids_for_names(above, trait_uids_by_name)
            below_uids = _trait_uids_for_names(below, trait_uids_by_name)
            setattr(chart, "predicted_traits_above_avg", set(above))
            setattr(chart, "predicted_traits_below_avg", set(below))
            setattr(chart, "predicted_trait_deviations", dict(deviations))
            setattr(chart, "traits", list(above_uids))
            setattr(chart, "traits_above_average", list(above_uids))
            setattr(chart, "traits_below_average", list(below_uids))
            setattr(chart, "trait_likelihoods", _trait_uid_mapping_for_names(likelihoods, trait_uids_by_name))
            setattr(chart, "_trait_prediction_metadata_cache", {"signature": signature, "metadata": metadata})
            return metadata
        if cached_only and (cached_rows_by_name or stale_rows_by_name):
            # Chart View must never revoke UID-owned trait metadata just because
            # one of the cache signatures drifted or because the active trait
            # working set changed after the chart was last calculated.  Any
            # rows previously persisted for this chart UID remain displayable;
            # stale/incomplete rows merely earn a Recalculate prompt above the
            # still-rendered table.
            display_rows_by_name = dict(stale_rows_by_name)
            display_rows_by_name.update(cached_rows_by_name)
            display_is_stale = bool(stale_rows_by_name) or set(display_rows_by_name) != active_trait_names
            _predictions_debug(
                owner,
                "Trait metadata displayable DB row cache hit chart_uid=%s traits=%s stale=%s",
                chart_uid,
                len(display_rows_by_name),
                display_is_stale,
            )
            above = {name for name, row in display_rows_by_name.items() if row.get("direction") == "above"}
            below = {name for name, row in display_rows_by_name.items() if row.get("direction") == "below"}
            latest_updated_at = max(
                (str(row.get("updated_at", "") or "") for row in display_rows_by_name.values()),
                default="",
            )
            stale_trait_names = active_trait_names - set(cached_rows_by_name)
            full_reasons: list[str] = []
            if active_trait_names and set(stale_chart_rows_by_name) >= active_trait_names:
                full_reasons.append("astro_data")
                stale_trait_names = set()
            if active_trait_names and set(stale_norm_rows_by_name) >= active_trait_names:
                full_reasons.append("database_norms")
                stale_trait_names = set()
            metadata = _metadata_from_vectors(
                likelihoods={name: float(row.get("likelihood", 0.0)) for name, row in display_rows_by_name.items()},
                database_averages={name: float(row.get("db_average", 0.0)) for name, row in display_rows_by_name.items()},
                updated_at=latest_updated_at,
                stale_trait_names=stale_trait_names if display_is_stale else set(),
                full_staleness_reasons=full_reasons,
            )
            return metadata

    if cached_only:
        return None

    cached_likelihoods = {
        name: float(row.get("likelihood", 0.0))
        for name, row in cached_likelihood_rows_by_name.items()
    }
    cached_likelihoods.update(
        {name: float(row.get("likelihood", 0.0)) for name, row in cached_rows_by_name.items()}
    )
    cached_database_averages = dict(snapshot_database_averages)
    cached_database_averages.update(
        {name: float(row.get("db_average", 0.0)) for name, row in cached_rows_by_name.items()}
    )
    missing_traits = [trait for name, trait in traits_by_name.items() if name not in cached_likelihoods]
    likelihoods = dict(cached_likelihoods)
    if missing_traits:
        _predictions_debug(owner, "Trait metadata scoring missing chart traits=%s", len(missing_traits))
        if len(missing_traits) == len(traits_by_name):
            likelihoods.update(
                global_trait_prediction_index().chart_likelihoods(
                    chart,
                    traits,
                    chart_signature=chart_signature,
                    trait_signature=trait_signature,
                )
            )
        else:
            likelihoods.update(trait_likelihoods_with_distribution_cache(owner, chart, missing_traits))
    database_averages = dict(cached_database_averages)
    missing_average_traits = [trait for name, trait in traits_by_name.items() if name not in database_averages]
    if missing_average_traits:
        _predictions_debug(owner, "Trait metadata resolving DB averages missing_traits=%s", len(missing_average_traits))
        database_averages.update(_database_trait_averages(owner, missing_average_traits))
    if set(database_averages) >= active_trait_names:
        try:
            db.upsert_trait_baseline_snapshot(
                norm_signature=norm_signature,
                trait_signature=trait_signature,
                rows=[
                    {
                        "trait_name": name,
                        "trait_uid": trait_uids_by_name.get(name, ""),
                        "db_average": database_averages.get(name, 0.0),
                    }
                    for name in active_trait_names
                ],
                chart_count=int(_database_norm_state(owner).get("chart_count", 0) or 0),
                norm_state=_database_norm_state(owner),
            )
        except Exception as exc:
            logger.warning("Traits panel could not persist full DB baseline snapshot: %s", exc, exc_info=True)
    metadata = _metadata_from_vectors(
        likelihoods=likelihoods,
        database_averages=database_averages,
    )
    unavailable_names = sorted(active_trait_names - set(database_averages))
    if unavailable_names:
        detail = (
            "Static trait norms are missing or analytically outdated for: "
            + ", ".join(unavailable_names)
            + ". Use Settings > Traits > Reassess unavailable traits to calculate only these profiles."
        )
        logger.warning("Traits panel rendered partial results; %s", detail)
        metadata["unavailable_traits"] = unavailable_names
        metadata["unavailable_trait_reason"] = detail
    _apply_trait_metadata_to_chart(chart, metadata, trait_uids_by_name, signature)
    if chart_uid is not None:
        rows_for_persistence = [
            {
                "trait_name": name,
                "trait_uid": trait_uids_by_name.get(name, ""),
                "trait_signature": trait_signature,
                "direction": _direction_for_deviation(float(metadata.get("deviations", {}).get(name, 0.0))),
                "likelihood": likelihoods.get(name, 0.0),
                "db_average": database_averages.get(name, 0.0),
                "deviation": metadata.get("deviations", {}).get(name, 0.0),
            }
            for name in active_trait_names
        ]
        try:
            db.upsert_chart_trait_likelihoods(
                chart_uid,
                rows_for_persistence,
                chart_signature=chart_signature,
            )
        except Exception as exc:
            logger.warning(
                "Traits panel could not update chart-local trait likelihoods for chart UID %s: %s",
                chart_uid,
                exc,
                exc_info=True,
            )
        try:
            db.upsert_chart_trait_metadata(
                chart_uid,
                rows_for_persistence,
                trait_signature=trait_signature,
                norm_signature=norm_signature,
                chart_signature=chart_signature,
            )
        except Exception as exc:
            logger.warning(
                "Traits panel could not update cached DB trait metadata for chart UID %s: %s",
                chart_uid,
                exc,
                exc_info=True,
            )
    return metadata


def _trait_predictions_cache_key(
    owner: Any,
    chart: Any | None,
    traits: list[dict[str, Any]],
    *,
    trait_signature: str | None = None,
    trait_display_signature: str | None = None,
    norm_signature: str | None = None,
    chart_signature: str | None = None,
) -> str | None:
    if chart is None:
        return None
    chart_uid = str(getattr(chart, "chart_uid", "") or "").strip().upper()
    chart_scope = f"uid:{chart_uid}" if chart_uid else "draft"
    trait_signature = trait_signature or _stable_json_hash(_trait_signature_payload(traits))
    trait_display_signature = trait_display_signature or _stable_json_hash(_trait_display_signature_payload(traits))
    if norm_signature is None:
        try:
            norm_signature = _trait_snapshot_norm_signature(traits)
        except Exception as exc:
            logger.warning(
                "Traits panel could not build DB norm signature for view cache: %s",
                exc,
                exc_info=True,
            )
            norm_signature = "norm:unavailable"
    chart_signature = chart_signature or _chart_trait_metadata_signature(chart)
    return _stable_json_hash(
        {
            "version": TRAIT_DB_NORMS_CACHE_VERSION,
            "chart_scope": chart_scope,
            "chart_signature": chart_signature,
            "trait_signature": trait_signature,
            "trait_display_signature": trait_display_signature,
            "norm_signature": norm_signature,
        }
    )


def _trait_predictions_refresh_message(updated_at: str | None) -> str:
    timestamp = html.escape((updated_at or "").replace("T", " "))
    return f"Current results last updated on {timestamp}" if timestamp else ""


def _set_traits_updated_label(owner: Any, updated_at: str | None) -> None:
    label = getattr(owner, "traits_prediction_updated_label", None)
    if isinstance(label, QLabel):
        label.setText(
            _trait_predictions_refresh_message(updated_at)
            or "Current results have not been calculated yet."
        )


def _traits_calculate_prompt_html() -> str:
    return "No prior data. Calculate (can take awhile)?"


def _traits_recalculate_prompt_html(updated_at: str | None) -> str:
    return f"Cached trait predictions shown (updated {html.escape(str(updated_at or 'unknown'))}). Recalculate to refresh.<br>"


def _traits_stale_recalculate_prompt_html(updated_at: str | None) -> str:
    return f"Cached trait predictions shown (updated {html.escape(str(updated_at or 'unknown'))}); birth data or norms changed. Recalculate to refresh.<br>"


def _set_traits_header_action(owner: Any, state: str) -> None:
    callback = getattr(owner, "_set_prediction_header_action", None)
    if callable(callback):
        callback("traits", state)


def _predictions_manual_recalculation_only(owner: Any) -> bool:
    # Predictions panel contract for future maintainers/agents:
    # default manual mode means "show the current chart UID's latest saved
    # metadata, flag stale data, and wait for the user's Recalculate click."
    # Do not silently refresh stale cached sections from render/draw paths.
    return bool(getattr(owner, "_predictions_manual_recalculation_only", True))


def _trait_render_signatures(owner: Any, chart: Any, traits: list[dict[str, Any]]) -> dict[str, str]:
    """Precompute all signatures used by one Traits render pass exactly once."""
    trait_signature = _stable_json_hash(_trait_signature_payload(traits))
    legacy_trait_signature = _stable_json_hash(_trait_signature_payload(traits, strip_uids=True))
    trait_display_signature = _stable_json_hash(_trait_display_signature_payload(traits))
    snapshot = load_prediction_norms_snapshot()
    missing_traits = missing_trait_norms(traits, snapshot)
    if missing_traits:
        # Missing profiles are repaired as one trait-scoped worker operation.
        # Use its deterministic future token now; never fall back to a live DB
        # cohort signature or hide partial coverage behind a "present" snapshot.
        _predictions_debug(owner, "Trait render awaiting snapshot repair traits=%s", len(missing_traits))
    norm_signature = _trait_snapshot_norm_signature(traits, snapshot)
    return {
        "trait_signature": trait_signature,
        "legacy_trait_signature": legacy_trait_signature,
        "trait_display_signature": trait_display_signature,
        "norm_signature": norm_signature,
        "chart_signature": _chart_trait_metadata_signature(chart),
    }


def _traits_pending_cached_metadata(owner: Any) -> dict[str, Any] | None:
    chart = getattr(owner, "_traits_prediction_pending_chart", None)
    traits = getattr(owner, "_traits_prediction_pending_traits", None)
    signatures = getattr(owner, "_traits_prediction_pending_signatures", None)
    if chart is None or not isinstance(traits, list) or not traits or not isinstance(signatures, dict):
        return None
    cache_key = str(getattr(owner, "_traits_prediction_pending_cache_key", "") or "")
    cached_pending = getattr(owner, "_traits_prediction_pending_metadata", None)
    if (
        isinstance(cached_pending, dict)
        and str(getattr(owner, "_traits_prediction_pending_metadata_cache_key", "") or "") == cache_key
    ):
        # render_traits_predictions already performed the persistent-cache read.
        # Expansion and header clicks must not repeat the same SQLite/index
        # queries before deciding whether a calculation is necessary.
        return cached_pending
    cached_metadata = trait_metadata_for_chart(
        owner,
        chart,
        cached_only=True,
        traits=traits,
        trait_signature=signatures.get("trait_signature"),
        legacy_trait_signature=signatures.get("legacy_trait_signature"),
        norm_signature=signatures.get("norm_signature"),
        chart_signature=signatures.get("chart_signature"),
    )
    if isinstance(cached_metadata, dict):
        owner._traits_prediction_pending_metadata = cached_metadata
        owner._traits_prediction_pending_metadata_cache_key = cache_key
        return cached_metadata
    return None


def _traits_pending_cache_is_up_to_date(owner: Any) -> bool:
    cached_metadata = _traits_pending_cached_metadata(owner)
    return isinstance(cached_metadata, dict) and not bool(cached_metadata.get("stale"))


def start_traits_prediction_calculation(owner: Any, *, user_initiated: bool = False) -> None:
    """Start Traits prediction calculation unless the current chart cache is fresh."""
    if _traits_pending_cache_is_up_to_date(owner):
        if user_initiated:
            parent = owner if isinstance(owner, QWidget) else None
            QMessageBox.information(
                parent,
                "Traits",
                "Traits up to date! No recalculation necessary.",
            )
        return
    _start_traits_prediction_calculation(owner)


def sync_traits_prediction_section_expansion(owner: Any, expanded: bool) -> None:
    """Apply Chart Editor Predictions-specific Traits expansion/calculation rules."""
    expanded_by_key = getattr(owner, "_chart_analysis_section_expanded", None)
    if isinstance(expanded_by_key, dict):
        expanded_by_key["traits"] = expanded
    if not expanded:
        return
    if _traits_pending_cached_metadata(owner) is None:
        QTimer.singleShot(0, lambda owner=owner: start_traits_prediction_calculation(owner))


def _set_traits_prediction_section_expanded(owner: Any, expanded: bool) -> None:
    controller = getattr(owner, "_chart_analysis_sections_controller", None)
    set_checked = getattr(controller, "set_section_checked", None)
    if callable(set_checked):
        set_checked("traits", expanded)
        return
    expanded_by_key = getattr(owner, "_chart_analysis_section_expanded", None)
    if isinstance(expanded_by_key, dict):
        expanded_by_key["traits"] = expanded


def _traits_prediction_section_expanded(owner: Any) -> bool:
    expanded_by_key = getattr(owner, "_chart_analysis_section_expanded", None)
    if isinstance(expanded_by_key, dict):
        return bool(expanded_by_key.get("traits", False))
    return False


def _start_traits_prediction_calculation(owner: Any) -> None:
    chart = getattr(owner, "_traits_prediction_pending_chart", None)
    traits = getattr(owner, "_traits_prediction_pending_traits", None)
    cache_key = str(getattr(owner, "_traits_prediction_pending_cache_key", "") or "")
    signatures = getattr(owner, "_traits_prediction_pending_signatures", None)
    if chart is None or not isinstance(traits, list) or not traits:
        return
    active_jobs = getattr(owner, "_traits_prediction_worker_jobs", None)
    if (
        isinstance(active_jobs, list)
        and active_jobs
        and str(getattr(owner, "_traits_prediction_active_cache_key", "") or "") == cache_key
    ):
        _predictions_debug(owner, "Trait refresh already active for cache_key=%s; coalescing request", cache_key[:12])
        return
    owner._traits_prediction_render_token = object()
    token = owner._traits_prediction_render_token
    message = "Loading trait predictions."
    _apply_traits_prediction_view(owner, message, message)
    label = getattr(owner, "traits_prediction_label", None)
    if isinstance(label, QLabel):
        label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        start_prediction_loading_ellipsis(label, "Loading trait predictions")
    _start_traits_prediction_refresh_worker(
        owner,
        chart,
        traits,
        cache_key,
        token,
        signatures if isinstance(signatures, dict) else None,
    )

def _current_traits_prediction_html(owner: Any) -> str:
    combo = getattr(owner, "traits_prediction_mode_combo", None)
    mode = combo.currentData() if isinstance(combo, QComboBox) else "above"
    return getattr(
        owner,
        "_traits_prediction_below_avg_html" if mode == "below" else "_traits_prediction_above_avg_html",
        "",
    )


def _set_traits_prediction_label_for_mode(owner: Any) -> None:
    _refresh_traits_prediction_filter(owner)
    label = getattr(owner, "traits_prediction_label", None)
    if isinstance(label, QLabel):
        label.adjustSize()
        label.setMinimumHeight(label.sizeHint().height())


def _trait_prediction_rows_from_metadata(
    traits: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    likelihoods = dict(metadata.get("likelihoods", {}))
    database_averages = dict(metadata.get("database_averages", {}))
    db_deviations = dict(metadata.get("deviations", {}))
    color_by_name = {
        str(trait.get("name", "")): normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR)))
        for trait in traits
    }
    rows: list[dict[str, Any]] = []
    for name, db_deviation in db_deviations.items():
        if name not in likelihoods or name not in database_averages:
            continue
        deviation = float(db_deviation)
        if abs(deviation) < TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD:
            continue
        rows.append(
            {
                "name": str(name),
                "likelihood": float(likelihoods[name]),
                "database_average": float(database_averages[name]),
                "deviation": deviation,
                "color": color_by_name.get(str(name), DEFAULT_TRAIT_COLOR),
            }
        )
    return rows


def _set_traits_prediction_rows(owner: Any, rows: list[dict[str, Any]]) -> None:
    model = getattr(owner, "_traits_prediction_rows_model", None)
    if isinstance(model, _TraitPredictionRowsModel):
        model.set_rows(rows)
    table = getattr(owner, "traits_prediction_table", None)
    if isinstance(table, QTableView):
        table.setVisible(bool(rows))
        _resize_traits_prediction_table_to_contents(table)
    _refresh_traits_prediction_filter(owner)


def _trait_predictions_html_from_metadata(
    traits: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> tuple[str, str]:
    likelihoods = dict(metadata.get("likelihoods", {}))
    database_averages = dict(metadata.get("database_averages", {}))
    db_deviations = dict(metadata.get("deviations", {}))
    if not likelihoods:
        message = "No scorable traits uploaded."
        return message, message
    if not database_averages:
        message = "Trait predictions unavailable until database trait averages can be calculated."
        return message, message
    color_by_name = {
        str(trait.get("name", "")): normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR)))
        for trait in traits
    }
    threshold = TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD
    above_avg_traits = sorted(
        (
            (name, float(likelihoods[name]), float(database_averages[name]), float(db_deviation))
            for name, db_deviation in db_deviations.items()
            if db_deviation >= threshold
        ),
        key=lambda item: item[3],
        reverse=True,
    )
    below_avg_traits = sorted(
        (
            (name, float(likelihoods[name]), float(database_averages[name]), float(db_deviation))
            for name, db_deviation in db_deviations.items()
            if db_deviation <= -threshold
        ),
        key=lambda item: item[3],
    )
    return (
        _trait_table("Above avg traits", above_avg_traits, color_by_name) + _trait_failure_footnote(metadata),
        _trait_table("Below avg traits", below_avg_traits, color_by_name) + _trait_failure_footnote(metadata),
    )


def _trait_failure_footnote(metadata: dict[str, Any]) -> str:
    """Return a quiet user-facing footnote while keeping diagnostics out of the caption."""
    names = [str(name) for name in metadata.get("unavailable_traits", []) if str(name)]
    if not names:
        return ""
    return (
        '<br><span style="color:#d9534f; font-style:italic;">'
        f"The following traits failed to load: {html.escape(', '.join(names))}. "
        '<a href="trait-predictions:failures">🛈</a></span>'
    )


class _TraitPredictionsRefreshWorker(QObject):
    """Calculate trait prediction metadata away from the Qt GUI thread."""

    finished = Signal(object, object)
    failed = Signal(object, str)

    def __init__(
        self,
        owner: Any,
        chart: Any,
        traits: list[dict[str, Any]],
        token: object,
        signatures: dict[str, str] | None = None,
    ) -> None:
        super().__init__()
        self._owner = owner
        self._chart = chart
        self._traits = traits
        self._token = token
        self._signatures = signatures or {}
        self._cancelled = False

    @Slot()
    def cancel(self) -> None:
        self._cancelled = True

    def _is_cancelled(self) -> bool:
        return self._cancelled or QThread.currentThread().isInterruptionRequested()

    @Slot()
    def run(self) -> None:
        try:
            _predictions_debug(self._owner, "Trait refresh worker start token=%s", id(self._token))
            if self._is_cancelled():
                _predictions_debug(self._owner, "Trait refresh worker cancelled before metadata token=%s", id(self._token))
                self.failed.emit(self._token, "cancelled")
                return
            metadata = trait_metadata_for_chart(
                self._owner,
                self._chart,
                traits=self._traits,
                trait_signature=self._signatures.get("trait_signature"),
                legacy_trait_signature=self._signatures.get("legacy_trait_signature"),
                norm_signature=self._signatures.get("norm_signature"),
                chart_signature=self._signatures.get("chart_signature"),
            )
            if self._is_cancelled():
                _predictions_debug(self._owner, "Trait refresh worker cancelled after metadata token=%s", id(self._token))
                self.failed.emit(self._token, "cancelled")
                return
        except Exception as exc:
            logger.warning("Traits panel background refresh failed: %s", exc, exc_info=True)
            self.failed.emit(self._token, str(exc))
            return
        _predictions_debug(self._owner, "Trait refresh worker finished token=%s", id(self._token))
        self.finished.emit(self._token, metadata)


class _TraitPredictionsRefreshReceiver(QObject):
    """Receive worker results on the GUI thread before touching widgets."""

    def __init__(self, owner: Any, cache_key: str, token: object, traits: list[dict[str, Any]]) -> None:
        parent = owner if isinstance(owner, QWidget) else None
        super().__init__(parent)
        self._owner = owner
        self._cache_key = cache_key
        self._token = token
        self._traits = traits
        self._thread: QThread | None = None
        self._worker: QObject | None = None

    def set_job(self, thread: QThread, worker: QObject) -> None:
        self._thread = thread
        self._worker = worker

    @Slot(object, object)
    def handle_finished(self, finished_token: object, metadata: object) -> None:
        if finished_token is not self._token:
            return
        if getattr(self._owner, "_traits_prediction_render_token", None) is not finished_token:
            return
        resolved_metadata = metadata if isinstance(metadata, dict) else {}
        self._owner._traits_prediction_pending_metadata = resolved_metadata
        self._owner._traits_prediction_pending_metadata_cache_key = self._cache_key
        _apply_traits_prediction_metadata(self._owner, self._traits, resolved_metadata)

    @Slot(object, str)
    def handle_failed(self, finished_token: object, error_message: str) -> None:
        if finished_token is not self._token:
            return
        if getattr(self._owner, "_traits_prediction_render_token", None) is not finished_token:
            return
        message = f"Trait predictions unavailable: {html.escape(error_message)}"
        _apply_traits_prediction_view(self._owner, message, message)

    @Slot()
    def cleanup(self) -> None:
        if self._thread is not None and self._worker is not None:
            _forget_traits_prediction_worker_job(self._owner, self._thread, self._worker, self)
        self.deleteLater()


def _apply_traits_prediction_view(owner: Any, above_html: str, below_html: str, *, prefix_html: str = "") -> None:
    owner._traits_prediction_above_avg_html = f"{prefix_html}{above_html}"
    owner._traits_prediction_below_avg_html = f"{prefix_html}{below_html}"
    _set_traits_prediction_rows(owner, [])
    label = getattr(owner, "traits_prediction_label", None)
    if isinstance(label, QLabel):
        stop_prediction_loading_blink(label)
        stop_prediction_loading_ellipsis(label)
        current_html = _current_traits_prediction_html(owner)
        if current_html:
            label.setText(current_html)
            label.setVisible(True)
        else:
            # Empty content is a valid actionable no-cache/manual state now that
            # calculation lives in the section header button. Do not substitute
            # the old unavailable fallback for a calculable chart.
            label.setText("")
            label.setVisible(False)
        label.adjustSize()
        label.setMinimumHeight(label.sizeHint().height())


def _apply_traits_prediction_metadata(
    owner: Any,
    traits: list[dict[str, Any]],
    metadata: dict[str, Any],
    *,
    prefix_html: str = "",
) -> None:
    _set_traits_updated_label(owner, str(metadata.get("updated_at", "") or ""))
    rows = _trait_prediction_rows_from_metadata(traits, metadata)
    table = getattr(owner, "traits_prediction_table", None)
    has_table = isinstance(table, QTableView)
    if has_table:
        owner._traits_prediction_above_avg_html = prefix_html
        owner._traits_prediction_below_avg_html = prefix_html
    else:
        above_html, below_html = _trait_predictions_html_from_metadata(traits, metadata)
        owner._traits_prediction_above_avg_html = f"{prefix_html}{above_html}"
        owner._traits_prediction_below_avg_html = f"{prefix_html}{below_html}"
    _set_traits_prediction_rows(owner, rows)
    label = getattr(owner, "traits_prediction_label", None)
    if isinstance(label, QLabel):
        failure_detail = str(metadata.get("unavailable_trait_reason", "") or "")
        owner._traits_prediction_failure_detail = failure_detail
        label.setToolTip(failure_detail)
        stop_prediction_loading_blink(label)
        stop_prediction_loading_ellipsis(label)
        if not has_table:
            label.setText(_current_traits_prediction_html(owner) or "Trait predictions unavailable for this chart.")
            label.setVisible(True)
        elif prefix_html or failure_detail:
            label.setText(f"{prefix_html}{_trait_failure_footnote(metadata)}")
            label.setVisible(True)
        elif not rows:
            label.setText("No traits meet the 5% deviation threshold.")
            label.setVisible(True)
        else:
            label.setText("")
            label.setVisible(False)
        label.adjustSize()
        label.setMinimumHeight(label.sizeHint().height())


def _forget_traits_prediction_worker_job(
    owner: Any,
    thread: QThread,
    worker: QObject,
    receiver: QObject,
) -> None:
    jobs = getattr(owner, "_traits_prediction_worker_jobs", None)
    if isinstance(jobs, list):
        try:
            jobs.remove((thread, worker, receiver))
        except ValueError:
            pass
        if not jobs:
            setattr(owner, "_traits_prediction_active_cache_key", "")
    thread.deleteLater()


def _cancel_traits_prediction_worker_jobs(owner: Any, *, wait_msecs: int | None = None) -> None:
    """Request cancellation for active Traits workers without starting duplicate jobs."""
    jobs = getattr(owner, "_traits_prediction_worker_jobs", None)
    if not isinstance(jobs, list) or not jobs:
        return
    for thread, worker, _receiver in list(jobs):
        if hasattr(worker, "cancel"):
            try:
                worker.cancel()
            except RuntimeError:
                pass
        if not isinstance(thread, QThread):
            continue
        try:
            if thread.isRunning():
                thread.requestInterruption()
                thread.quit()
                if wait_msecs is not None:
                    thread.wait(max(0, int(wait_msecs)))
        except RuntimeError:
            continue


def stop_traits_prediction_refresh_workers(owner: Any, wait_msecs: int | None = None) -> None:
    """Stop Chart View trait prediction refresh threads before their owner is destroyed."""
    owner._traits_prediction_render_token = object()
    _cancel_traits_prediction_worker_jobs(owner, wait_msecs=wait_msecs)
    jobs = getattr(owner, "_traits_prediction_worker_jobs", None)
    if not isinstance(jobs, list) or not jobs:
        return

    for thread, _worker, _receiver in list(jobs):
        if not isinstance(thread, QThread):
            continue
        try:
            if thread.isRunning():
                if wait_msecs is None:
                    thread.wait()
                else:
                    thread.wait(max(0, int(wait_msecs)))
        except RuntimeError:
            continue
    jobs.clear()


def _start_traits_prediction_refresh_worker(
    owner: Any,
    chart: Any,
    traits: list[dict[str, Any]],
    cache_key: str,
    token: object,
    signatures: dict[str, str] | None = None,
) -> None:
    label = getattr(owner, "traits_prediction_label", None)
    if not isinstance(label, QLabel):
        return

    _predictions_debug(owner, "Trait refresh worker scheduling token=%s cache_key=%s", id(token), cache_key[:12])
    _cancel_traits_prediction_worker_jobs(owner, wait_msecs=0)
    owner._traits_prediction_active_cache_key = cache_key
    thread_parent = owner if isinstance(owner, QWidget) else None
    thread = QThread(thread_parent)
    worker = _TraitPredictionsRefreshWorker(owner, chart, traits, token, signatures)
    receiver = _TraitPredictionsRefreshReceiver(owner, cache_key, token, traits)
    receiver.set_job(thread, worker)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.finished.connect(receiver.handle_finished, Qt.QueuedConnection)
    worker.failed.connect(receiver.handle_failed, Qt.QueuedConnection)
    worker.finished.connect(worker.deleteLater)
    worker.failed.connect(worker.deleteLater)
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.finished.connect(receiver.cleanup, Qt.QueuedConnection)

    jobs = getattr(owner, "_traits_prediction_worker_jobs", None)
    if not isinstance(jobs, list):
        jobs = []
        owner._traits_prediction_worker_jobs = jobs
    jobs.append((thread, worker, receiver))
    thread.start()


def render_traits_predictions(owner: Any, chart: Any | None) -> None:
    """Render uploaded custom trait scores into Chart View's Predictions panel without showing stale chart data."""
    _predictions_debug(owner, "Trait render requested chart=%s", getattr(chart, "name", getattr(chart, "chart_uid", "none")))
    label = getattr(owner, "traits_prediction_label", None)
    if not isinstance(label, QLabel):
        return
    _configure_traits_prediction_label(owner, label)
    # A render may exit before cache metadata is available (no traits,
    # placeholder chart, cache miss, or calculation failure). Never let the
    # previously viewed chart's timestamp survive any of those paths.
    _set_traits_updated_label(owner, None)
    owner._traits_prediction_chart = chart
    owner._traits_prediction_render_token = object()
    owner._traits_prediction_pending_metadata = None
    owner._traits_prediction_pending_metadata_cache_key = ""
    traits = list_traits(active_only=True)
    owner._traits_prediction_trait_lookup = {
        str(trait.get("name", "")).strip().casefold(): trait
        for trait in traits
        if str(trait.get("name", "")).strip()
    }
    if not traits:
        message = (
            "No active traits. Reactivate traits in Settings > Traits to include them in Predictions."
            if list_traits()
            else "Traits are unavailable. Check Settings > Traits before using Predictions."
        )
        _apply_traits_prediction_view(owner, message, message)
        return
    if chart is None or owner._is_placeholder_chart(chart):
        _apply_traits_prediction_view(
            owner,
            "Trait predictions unavailable for this chart.",
            "Trait predictions unavailable for this chart.",
        )
        return

    signatures = _trait_render_signatures(owner, chart, traits)
    cache_key = _trait_predictions_cache_key(
        owner,
        chart,
        traits,
        trait_signature=signatures.get("trait_signature"),
        trait_display_signature=signatures.get("trait_display_signature"),
        norm_signature=signatures.get("norm_signature"),
        chart_signature=signatures.get("chart_signature"),
    )
    # Keep the cached-only phase explicit: trait_metadata_for_chart(owner, chart, cached_only=True)
    cached_metadata = trait_metadata_for_chart(
        owner,
        chart,
        cached_only=True,
        traits=traits,
        trait_signature=signatures.get("trait_signature"),
        legacy_trait_signature=signatures.get("legacy_trait_signature"),
        norm_signature=signatures.get("norm_signature"),
        chart_signature=signatures.get("chart_signature"),
    )
    if isinstance(cached_metadata, dict):
        owner._traits_prediction_pending_chart = chart
        owner._traits_prediction_pending_traits = traits
        owner._traits_prediction_pending_cache_key = cache_key or ""
        owner._traits_prediction_pending_signatures = signatures
        owner._traits_prediction_pending_metadata = cached_metadata
        owner._traits_prediction_pending_metadata_cache_key = cache_key or ""
        _set_traits_prediction_section_expanded(owner, True)
        if bool(cached_metadata.get("stale")):
            _set_traits_header_action(owner, "recalculate")
            if _predictions_manual_recalculation_only(owner):
                _apply_traits_prediction_metadata(
                    owner,
                    traits,
                    cached_metadata,
                    prefix_html=_traits_stale_recalculate_prompt_html(str(cached_metadata.get("updated_at", "") or "unknown")),
                )
            else:
                _apply_traits_prediction_metadata(
                    owner,
                    traits,
                    cached_metadata,
                    prefix_html=_trait_predictions_refresh_message(str(cached_metadata.get("updated_at", "") or "unknown")),
                )
                QTimer.singleShot(0, lambda owner=owner: _start_traits_prediction_calculation(owner))
        else:
            _set_traits_header_action(owner, "up_to_date")
            _apply_traits_prediction_metadata(owner, traits, cached_metadata)
        return

    was_expanded = _traits_prediction_section_expanded(owner)
    owner._traits_prediction_pending_chart = chart
    owner._traits_prediction_pending_traits = traits
    owner._traits_prediction_pending_cache_key = cache_key or ""
    owner._traits_prediction_pending_signatures = signatures
    if not was_expanded:
        _set_traits_prediction_section_expanded(owner, False)
    _set_traits_header_action(owner, "calculate")
    if _predictions_manual_recalculation_only(owner):
        _predictions_debug(owner, "Trait render found no persisted trait metadata; waiting for expansion/header calculate cache_key=%s", (cache_key or "")[:12])
        prompt_html = _traits_calculate_prompt_html()
        _apply_traits_prediction_view(owner, prompt_html, prompt_html)
        if was_expanded or _traits_prediction_section_expanded(owner):
            QTimer.singleShot(0, lambda owner=owner: start_traits_prediction_calculation(owner))
    else:
        message = "● Loading fresh trait predictions for this UID… ●"
        _predictions_debug(owner, "Trait render found no persisted trait metadata; auto-loading fresh traits cache_key=%s", (cache_key or "")[:12])
        _apply_traits_prediction_view(owner, message, message)
        start_prediction_loading_blink(label)
        QTimer.singleShot(0, lambda owner=owner: _start_traits_prediction_calculation(owner))
    return
