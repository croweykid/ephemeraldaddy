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

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QSortFilterProxyModel, QThread, Qt, Signal, Slot
try:
    from PySide6.QtGui import QColor
except Exception:  # pragma: no cover - headless test environments may omit QtGui libs
    QColor = None  # type: ignore[assignment]
try:
    from PySide6.QtWidgets import QLabel, QComboBox, QHeaderView, QStyledItemDelegate, QTableView, QWidget
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
from ephemeraldaddy.core import db
from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.gui.features.charts.database_norms_cache import (
    DATABASE_NORMS_CACHE_FILENAME,
    DATABASE_NORMS_STALE_RATIO,
    analytical_mapping_signature,
    database_norms_refresh_threshold,
)
try:
    from ephemeraldaddy.gui.style import apply_chart_info_link_cursor, set_chart_info_html
except Exception:  # pragma: no cover - headless tests may not import Qt-backed style module
    def apply_chart_info_link_cursor(_widget: Any) -> None:
        return None

    def set_chart_info_html(widget: Any, content: str) -> None:
        if hasattr(widget, "setHtml"):
            widget.setHtml(content)
        elif hasattr(widget, "setPlainText"):
            widget.setPlainText(content)


logger = logging.getLogger(__name__)

TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD = 5.0


TRAIT_ROW_NAME_ROLE = Qt.UserRole + 1
TRAIT_ROW_COLOR_ROLE = Qt.UserRole + 2
TRAIT_ROW_DEVIATION_ROLE = Qt.UserRole + 3
TRAIT_ROW_DIRECTION_ROLE = Qt.UserRole + 4


class _TraitPredictionRowsModel(QAbstractTableModel):
    """Qt row model for Chart View trait predictions."""

    _HEADERS = ("Trait", "%", "DB avg", "vs DB")

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
                return f"{float(row.get('database_average', 0.0)):.1f}%"
            if column == 3:
                return _format_signed_percentage(float(row.get("deviation", 0.0)))
        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter if column == 0 else Qt.AlignRight | Qt.AlignVCenter
        if role == Qt.ForegroundRole and QColor is not None:
            if column == 0:
                return QColor(str(row.get("color") or DEFAULT_TRAIT_COLOR))
            return QColor("#f5f5f5")
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
        if QColor is not None and isinstance(color, QColor):
            option.palette.setColor(option.palette.Text, color)


def configure_traits_prediction_table(owner: Any, table: QTableView) -> None:
    model = _TraitPredictionRowsModel(table)
    proxy = _TraitPredictionFilterModel(owner, table)
    proxy.setSourceModel(model)
    table.setModel(proxy)
    table.setItemDelegate(_TraitPredictionColorDelegate(table))
    table.setSortingEnabled(True)
    table.sortByColumn(3, Qt.DescendingOrder)
    table.setSelectionBehavior(QTableView.SelectRows)
    table.setSelectionMode(QTableView.SingleSelection)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(False)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    for column in (1, 2, 3):
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
        proxy.sort(3, Qt.AscendingOrder if mode == "below" else Qt.DescendingOrder)
    table = getattr(owner, "traits_prediction_table", None)
    if isinstance(table, QTableView):
        table.resizeRowsToContents()

TRAIT_DB_NORMS_CACHE_VERSION = 1
TRAIT_DB_NORMS_CACHE_PATH = db.DB_DIR / DATABASE_NORMS_CACHE_FILENAME
TRAIT_DB_NORMS_MAX_STALE_RATIO = DATABASE_NORMS_STALE_RATIO
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


def _format_signed_percentage(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.1f}%"


def _traits_table_header() -> str:
    return (
        "<tr>"
        "<th style='padding:1px 8px 2px 0; text-align:left; color:#f5f5f5;'>trait</th>"
        "<th style='padding:1px 8px 2px 0; text-align:right; color:#f5f5f5;'>%</th>"
        "<th style='padding:1px 0 2px 0; text-align:right; color:#f5f5f5;'>vs DB avg</th>"
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
    difference_color = "#d8d8d8"
    if db_deviation > 0:
        difference_color = "#90ee90"
    elif db_deviation < 0:
        difference_color = "#ffb3b3"
    safe_title = html.escape(f"DB average: {max(0.0, min(100.0, db_average)):.1f}%")
    return (
        "<tr>"
        f"<td style='padding:1px 8px 1px 0; white-space:nowrap; color:{safe_color};' title='{safe_title}'>"
        f"<a href='{safe_href}' style='color:{safe_color}; text-decoration:none;'>{safe_name}</a>"
        "</td>"
        f"<td style='padding:1px 8px 1px 0; text-align:right; color:#d8d8d8;'>{pct:.1f}%</td>"
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


def _trait_info_html(trait: dict[str, Any]) -> str:
    name = str(trait.get("name", "")).strip() or "Trait"
    color = normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR)))
    description = str(trait.get("description", "")).strip() or "no description provided"
    sample_count = _trait_sample_count(trait)
    return (
        f"<div style='font-size:18px; font-weight:700; color:{html.escape(color)};'>"
        f"{html.escape(name)}</div>"
        "<div style='height:6px;'></div>"
        "<div style='font-size:12px; color:#f5f5f5; font-style:italic; line-height:1.35;'>"
        f"{html.escape(description).replace(chr(10), '<br>')}"
        "</div>"
        "<div style='height:8px;'></div>"
        "<div style='font-size:9px; color:#b8b8b8; font-variant:small-caps; letter-spacing:0.8px;'>"
        f"based on aggregated data from {sample_count}"
        "</div>"
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
        set_chart_info_html(output, _trait_info_html(trait))


def _on_trait_prediction_link_activated(owner: Any, target: str) -> None:
    if str(target or "") == "trait-predictions:calculate":
        _start_traits_prediction_calculation(owner)
        return
    parts = str(target or "").split(":", 1)
    if len(parts) != 2 or parts[0] != "trait":
        return
    _show_trait_chart_info(owner, urllib.parse.unquote(parts[1]))


def _configure_traits_prediction_label(owner: Any, label: QLabel) -> None:
    label.setOpenExternalLinks(False)
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


def _database_chart_ids(owner: Any) -> tuple[int, ...]:
    def _build() -> tuple[int, ...]:
        chart_rows = _database_chart_rows(owner)
        normalize_row = getattr(owner, "_normalize_chart_row", None)
        chart_ids: set[int] = set()
        for row in chart_rows:
            normalized = normalize_row(row) if callable(normalize_row) else row
            if normalized is None:
                continue
            try:
                chart_ids.add(int(normalized[0]))
            except (TypeError, ValueError, IndexError):
                continue
        return tuple(sorted(chart_ids))

    return _owner_memoized(owner, "_traits_prediction_database_chart_ids_cache", _build)


def _database_chart_uids(owner: Any) -> tuple[str, ...]:
    def _build() -> tuple[str, ...]:
        chart_rows = _database_chart_rows(owner)
        chart_uids: set[str] = set()
        missing_uid_ids: set[int] = set()
        for row in chart_rows:
            try:
                chart_id = int(row[0])
            except (TypeError, ValueError, IndexError):
                continue
            raw_uid = None
            try:
                if len(row) > 30:
                    raw_uid = row[30]
            except TypeError:
                raw_uid = None
            chart_uid = str(raw_uid or "").strip().upper()
            if chart_uid:
                chart_uids.add(chart_uid)
            else:
                missing_uid_ids.add(chart_id)
        if missing_uid_ids:
            try:
                chart_uids.update(
                    str(uid).strip().upper()
                    for uid in db.get_chart_uid_map(missing_uid_ids).values()
                    if str(uid or "").strip()
                )
            except Exception as exc:
                logger.warning("Traits panel could not resolve chart UIDs for norm signature: %s", exc, exc_info=True)
        return tuple(sorted(chart_uids))

    return _owner_memoized(owner, "_traits_prediction_database_chart_uids_cache", _build)


def _chart_uid_for_trait_metadata(chart: Any) -> str | None:
    chart_uid = str(getattr(chart, "chart_uid", "") or "").strip()
    return chart_uid or None


def _debug_chart_uid(chart: Any) -> str:
    chart_uid = _chart_uid_for_trait_metadata(chart)
    return chart_uid or "unavailable"


def _database_chart_uid_and_id_for_chart(owner: Any, chart: Any) -> tuple[str, int | None] | None:
    """Resolve a chart object back to its persisted Database View UID and row id."""
    chart_uid = str(getattr(chart, "chart_uid", "") or "").strip().upper()
    explicit_id = getattr(chart, "chart_id", None) or getattr(chart, "id", None)
    if chart_uid:
        try:
            return chart_uid, int(explicit_id) if explicit_id is not None else db.get_chart_id_by_uid(chart_uid)
        except (TypeError, ValueError):
            return chart_uid, db.get_chart_id_by_uid(chart_uid)
        except Exception:
            return chart_uid, None
    try:
        persisted_id = int(explicit_id) if explicit_id is not None else None
    except (TypeError, ValueError):
        persisted_id = None
    if persisted_id is None:
        return None
    try:
        chart_uid = str(db.get_chart_uid(persisted_id) or "").strip().upper()
    except Exception:
        chart_uid = ""
    if chart_uid:
        return chart_uid, persisted_id
    normalize_row = getattr(owner, "_normalize_chart_row", None)
    for row in _database_chart_rows(owner):
        normalized = normalize_row(row) if callable(normalize_row) else row
        if normalized is None:
            continue
        try:
            chart_id = int(normalized[0])
        except (TypeError, ValueError, IndexError):
            continue
        row_uid = ""
        if isinstance(normalized, (list, tuple)) and len(normalized) > 30:
            row_uid = str(normalized[30] or "").strip().upper()
        if chart_id == persisted_id and row_uid:
            return row_uid, persisted_id
    return None


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

    Database Analytics, Chart View Traits, and D&D alignment traits all use this
    wrapper so persisted database charts are scored once per analytical profile.
    Draft/unsaved charts still fall back to direct scoring because they do not
    have stable database row tokens for the persisted cache.
    """
    if chart is None or not traits:
        return {}
    collect = getattr(owner, "_collect_traits_distribution_analytics", None)
    signature_builder = getattr(owner, "_traits_distribution_signature", None)
    chart_identity = _database_chart_uid_and_id_for_chart(owner, chart)
    chart_uid = chart_identity[0] if chart_identity is not None else ""
    chart_id = chart_identity[1] if chart_identity is not None else None
    if (
        not callable(collect)
        or not callable(signature_builder)
        or chart_id is None
        or not chart_uid
        or not _persisted_chart_signature_matches_current(chart_uid, chart)
    ):
        return calculate_trait_likelihoods(chart, traits)
    try:
        signature = signature_builder(traits)
        analytics = collect(
            [chart_id],
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
    try:
        uses_houses = bool(chart_uses_houses(chart))
    except Exception:
        uses_houses = bool(getattr(chart, "use_birth_time_data", False))
    scoring_payload = {
        "positions": getattr(chart, "positions", None),
        "aspects": getattr(chart, "aspects", None),
        "human_design_gates": getattr(chart, "human_design_gates", None),
        "human_design_channels": getattr(chart, "human_design_channels", None),
        "human_design_type": getattr(chart, "human_design_type", None),
        "human_design_profile": getattr(chart, "human_design_profile", None),
        "human_design_defined_centers": getattr(chart, "human_design_defined_centers", None),
        "human_design_authority": getattr(chart, "human_design_authority", None),
        "bazi_year_pillar": getattr(chart, "bazi_year_pillar", None),
        "bazi_month_pillar": getattr(chart, "bazi_month_pillar", None),
        "bazi_day_pillar": getattr(chart, "bazi_day_pillar", None),
        "bazi_hour_pillar": getattr(chart, "bazi_hour_pillar", None),
        "bazi_sign_weights": getattr(chart, "bazi_sign_weights", None),
        "bazi_branch_weights": getattr(chart, "bazi_branch_weights", None),
        "dominant_bazi_sign_weights": getattr(chart, "dominant_bazi_sign_weights", None),
    }
    if uses_houses:
        scoring_payload["houses"] = getattr(chart, "houses", None)
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
            "scoring_payload": scoring_payload,
        }
    )


def _database_norm_refresh_threshold(chart_count: int) -> int:
    """Return how many birth-data cohort changes justify refreshing DB norms."""
    return database_norms_refresh_threshold(chart_count)


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

    normalized_rows_by_id: dict[int, Any] = {}
    for row in rows:
        normalized = normalize_row(row) if callable(normalize_row) else row
        if normalized is None:
            continue
        try:
            chart_id = int(normalized[0])
        except Exception:
            continue
        normalized_rows_by_id[chart_id] = normalized

    tokens: list[tuple[str, str]] = []
    uid_map: dict[int, str] = {}
    missing_uid_ids: list[int] = []
    for chart_id, normalized in normalized_rows_by_id.items():
        uid = ""
        if isinstance(normalized, (list, tuple)) and len(normalized) > 30 and normalized[30]:
            uid = str(normalized[30]).strip().upper()
        if not uid:
            missing_uid_ids.append(chart_id)
            continue
        tokens.append((uid, _stable_json_hash(_database_norm_chart_token_payload(normalized, uid))))

    if missing_uid_ids:
        try:
            uid_map = db.get_chart_uid_map(missing_uid_ids)
        except Exception:
            uid_map = {}
        for chart_id in missing_uid_ids:
            normalized = normalized_rows_by_id.get(chart_id)
            uid = str(uid_map.get(chart_id, "")).strip().upper()
            if not uid:
                continue
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


def _database_norm_state_change_count(saved_state: dict[str, Any], current_state: dict[str, Any]) -> int:
    saved_tokens = saved_state.get("chart_tokens", {}) if isinstance(saved_state, dict) else {}
    current_tokens = current_state.get("chart_tokens", {}) if isinstance(current_state, dict) else {}
    if not isinstance(saved_tokens, dict) or not isinstance(current_tokens, dict):
        return max(
            int(saved_state.get("chart_count", 0) or 0) if isinstance(saved_state, dict) else 0,
            int(current_state.get("chart_count", 0) or 0) if isinstance(current_state, dict) else 0,
        )
    all_uids = set(saved_tokens) | set(current_tokens)
    return sum(1 for uid in all_uids if saved_tokens.get(uid) != current_tokens.get(uid))


def _database_norm_state_is_fresh(saved_state: dict[str, Any], current_state: dict[str, Any]) -> bool:
    saved_count = int(saved_state.get("chart_count", 0) or 0) if isinstance(saved_state, dict) else 0
    current_count = int(current_state.get("chart_count", 0) or 0) if isinstance(current_state, dict) else 0
    threshold = _database_norm_refresh_threshold(max(saved_count, current_count))
    return _database_norm_state_change_count(saved_state, current_state) < threshold


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


def _database_norm_signature_for_traits(
    owner: Any,
    traits: list[dict[str, Any]],
    *,
    current_norm_state: dict[str, Any] | None = None,
    chart_uids: tuple[str, ...] | None = None,
) -> str:
    """Return the active DB norm signature, preserving it until the refresh threshold is crossed."""
    current_norm_state = current_norm_state if current_norm_state is not None else _database_norm_state(owner)
    cache_entries = _load_trait_norm_cache()
    fresh_signatures: set[str] = set()
    stale_signatures: set[str] = set()
    chart_uids = chart_uids if chart_uids is not None else _database_chart_uids(owner)
    for trait in traits:
        cache_key = _trait_norm_cache_key(chart_uids, trait)
        cached = cache_entries.get(cache_key or "")
        cached_state = cached.get("norm_state", {}) if isinstance(cached, dict) else {}
        cached_signature = str(cached.get("norm_signature", "")).strip() if isinstance(cached, dict) else ""
        if not cached_signature:
            continue
        if _database_norm_state_is_fresh(cached_state, current_norm_state):
            fresh_signatures.add(cached_signature)
        else:
            stale_signatures.add(cached_signature)
    if fresh_signatures:
        return sorted(fresh_signatures)[0]
    if stale_signatures:
        _predictions_debug(
            owner,
            "Trait DB norm signature using stale persistent cache while background refresh can update it signatures=%s",
            sorted(stale_signatures),
        )
        return sorted(stale_signatures)[0]
    return _database_norm_signature_from_state(current_norm_state)


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
) -> dict[str, Any]:
    deviations = {
        name: float(pct) - float(database_averages[name])
        for name, pct in likelihoods.items()
        if name in database_averages
    }
    above = {name for name, deviation in deviations.items() if deviation >= TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD}
    below = {name for name, deviation in deviations.items() if deviation <= -TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD}
    stale = bool(stale_chart_vector or stale_trait_definition or stale_db_baseline)
    metadata: dict[str, Any] = {
        "above": above,
        "below": below,
        "deviations": deviations,
        "likelihoods": likelihoods,
        "database_averages": database_averages,
        "stale_chart_vector": bool(stale_chart_vector),
        "stale_trait_definition": bool(stale_trait_definition),
        "stale_db_baseline": bool(stale_db_baseline),
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


def _trait_norm_cache_key(chart_uids: tuple[str, ...], trait: dict[str, Any]) -> str | None:
    name = str(trait.get("name", "")).strip()
    if not name or bool(trait.get("archived", False)):
        return None
    payload = {
        "version": TRAIT_DB_NORMS_CACHE_VERSION,
        "cache_scope": "appwide_database_norms",
        "refresh_policy": "database_statistics_threshold",
        "norm_kind": "trait_database_average",
        "trait_uid": str(trait.get("uid") or trait.get("trait_uid") or "").strip(),
        "analytical_profile": _trait_analytical_profile(trait.get("profile", {})),
    }
    return _stable_json_hash(payload)


def _load_trait_norm_cache() -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(TRAIT_DB_NORMS_CACHE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning(
            "Traits panel skipped corrupt DB norm cache %s: %s",
            TRAIT_DB_NORMS_CACHE_PATH,
            exc,
            exc_info=True,
        )
        return {}
    if not isinstance(payload, dict) or payload.get("version") != TRAIT_DB_NORMS_CACHE_VERSION:
        logger.warning(
            "Traits panel skipped DB norm cache %s because it has an unsupported format or version.",
            TRAIT_DB_NORMS_CACHE_PATH,
        )
        return {}
    entries = payload.get("entries", {})
    if not isinstance(entries, dict):
        logger.warning(
            "Traits panel skipped DB norm cache entries from %s because entries is not a mapping.",
            TRAIT_DB_NORMS_CACHE_PATH,
        )
        return {}
    return entries


def _save_trait_norm_cache(entries: dict[str, dict[str, Any]]) -> None:
    try:
        TRAIT_DB_NORMS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temp_path = TRAIT_DB_NORMS_CACHE_PATH.with_suffix(f"{TRAIT_DB_NORMS_CACHE_PATH.suffix}.tmp")
        temp_path.write_text(
            json.dumps(
                {"version": TRAIT_DB_NORMS_CACHE_VERSION, "entries": entries},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        temp_path.replace(TRAIT_DB_NORMS_CACHE_PATH)
    except Exception:
        return


def clear_trait_norm_cache(trait_names: set[str] | None = None) -> None:
    """Clear persisted DB norm cache entries for selected traits or all traits."""
    if trait_names is None:
        TRAIT_DB_NORMS_CACHE_PATH.unlink(missing_ok=True)
        return
    normalized_names = {name.casefold() for name in trait_names}
    entries = _load_trait_norm_cache()
    for key, entry in list(entries.items()):
        if str(entry.get("trait_name", "")).casefold() in normalized_names:
            entries.pop(key, None)
    _save_trait_norm_cache(entries)


def _calculate_database_trait_averages_direct(
    owner: Any,
    chart_ids: tuple[int, ...],
    traits: list[dict[str, Any]],
) -> dict[str, float]:
    """Calculate DB trait averages without relying on Database Analytics caches."""
    if not chart_ids or not traits:
        return {}
    get_chart = getattr(owner, "_get_chart_for_filter", None)
    is_placeholder = getattr(owner, "_is_placeholder_chart", None)
    chart_count = 0
    totals: dict[str, float] = {str(trait.get("name", "")).strip(): 0.0 for trait in traits}
    totals = {name: total for name, total in totals.items() if name}
    if not totals:
        return {}
    for chart_id in chart_ids:
        try:
            chart = get_chart(int(chart_id)) if callable(get_chart) else db.load_chart(int(chart_id))
        except Exception as exc:
            logger.warning("Traits panel could not load chart %s while calculating DB trait averages: %s", chart_id, exc)
            continue
        if chart is None:
            continue
        if callable(is_placeholder) and is_placeholder(chart):
            continue
        try:
            likelihoods = calculate_trait_likelihoods(chart, traits)
        except Exception as exc:
            logger.warning(
                "Traits panel could not score chart %s while calculating DB trait averages: %s",
                chart_id,
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
) -> dict[str, float]:
    _predictions_debug(owner, "Trait DB averages requested traits=%s", len(traits))
    if not force_refresh_stale:
        snapshot_provider = getattr(owner, "_prediction_norm_snapshot_trait_averages", None)
        if callable(snapshot_provider):
            try:
                snapshot_averages = snapshot_provider(traits)
            except Exception as exc:
                logger.warning("Traits panel could not read shared Predictions norms snapshot: %s", exc, exc_info=True)
                snapshot_averages = {}
            if isinstance(snapshot_averages, dict):
                requested_names = {
                    str(trait.get("name", "") or "").strip()
                    for trait in traits
                    if str(trait.get("name", "") or "").strip()
                }
                if requested_names and requested_names.issubset(set(snapshot_averages)):
                    _predictions_debug(
                        owner,
                        "Trait DB averages served from shared Predictions snapshot traits=%s",
                        len(requested_names),
                    )
                    return {name: float(snapshot_averages[name]) for name in requested_names}
    chart_ids = _database_chart_ids(owner)
    chart_uids = _database_chart_uids(owner)
    current_norm_state = _database_norm_state(owner)
    collect = getattr(owner, "_collect_traits_distribution_analytics", None)
    signature_builder = getattr(owner, "_traits_distribution_signature", None)
    if not chart_ids or not chart_uids:
        return {}
    if not callable(collect) or not callable(signature_builder):
        return _calculate_database_trait_averages_direct(owner, chart_ids, traits)
    averages: dict[str, float] = {}
    cache_entries = _load_trait_norm_cache()
    missing_traits: list[dict[str, Any]] = []
    for trait in traits:
        name = str(trait.get("name", "")).strip()
        cache_key = _trait_norm_cache_key(chart_uids, trait)
        cached = cache_entries.get(cache_key or "")
        cached_state = cached.get("norm_state", {}) if isinstance(cached, dict) else {}
        if isinstance(cached, dict):
            try:
                cached_is_fresh = _database_norm_state_is_fresh(cached_state, current_norm_state)
                if not cached_is_fresh:
                    _predictions_debug(
                        owner,
                        "Trait DB average using stale persistent norm trait=%s cached_chart_count=%s current_chart_count=%s",
                        name,
                        cached.get("chart_count"),
                        current_norm_state.get("chart_count"),
                    )
                    if force_refresh_stale:
                        missing_traits.append(trait)
                        continue
                averages[name] = float(cached["db_average"])
                continue
            except (KeyError, TypeError, ValueError):
                pass
        missing_traits.append(trait)
    if not missing_traits:
        _predictions_debug(owner, "Trait DB averages served entirely from persistent cache traits=%s", len(averages))
        try:
            trait_uids_by_name = {
                str(trait.get("name", "")).strip(): _trait_uid_for_item(trait)
                for trait in traits
                if str(trait.get("name", "")).strip()
            }
            db.upsert_trait_baseline_snapshot(
                norm_signature=_database_norm_signature_from_state(current_norm_state),
                trait_signature=_stable_json_hash(_trait_signature_payload(traits)),
                rows=[
                    {
                        "trait_name": name,
                        "trait_uid": trait_uids_by_name.get(name, ""),
                        "db_average": average,
                    }
                    for name, average in averages.items()
                ],
                chart_count=int(current_norm_state.get("chart_count", 0) or 0),
                norm_state=current_norm_state,
            )
        except Exception as exc:
            logger.warning("Traits panel could not persist DB baseline snapshot: %s", exc, exc_info=True)
        return averages

    try:
        _predictions_debug(owner, "Trait DB averages collecting missing traits=%s chart_ids=%s", len(missing_traits), len(chart_ids))
        analytics = collect(chart_ids, trait_items=missing_traits, trait_signature=signature_builder(missing_traits))
    except Exception as exc:
        logger.warning("Traits panel could not collect Database Analytics trait averages: %s", exc, exc_info=True)
        direct_averages = _calculate_database_trait_averages_direct(owner, chart_ids, missing_traits)
        averages.update(direct_averages)
        return averages
    chart_count = max(0, int(analytics.get("chart_count", 0)))
    if not chart_count:
        direct_averages = _calculate_database_trait_averages_direct(owner, chart_ids, missing_traits)
        averages.update(direct_averages)
        return averages
    totals = analytics.get("totals", {})
    for trait_name in analytics.get("trait_names", []):
        name = str(trait_name)
        db_average = (float(totals.get(name, 0.0)) / float(chart_count)) * 100.0
        averages[name] = db_average
        trait_item = next((trait for trait in missing_traits if str(trait.get("name", "")).strip() == name), None)
        cache_key = _trait_norm_cache_key(chart_uids, trait_item or {})
        if cache_key:
            cache_entries[cache_key] = {
                "trait_name": name,
                "db_average": db_average,
                "chart_count": chart_count,
                "norm_state": current_norm_state,
                "norm_signature": _database_norm_signature_from_state(current_norm_state),
            }
    _save_trait_norm_cache(cache_entries)
    try:
        trait_uids_by_name = {
            str(trait.get("name", "")).strip(): _trait_uid_for_item(trait)
            for trait in traits
            if str(trait.get("name", "")).strip()
        }
        db.upsert_trait_baseline_snapshot(
            norm_signature=_database_norm_signature_from_state(current_norm_state),
            trait_signature=_stable_json_hash(_trait_signature_payload(traits)),
            rows=[
                {
                    "trait_name": name,
                    "trait_uid": trait_uids_by_name.get(name, ""),
                    "db_average": average,
                }
                for name, average in averages.items()
            ],
            chart_count=chart_count,
            norm_state=current_norm_state,
        )
    except Exception as exc:
        logger.warning("Traits panel could not persist DB baseline snapshot: %s", exc, exc_info=True)
    return averages


def warm_trait_database_norms(owner: Any, trait_names: set[str] | None = None) -> dict[str, float]:
    """Precompute and persist DB norms for selected active traits."""
    traits = list_traits(active_only=True)
    if trait_names is not None:
        normalized_names = {name.casefold() for name in trait_names}
        traits = [trait for trait in traits if str(trait.get("name", "")).casefold() in normalized_names]
    return _database_trait_averages(owner, traits, force_refresh_stale=True)


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
    norm_signature = norm_signature or _database_norm_signature_for_traits(owner, traits)
    chart_signature = chart_signature or _chart_trait_metadata_signature(chart)
    signature = (TRAIT_DB_NORMS_CACHE_VERSION, trait_signature, norm_signature, chart_signature)
    cached = getattr(chart, "_trait_prediction_metadata_cache", None)
    if isinstance(cached, dict) and cached.get("signature") == signature:
        _predictions_debug(owner, "Trait metadata memory cache hit chart_uid=%s", _debug_chart_uid(chart))
        return dict(cached.get("metadata", {}))

    chart_uid = _chart_uid_for_trait_metadata(chart)
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
                # If either chart birth data or DB norms changed, the row is stale,
                # but it is still a better cached result than a misleading "no data"
                # placeholder while the explicit recalculation path remains available.
                stale_rows_by_name[name] = row
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
        if cached_only and active_trait_names and set(stale_rows_by_name) == active_trait_names:
            _predictions_debug(owner, "Trait metadata stale DB row cache hit chart_uid=%s traits=%s", chart_uid, len(active_trait_names))
            above = {name for name, row in stale_rows_by_name.items() if row.get("direction") == "above"}
            below = {name for name, row in stale_rows_by_name.items() if row.get("direction") == "below"}
            latest_updated_at = max(
                (str(row.get("updated_at", "") or "") for row in stale_rows_by_name.values()),
                default="",
            )
            return {
                "above": above,
                "below": below,
                "deviations": {name: float(row.get("deviation", 0.0)) for name, row in stale_rows_by_name.items()},
                "likelihoods": {name: float(row.get("likelihood", 0.0)) for name, row in stale_rows_by_name.items()},
                "database_averages": {name: float(row.get("db_average", 0.0)) for name, row in stale_rows_by_name.items()},
                "stale": True,
                "updated_at": latest_updated_at,
            }

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
            norm_signature = _database_norm_signature_for_traits(owner, traits)
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
    timestamp = html.escape(updated_at or "never")
    return (
        "<div style='color:#70d878; font-style:italic; padding-bottom:5px; text-align:center;'>"
        f"Predictions panel is refreshing. Current results last updated: {timestamp} ♻️"
        "</div>"
    )


def _traits_calculate_prompt_html() -> str:
    return (
        "<div style='width:100%; min-height:120px; padding:24px 0; text-align:center;'>"
        "<div style='display:inline-block; max-width:100%; color:#f5f5f5; "
        "font-weight:600; white-space:normal; line-height:1.35; margin-bottom:12px;'>"
        "No prior data. Calculate (can take awhile)?"
        "</div>"
        "<div style='height:10px;'></div>"
        "<a href='trait-predictions:calculate' "
        "style='display:inline-block; background-color:#7b4dff; color:white; "
        "font-weight:bold; padding:7px 16px; border-radius:5px; text-decoration:none;'>"
        "Calculate!</a>"
        "</div>"
    )


def _traits_recalculate_prompt_html(updated_at: str | None) -> str:
    timestamp = html.escape(updated_at or "unknown")
    return (
        "<div style='width:100%; padding:0 0 8px 0; text-align:center; color:#b8b8b8;'>"
        f"<span style='font-style:italic;'>Cached trait predictions shown. Last calculated: {timestamp}.</span> "
        "<a href='trait-predictions:calculate' "
        "style='display:inline-block; margin-left:6px; background-color:#7b4dff; color:white; "
        "font-weight:bold; padding:4px 10px; border-radius:5px; text-decoration:none;'>"
        "Recalculate!</a>"
        "</div>"
    )


def _traits_stale_recalculate_prompt_html(updated_at: str | None) -> str:
    timestamp = html.escape(updated_at or "unknown")
    return (
        "<div style='width:100%; padding:0 0 8px 0; text-align:center; color:#ffdf8a;'>"
        "<span style='font-style:italic;'>Cached trait predictions shown, but the chart's birth data "
        f"has changed since they were calculated ({timestamp}).</span> "
        "<a href='trait-predictions:calculate' "
        "style='display:inline-block; margin-left:6px; background-color:#7b4dff; color:white; "
        "font-weight:bold; padding:4px 10px; border-radius:5px; text-decoration:none;'>"
        "Recalculate!</a>"
        "</div>"
    )


def _trait_render_signatures(owner: Any, chart: Any, traits: list[dict[str, Any]]) -> dict[str, str]:
    """Precompute all signatures used by one Traits render pass exactly once."""
    trait_signature = _stable_json_hash(_trait_signature_payload(traits))
    legacy_trait_signature = _stable_json_hash(_trait_signature_payload(traits, strip_uids=True))
    trait_display_signature = _stable_json_hash(_trait_display_signature_payload(traits))
    current_norm_state = _database_norm_state(owner)
    chart_uids = _database_chart_uids(owner)
    try:
        norm_signature = _database_norm_signature_for_traits(
            owner,
            traits,
            current_norm_state=current_norm_state,
            chart_uids=chart_uids,
        )
    except Exception as exc:
        logger.warning(
            "Traits panel could not build DB norm signature for render pass: %s",
            exc,
            exc_info=True,
        )
        norm_signature = "norm:unavailable"
    return {
        "trait_signature": trait_signature,
        "legacy_trait_signature": legacy_trait_signature,
        "trait_display_signature": trait_display_signature,
        "norm_signature": norm_signature,
        "chart_signature": _chart_trait_metadata_signature(chart),
    }


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
    message = (
        _trait_predictions_refresh_message(None)
        + "<div style='color:#d8d8d8; text-align:center;'>Loading trait predictions for this chart…</div>"
    )
    _apply_traits_prediction_view(owner, message, message)
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
        _trait_table("Above avg traits", above_avg_traits, color_by_name),
        _trait_table("Below avg traits", below_avg_traits, color_by_name),
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
        _apply_traits_prediction_metadata(self._owner, self._traits, metadata if isinstance(metadata, dict) else {})

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
        label.setText(_current_traits_prediction_html(owner) or "Trait predictions unavailable for this chart.")
        label.adjustSize()
        label.setMinimumHeight(label.sizeHint().height())


def _apply_traits_prediction_metadata(
    owner: Any,
    traits: list[dict[str, Any]],
    metadata: dict[str, Any],
    *,
    prefix_html: str = "",
) -> None:
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
        if not has_table:
            label.setText(_current_traits_prediction_html(owner) or "Trait predictions unavailable for this chart.")
            label.setVisible(True)
        elif prefix_html:
            label.setText(prefix_html)
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
    owner._traits_prediction_render_token = object()
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
            else "No traits uploaded. Add traits in Settings > Traits."
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
        if bool(cached_metadata.get("stale")):
            _apply_traits_prediction_metadata(
                owner,
                traits,
                cached_metadata,
                prefix_html=_traits_stale_recalculate_prompt_html(str(cached_metadata.get("updated_at", "") or "unknown")),
            )
        else:
            _apply_traits_prediction_metadata(owner, traits, cached_metadata)
        return

    owner._traits_prediction_pending_chart = chart
    owner._traits_prediction_pending_traits = traits
    owner._traits_prediction_pending_cache_key = cache_key or ""
    owner._traits_prediction_pending_signatures = signatures
    message = _traits_calculate_prompt_html()
    _predictions_debug(owner, "Trait render found no persisted trait metadata; showing manual calculate prompt cache_key=%s", (cache_key or "")[:12])
    _apply_traits_prediction_view(owner, message, message)
    return
