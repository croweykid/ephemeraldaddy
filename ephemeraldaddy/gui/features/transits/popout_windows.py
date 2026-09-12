"""Transit popout windows owned by the canonical Transit workflow package."""

from __future__ import annotations

import copy
import datetime
import logging
import uuid
from typing import Any, Callable, Protocol

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import QDate, QThread, QTime, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDateEdit, QDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QPushButton, QSizePolicy, QTabWidget, QTimeEdit, QWidget,
)

from ephemeraldaddy.core.aspect_display import iter_displayable_aspects
from ephemeraldaddy.core.aspects import ASPECT_DEFS
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.interpretations import ASPECT_SORT_OPTIONS
from ephemeraldaddy.core.interpretations import ANGLE_WEIGHT, NATAL_WEIGHT, TRANSIT_WEIGHT
from ephemeraldaddy.core.composite import (
    PERSONAL_TRANSIT_MODE_DAILY_VIBE, PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
    TRANSIT_ASPECT_RULES, find_transit_aspect_window_result, personal_transit_orb_cap,
    personal_transit_rules_for_mode, split_daily_vibe_hits_by_expected_duration,
)
from ephemeraldaddy.graphics.wheel_plot import draw_chart_wheel
from ephemeraldaddy.gui.features.charts.chart_data_output import ChartDataTableOutput, apply_chart_data_highlighter
from ephemeraldaddy.gui.features.charts.exporters import sanitize_export_token as _sanitize_export_token
from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_planet_weights as _calculate_dominant_planet_weights,
    chart_uses_houses as _chart_uses_houses,
)
from ephemeraldaddy.gui.features.charts.personal_transit_popout import (
    PersonalTransitLocationError, build_personal_transit_header_lines,
    recalculate_personal_transit, resolve_personal_transit_location,
)
from ephemeraldaddy.gui.features.charts.presentation import (
    format_degree_minutes as _format_degree_minutes,
    format_transit_range as _format_transit_range,
)
from ephemeraldaddy.gui.features.charts.text_summary import (
    _aspect_score, _format_popout_aspect_endpoint, _overlay_aspect_segments, format_chart_text,
)
from ephemeraldaddy.gui.features.charts.transit_workers import (
    ManagedTransitPopoutDialog, TransitAspectWindowRelay, TransitAspectWindowWorker,
)
from ephemeraldaddy.gui.features.transits.export import build_transit_chart_export_text
from ephemeraldaddy.gui.features.transits.popout_layout import build_transit_popout_scaffold
from ephemeraldaddy.gui.features.transits.range_worker import (
    PersonalTransitRangeRelay,
    PersonalTransitRangeWorker,
)
from ephemeraldaddy.gui.features.transits.theme_view import (
    format_transit_range_table, theme_entries_grouped_by_time,
)
from ephemeraldaddy.gui.features.retcon.transit_window import (
    resolve_transit_window_scan_config, resolve_transit_window_scan_config_for_transit_body,
)
from ephemeraldaddy.gui.style import (
    CHART_DATA_HIGHLIGHT_COLOR, CHART_DATA_MONOSPACE_FONT_FAMILY,
    CHART_DATA_POPOUT_HEADER_STYLE,
)
from ephemeraldaddy.io.geocode import LocationLookupError, geocode_location

logger = logging.getLogger(__name__)


def _new_debug_action_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class TransitPopoutHost(Protocol):
    """Explicit boundary required by the Transit popout controller."""

    transit_panel_controller: Any
    _popout_summary_contexts: dict[Any, dict[str, object]]

    def _attach_popout_share_button(self, *args: Any, **kwargs: Any) -> Any: ...
    def _build_popout_left_panel(self, *args: Any, **kwargs: Any) -> Any: ...
    def _chart_data_visibility_options(self) -> dict[str, Any]: ...
    def _register_popout_shortcuts(self, dialog: Any) -> None: ...
    def _sort_popout_aspects(self, aspect_hits: list[Any], sort_mode: str) -> list[Any]: ...


class TransitPopoutController:
    """Own Global and Personal Transit popouts behind a declared host boundary."""

    def __init__(self, host: TransitPopoutHost) -> None:
        self._host = host
        self._dialogs: list[QDialog] = []
        self._chart_by_dialog: dict[QDialog, Chart] = {}

    def _set_personal_theme_tabs(
        self,
        tabs: QTabWidget,
        windows: list[Any],
        center: datetime.datetime,
        chart_info_output: QPlainTextEdit,
        display_timezone: datetime.tzinfo | None,
    ) -> None:
        """Render one clickable, chart-data-formatted tab per transit theme."""
        while tabs.count():
            old = tabs.widget(0)
            self._host._popout_summary_contexts.pop(old.viewport(), None)
            tabs.removeTab(0)
            old.deleteLater()
        grouped = theme_entries_grouped_by_time(windows, center)
        if not grouped:
            empty = QPlainTextEdit("No themed major transits occur in this ±30 day window.")
            empty.setReadOnly(True)
            tabs.addTab(empty, "No Themes")
            return
        headings = (("past", "🌖Past"), ("present", "🌕Present"), ("future", "🌒Future"))
        for theme_label, buckets in grouped.items():
            output = ChartDataTableOutput()
            output.setReadOnly(True)
            lines: list[str] = []
            aspect_info_map: dict[int, dict[str, object]] = {}
            header_rows: list[int] = []
            for bucket, heading in headings:
                header_rows.append(len(lines))
                lines.append(heading)
                entries = buckets[bucket]
                if not entries:
                    lines.append("None")
                    lines.append("")
                    continue
                for entry in entries:
                    start = entry.start.astimezone(display_timezone) if display_timezone else entry.start
                    end = entry.end.astimezone(display_timezone) if display_timezone else entry.end
                    line = f"{start:%Y-%m-%d} – {end:%Y-%m-%d}  {entry.aspect_label}  ⓘ"
                    aspect_info_map[len(lines)] = {
                        "p1": entry.transiting_body, "p2": entry.natal_body,
                        "type": entry.aspect_type,
                        "angle": float(ASPECT_DEFS.get(entry.aspect_type.replace(" ", "_").lower(), {}).get("angle", 0.0)),
                        "delta": 0.0,
                    }
                    lines.append(line)
                lines.append("")
            output.setPlainText("\n".join(lines).rstrip())
            apply_chart_data_highlighter(output)
            header_format = QTextCharFormat()
            header_format.setFontWeight(QFont.Bold)
            header_format.setForeground(QColor(CHART_DATA_HIGHLIGHT_COLOR))
            document = output.document()
            for row in header_rows:
                cursor = QTextCursor(document.findBlockByNumber(row))
                cursor.select(QTextCursor.BlockUnderCursor)
                cursor.mergeCharFormat(header_format)
            output.viewport().installEventFilter(self._host)
            self._host._popout_summary_contexts[output.viewport()] = {
                "output_widget": output, "chart_info_output": chart_info_output,
                "position_info_map": {}, "aspect_info_map": aspect_info_map,
                "species_info_map": {}, "summary_block_offset": 0,
            }
            output.viewport().destroyed.connect(
                lambda _=None, key=output.viewport(): self._host._popout_summary_contexts.pop(key, None)
            )
            tabs.addTab(output, theme_label)

    def _set_global_theme_tabs(
        self, tabs: QTabWidget, aspects: list[Any], when: datetime.datetime | None,
        chart_info_output: QPlainTextEdit, display_timezone: datetime.tzinfo | None,
    ) -> None:
        """Render global aspects in the same per-theme, clickable tab contract."""
        from ephemeraldaddy.gui.features.transits.theme_view import themes_for_aspect_bodies

        grouped: dict[str, list[tuple[str, str, str]]] = {}
        for aspect in aspects:
            if isinstance(aspect, dict):
                left = str(aspect.get("p1") or aspect.get("body1") or "")
                right = str(aspect.get("p2") or aspect.get("body2") or "")
                aspect_type = str(aspect.get("type") or aspect.get("aspect") or "aspect")
            else:
                left_obj, right_obj = getattr(aspect, "a", ""), getattr(aspect, "b", "")
                left = str(getattr(left_obj, "name", left_obj))
                right = str(getattr(right_obj, "name", right_obj))
                aspect_type = str(getattr(aspect, "aspect", "aspect"))
            for _key, label in themes_for_aspect_bodies(left, right):
                grouped.setdefault(label, []).append((left, aspect_type, right))
        while tabs.count():
            old = tabs.widget(0)
            self._host._popout_summary_contexts.pop(old.viewport(), None)
            tabs.removeTab(0)
            old.deleteLater()
        shown_when = when.astimezone(display_timezone) if when and display_timezone else when
        date_label = f"{shown_when:%Y-%m-%d}" if shown_when else "Unknown date"
        for theme_label in sorted(grouped, key=str.casefold):
            output = ChartDataTableOutput()
            output.setReadOnly(True)
            lines = ["🌖Past", "None", "", "🌕Present"]
            aspect_map: dict[int, dict[str, object]] = {}
            for left, aspect_type, right in grouped[theme_label]:
                aspect_map[len(lines)] = {
                    "p1": left, "p2": right, "type": aspect_type,
                    "angle": float(ASPECT_DEFS.get(aspect_type.replace(" ", "_").lower(), {}).get("angle", 0.0)),
                    "delta": 0.0,
                }
                lines.append(f"{date_label}  {left} {aspect_type} {right}  ⓘ")
            lines.extend(["", "🌒Future", "None"])
            output.setPlainText("\n".join(lines))
            apply_chart_data_highlighter(output)
            fmt = QTextCharFormat()
            fmt.setFontWeight(QFont.Bold)
            fmt.setForeground(QColor(CHART_DATA_HIGHLIGHT_COLOR))
            for row in (0, 3, len(lines) - 2):
                cursor = QTextCursor(output.document().findBlockByNumber(row))
                cursor.select(QTextCursor.BlockUnderCursor)
                cursor.mergeCharFormat(fmt)
            output.viewport().installEventFilter(self._host)
            self._host._popout_summary_contexts[output.viewport()] = {
                "output_widget": output, "chart_info_output": chart_info_output,
                "position_info_map": {}, "aspect_info_map": aspect_map,
                "species_info_map": {}, "summary_block_offset": 0,
            }
            output.viewport().destroyed.connect(
                lambda _=None, key=output.viewport(): self._host._popout_summary_contexts.pop(key, None)
            )
            tabs.addTab(output, theme_label)
        if not grouped:
            empty = QPlainTextEdit(f"No themed global transit aspects occur on {date_label}.")
            empty.setReadOnly(True)
            tabs.addTab(empty, "No Themes")

    def action_chart(self) -> Chart | None:
        """Return the chart belonging to the active or most recent visible popout."""
        active_window = QApplication.activeWindow()
        if isinstance(active_window, QDialog):
            active_chart = self._chart_by_dialog.get(active_window)
            if active_chart is not None:
                return active_chart
        for dialog in reversed(self._dialogs):
            chart = self._chart_by_dialog.get(dialog)
            if chart is not None and dialog.isVisible():
                return chart
        return None

    def _build_transit_export_file_stem(
        self,
        transit_chart: Chart,
        *,
        chart_name_for_personal_transit: str | None = None,
    ) -> str:
        timestamp = (
            transit_chart.dt.strftime("%Y-%m-%d_%H%M")
            if transit_chart.dt
            else datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d_%H%M")
        )
        return f"transit_{timestamp}_{_sanitize_export_token(chart_name_for_personal_transit)}"

    @staticmethod
    def _personal_transit_priority(
        hit: Any,
        mode: str,
        natal_planet_weights: dict[str, float] | None = None,
    ) -> float:
        orb_cap = personal_transit_orb_cap(mode, hit.a.name, hit.b.name, hit.aspect)
        if orb_cap <= 0:
            return 0.0
        orb_factor = max(0.0, 1.0 - (float(hit.orb_deg) / orb_cap))
        aspect_key = str(hit.aspect).replace(" ", "_").lower()
        aspect_angle = float(ASPECT_DEFS.get(aspect_key, {}).get("angle", 0.0))
        transit_weight = float(TRANSIT_WEIGHT.get(hit.a.name, 1.0))
        natal_weight = float(
            (natal_planet_weights or NATAL_WEIGHT).get(
                hit.b.name, NATAL_WEIGHT.get(hit.b.name, 1.0)
            )
        )
        return (transit_weight + natal_weight) * float(
            ANGLE_WEIGHT.get(aspect_angle, 1.0)
        ) * orb_factor

    def _sort_personal_transit_mode_aspects(
        self,
        aspect_hits: list[Any],
        sort_mode: str,
        mode: str,
        natal_planet_weights: dict[str, float] | None = None,
    ) -> list[Any]:
        if sort_mode == "Priority":
            return sorted(
                aspect_hits,
                key=lambda hit: self._personal_transit_priority(
                    hit, mode, natal_planet_weights
                ),
                reverse=True,
            )
        return self._host._sort_popout_aspects(aspect_hits, sort_mode)

    def show_personal_transit_chart_popout(
        self,
        natal_chart: Chart,
        transit_chart: Chart,
        transit_positions_in_natal_houses: dict[str, Any],
        aspect_hits_by_mode: dict[str, list[Any]],
                *,
        include_time: bool,
    ) -> None:
        dialog = ManagedTransitPopoutDialog(self._host)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.setWindowTitle(transit_chart.name)
        dialog.setMinimumSize(780, 780)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        dialog.setLayout(layout)
        transit_scaffold = build_transit_popout_scaffold(layout)

        all_hits = list(aspect_hits_by_mode.get(PERSONAL_TRANSIT_MODE_LIFE_FORECAST, []))
        all_hits.extend(aspect_hits_by_mode.get(PERSONAL_TRANSIT_MODE_DAILY_VIBE, []))
        hit_modes: dict[int, str] = {}
        for mode_name, mode_hits in aspect_hits_by_mode.items():
            for hit in mode_hits:
                hit_modes[id(hit)] = mode_name
        natal_planet_weights = getattr(natal_chart, "dominant_planet_weights", None) or _calculate_dominant_planet_weights(natal_chart)

        def _weighted_personal_transit_score(hit: Any) -> float:
            mode_name = hit_modes.get(id(hit), PERSONAL_TRANSIT_MODE_LIFE_FORECAST)
            return max(
                0.0,
                self._personal_transit_priority(
                    hit,
                    mode_name,
                    natal_planet_weights=natal_planet_weights,
                ),
            )

        chart_info_output = self._host._build_popout_left_panel(
            transit_scaffold.aspects_layout,
            chart_info_placeholder="Personal Transit Chart: natal houses with transit planet overlay.",
            aspect_entries=all_hits,
            export_file_stem=f"{_sanitize_export_token(natal_chart.name)}-transit_aspect_distribution",
            weighted_score_for_entry=_weighted_personal_transit_score,
            chart_info_layout=transit_scaffold.chart_info_layout,
        )

        right_layout = transit_scaffold.table_layout

        controls_layout = QGridLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setHorizontalSpacing(8)
        controls_layout.setVerticalSpacing(6)

        controls_layout.addWidget(QLabel("Date"), 0, 0)
        popout_date_input = QDateEdit()
        popout_date_input.setDisplayFormat("yyyy-MM-dd")
        popout_date_input.setCalendarPopup(True)
        popout_date_input.setDateRange(
            QDate(1900, 1, 1),
            QDate(2100, 12, 31),
        )
        controls_layout.addWidget(popout_date_input, 0, 1)

        controls_layout.addWidget(QLabel("Time"), 0, 2)
        popout_time_input = QTimeEdit()
        popout_time_input.setDisplayFormat("HH:mm")
        controls_layout.addWidget(popout_time_input, 0, 3)

        controls_layout.addWidget(QLabel("Place"), 1, 0)
        popout_location_input = QLineEdit()
        popout_location_input.setPlaceholderText("City, Country or lat, lon")
        controls_layout.addWidget(popout_location_input, 1, 1, 1, 3)

        update_button = QPushButton("Update Chart")
        controls_layout.addWidget(update_button, 0, 4, 2, 1)
        right_layout.addLayout(controls_layout)

        local_tz = self._host.transit_panel_controller.display_timezone
        location_label = getattr(transit_chart, "birth_place", None) or getattr(self._host, "_transit_location_label", None) or "Unknown"
        raw_location = location_label
        transit_location = (transit_chart.lat, transit_chart.lon)
        if transit_chart.dt:
            transit_dt_local = transit_chart.dt.astimezone(local_tz)
            popout_date_input.setDate(QDate(transit_dt_local.year, transit_dt_local.month, transit_dt_local.day))
            popout_time_input.setTime(QTime(transit_dt_local.hour, transit_dt_local.minute))
        popout_location_input.setText(raw_location)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)
        header_left = QLabel("")
        header_left.setStyleSheet(CHART_DATA_POPOUT_HEADER_STYLE)
        header_font = header_left.font()
        header_font.setFamily(CHART_DATA_MONOSPACE_FONT_FAMILY)
        header_left.setFont(header_font)
        header_layout.addWidget(header_left, 0, Qt.AlignLeft | Qt.AlignTop)
        header_layout.addStretch(1)

        right_layout.addLayout(header_layout)

        figure = Figure(figsize=(10.9, 10.9))
        canvas = FigureCanvas(figure)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        transit_scaffold.chart_drawing_layout.addWidget(canvas, 1)

        # Keep the Chart Data Output header row aligned with the left
        # popout panel's "Chart Info!" label so both text panels begin on
        # the same horizontal line.
        summary_controls = QHBoxLayout()
        summary_controls.setContentsMargins(0, 0, 0, 0)
        summary_controls.addStretch(1)
        summary_sort_label = QLabel("Aspects")
        summary_sort_label.setStyleSheet("font-weight: bold;")
        summary_sort_combo = QComboBox()
        summary_sort_combo.addItems(ASPECT_SORT_OPTIONS)
        summary_sort_combo.setCurrentText("Priority")
        summary_sort_combo.setMinimumWidth(140)
        summary_controls.addWidget(summary_sort_label)
        summary_controls.addWidget(summary_sort_combo)
        chart_data_header = QWidget()
        chart_data_header.setLayout(summary_controls)
        chart_data_header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        right_layout.addWidget(chart_data_header, 0)

        summary_output = ChartDataTableOutput()
        summary_output.setReadOnly(True)
        output_font = summary_output.font()
        summary_output.setFont(output_font)
        summary_output.setTabStopDistance(6)
        apply_chart_data_highlighter(summary_output)
        summary_output.setPlainText("")
        summary_output.setMinimumHeight(220)
        summary_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        summary_output.viewport().installEventFilter(self._host)
        right_layout.addWidget(summary_output, 3)

        theme_tabs = QTabWidget()
        theme_loading_output = QPlainTextEdit("Calculating major transits for the surrounding 60 days…")
        theme_loading_output.setReadOnly(True)
        theme_tabs.addTab(theme_loading_output, "Themes")
        transit_scaffold.theme_layout.addWidget(theme_tabs, 1)

        def _show_theme_status(message: str) -> None:
            while theme_tabs.count():
                old = theme_tabs.widget(0)
                self._host._popout_summary_contexts.pop(old.viewport(), None)
                theme_tabs.removeTab(0)
                old.deleteLater()
            status = QPlainTextEdit(message)
            status.setReadOnly(True)
            theme_tabs.addTab(status, "Themes")

        transit_timestamp = transit_chart.dt.strftime("%Y-%m-%d_%H%M") if transit_chart.dt else datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d_%H%M")
        transit_file_stem = self._build_transit_export_file_stem(
            transit_chart,
            chart_name_for_personal_transit=natal_chart.name,
        )
        summary_share_button = self._host._attach_popout_share_button(
            summary_output,
            transit_file_stem,
            export_text_provider=lambda: _build_personal_transit_export_text(),
        )
        summary_share_ready_tooltip = summary_share_button.toolTip()

        popout_context_key = summary_output.viewport()
        popout_context: dict[str, object] = {
            "output_widget": summary_output,
            "chart_info_output": chart_info_output,
            "position_info_map": {},
            "aspect_info_map": {},
            "species_info_map": {},
            "summary_block_offset": 0,
            "share_button": summary_share_button,
        }
        self._host._popout_summary_contexts[popout_context_key] = popout_context
        surrounding_major_windows: list[Any] = []
        range_generation = 0
        range_thread: QThread | None = None
        range_worker: PersonalTransitRangeWorker | None = None
        range_relay: PersonalTransitRangeRelay | None = None
        range_loading = False
        range_error: str | None = None

        def _summary_header_lines() -> list[str]:
            return build_personal_transit_header_lines(
                natal_chart_name=natal_chart.name,
                transit_chart=transit_chart,
                location_label=location_label,
                include_time=include_time,
                local_tz=local_tz,
            )

        def _range_status_text() -> str:
            if range_loading:
                return "SURROUNDING MAJOR TRANSITS (±30 DAYS)\n- Calculating…"
            if range_error:
                return (
                    "SURROUNDING MAJOR TRANSITS (±30 DAYS)\n"
                    f"- Unavailable ({range_error})"
                )
            return format_transit_range_table(
                surrounding_major_windows,
                display_timezone=local_tz,
            )

        def _refresh_theme_view() -> None:
            nonlocal range_generation, range_thread, range_worker, range_relay, range_loading, range_error
            center = transit_chart.dt or datetime.datetime.now(datetime.timezone.utc)
            chart_uid = str(
                getattr(natal_chart, "chart_uid", None)
                or getattr(natal_chart, "uid", None)
                or ""
            )
            if not chart_uid:
                range_loading = False
                range_error = "The natal chart must be saved with a permanent Chart UID."
                _show_theme_status("Theme View needs the natal chart's permanent Chart UID. Save the chart first.")
                summary_share_button.setEnabled(True)
                summary_share_button.setToolTip(summary_share_ready_tooltip)
                _refresh_summary()
                return
            range_generation += 1
            generation = range_generation
            range_loading = True
            range_error = None
            if range_thread is not None and range_thread.isRunning():
                range_thread.requestInterruption()
                range_thread.quit()

            _show_theme_status("Calculating major transits for the surrounding 60 days…")
            summary_share_button.setEnabled(False)
            summary_share_button.setToolTip(
                "Export will be available when the surrounding transit scan finishes."
            )
            surrounding_major_windows.clear()
            _refresh_summary()

            thread = QThread()
            worker = PersonalTransitRangeWorker(
                generation,
                chart_uid,
                natal_chart,
                center - datetime.timedelta(days=30),
                center + datetime.timedelta(days=30),
                transit_location,
            )
            relay = PersonalTransitRangeRelay(dialog)
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.finished.connect(relay.forward_ready, Qt.QueuedConnection)
            worker.failed.connect(relay.forward_failed, Qt.QueuedConnection)

            def _range_ready(completed_generation: int, payload: object) -> None:
                nonlocal range_loading, range_error
                if completed_generation != range_generation:
                    return
                range_loading = False
                range_error = None
                windows = list(payload) if isinstance(payload, (list, tuple)) else []
                surrounding_major_windows[:] = windows
                self._set_personal_theme_tabs(
                    theme_tabs, windows, center, chart_info_output, local_tz
                )
                summary_share_button.setEnabled(True)
                summary_share_button.setToolTip(summary_share_ready_tooltip)
                _refresh_summary()

            def _range_failed(failed_generation: int, error_text: str) -> None:
                nonlocal range_loading, range_error
                if failed_generation != range_generation or error_text == "Cancelled":
                    return
                range_loading = False
                range_error = error_text or "Unknown range calculation error"
                logger.warning("Personal Transit range calculation failed: %s", error_text)
                _show_theme_status("Theme View could not calculate this transit range.")
                summary_share_button.setEnabled(True)
                summary_share_button.setToolTip(summary_share_ready_tooltip)
                _refresh_summary()

            def _range_thread_finished(finished_thread: QThread = thread) -> None:
                nonlocal range_thread, range_worker, range_relay
                if finished_thread in transit_retired_threads:
                    transit_retired_threads.remove(finished_thread)
                if range_thread is finished_thread:
                    range_thread = None
                    range_worker = None
                    range_relay = None

            relay.ready.connect(_range_ready)
            relay.failed.connect(_range_failed)
            worker.finished.connect(thread.quit)
            worker.failed.connect(thread.quit)
            thread.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            transit_retired_threads.append(thread)
            thread.finished.connect(_range_thread_finished)
            range_thread = thread
            range_worker = worker
            range_relay = relay
            thread.start()

        def _redraw_chart_wheel() -> None:
            header_left.setText("\n".join(_summary_header_lines()[2:4]))
            dialog.setWindowTitle(transit_chart.name)
            figure.clear()
            overlay_positions = {
                name: body.lon_deg
                for name, body in transit_positions_in_natal_houses.items()
                if name not in {"AS", "MC", "DS", "IC"}
            }
            all_aspect_hits = list(aspect_hits_by_mode.get(PERSONAL_TRANSIT_MODE_LIFE_FORECAST, []))
            all_aspect_hits.extend(aspect_hits_by_mode.get(PERSONAL_TRANSIT_MODE_DAILY_VIBE, []))
            natal_for_plot = copy.deepcopy(natal_chart)
            natal_for_plot.name = transit_chart.name
            natal_for_plot.aspects = []
            overlay_aspects = _overlay_aspect_segments(all_aspect_hits)
            draw_chart_wheel(
                figure,
                natal_for_plot,
                canvas=canvas,
                overlay_positions=overlay_positions,
                overlay_aspects=overlay_aspects,
                overlay_aspects_only=True,
                overlay_color="#b54a4a",
                overlay_sign_color="#de8a8a",
                base_monochrome_color="#4f72b8",
                wheel_padding=0.03,
                show_title=False,
                symbol_scale=0.7,
            )
            canvas.draw_idle()

        transit_ranges: dict[tuple[str, str, str, str], dict[str, object]] = {}
        transit_workers: dict[
            tuple[str, str, str, str],
            tuple[QThread, TransitAspectWindowWorker, TransitAspectWindowRelay],
        ] = {}
        transit_retired_threads: list[QThread] = []
        calendar_info_map: dict[int, dict[str, object]] = {}
        mode_labels = {
            PERSONAL_TRANSIT_MODE_LIFE_FORECAST: "Life Forecast",
            PERSONAL_TRANSIT_MODE_DAILY_VIBE: "Daily Vibe",
        }
        mode_rules = {
            PERSONAL_TRANSIT_MODE_LIFE_FORECAST: personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_LIFE_FORECAST),
            PERSONAL_TRANSIT_MODE_DAILY_VIBE: personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_DAILY_VIBE),
        }
        transit_scan_config = resolve_transit_window_scan_config()

        def _scan_config_for_hit(hit_obj: Any):
            return resolve_transit_window_scan_config_for_transit_body(
                str(hit_obj.a.name),
                base_config=transit_scan_config,
            )
        natal_planet_weights = getattr(natal_chart, "dominant_planet_weights", None)
        if not natal_planet_weights:
            natal_planet_weights = _calculate_dominant_planet_weights(natal_chart)

        def _transit_range_key(mode: str, hit_obj: Any) -> tuple[str, str, str, str]:
            return (
                str(mode),
                str(hit_obj.a.name),
                str(hit_obj.aspect),
                str(hit_obj.b.name),
            )

        def _build_personal_transit_sections(sort_mode: str) -> list[tuple[str, str, list[tuple[Any, str]], str]]:
            daily_hits, rollover_hits = split_daily_vibe_hits_by_expected_duration(
                aspect_hits_by_mode.get(PERSONAL_TRANSIT_MODE_DAILY_VIBE, [])
            )
            return [
                (
                    "Daily Vibe",
                    "(Short-term 1-3 day personal transits)",
                    [
                        (hit, PERSONAL_TRANSIT_MODE_DAILY_VIBE)
                        for hit in self._sort_personal_transit_mode_aspects(
                            daily_hits,
                            sort_mode,
                            PERSONAL_TRANSIT_MODE_DAILY_VIBE,
                            natal_planet_weights=natal_planet_weights,
                        )
                    ],
                    PERSONAL_TRANSIT_MODE_DAILY_VIBE,
                ),
                (
                    "Life Forecast",
                    "(Longer-term and structural transits)",
                    [
                        (hit, PERSONAL_TRANSIT_MODE_LIFE_FORECAST)
                        for hit in self._sort_personal_transit_mode_aspects(
                            aspect_hits_by_mode.get(PERSONAL_TRANSIT_MODE_LIFE_FORECAST, []),
                            sort_mode,
                            PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
                            natal_planet_weights=natal_planet_weights,
                        )
                    ]
                    + [
                        (hit, PERSONAL_TRANSIT_MODE_DAILY_VIBE)
                        for hit in self._sort_personal_transit_mode_aspects(
                            rollover_hits,
                            sort_mode,
                            PERSONAL_TRANSIT_MODE_DAILY_VIBE,
                            natal_planet_weights=natal_planet_weights,
                        )
                    ],
                    PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
                ),
            ]

        def _window_cache_key(mode: str, hit_obj: Any) -> tuple[object, ...]:
            chart_dt = transit_chart.dt
            scan_config = _scan_config_for_hit(hit_obj)
            return self._host.transit_panel_controller.transit_window_cache_key(
                mode=mode,
                hit_obj=hit_obj,
                chart_dt=chart_dt,
                transit_location=transit_location,
                mode_rules=mode_rules,
                scan_config=scan_config,
            )

        def _window_cache_get(cache_key: tuple[object, ...]) -> dict[str, object] | None:
            return self._host.transit_panel_controller.get_transit_window_cache(cache_key)

        def _window_cache_put(cache_key: tuple[object, ...], payload: dict[str, object]) -> None:
            self._host.transit_panel_controller.put_transit_window_cache(cache_key, payload)

        _transit_shutdown_in_progress = False
        _transit_shutdown_callbacks: list[Callable[[], None]] = []

        def _finalize_transit_worker_shutdown() -> None:
            nonlocal _transit_shutdown_in_progress
            pending_keys = list(transit_workers.keys())
            for key in pending_keys:
                worker_entry = transit_workers.get(key)
                if worker_entry is None:
                    continue
                thread, _worker, _relay = worker_entry
                if thread.isRunning():
                    logger.debug(
                        "Transit worker shutdown still waiting (active_workers=%s retired_threads=%s).",
                        len(transit_workers),
                        len(transit_retired_threads),
                    )
                    return
                transit_workers.pop(key, None)
            if any(thread.isRunning() for thread in transit_retired_threads):
                logger.debug(
                    "Transit worker shutdown still waiting on retired threads (active_workers=%s retired_threads=%s).",
                    len(transit_workers),
                    len(transit_retired_threads),
                )
                return
            transit_retired_threads[:] = [thread for thread in transit_retired_threads if thread.isRunning()]

            callbacks = list(_transit_shutdown_callbacks)
            _transit_shutdown_callbacks.clear()
            _transit_shutdown_in_progress = False
            logger.debug(
                "Transit worker shutdown completed (callbacks=%s retired_threads=%s).",
                len(callbacks),
                len(transit_retired_threads),
            )
            for callback in callbacks:
                callback()

        #ojo: changes here feel risky...
        def _begin_transit_worker_shutdown(on_complete: Callable[[], None]) -> None:
            nonlocal _transit_shutdown_in_progress

            _transit_shutdown_callbacks.append(on_complete)
            if _transit_shutdown_in_progress:
                return
            _transit_shutdown_in_progress = True
            debug_id = _new_debug_action_id("transit_shutdown")
            logger.debug(
                "Transit worker shutdown started (id=%s active_workers=%s).",
                debug_id,
                len(transit_workers),
            )

            for key, (thread, _worker, _relay) in list(transit_workers.items()):
                try:
                    thread.finished.connect(_finalize_transit_worker_shutdown)
                    thread.requestInterruption()
                    thread.quit()
                except RuntimeError:
                    logger.exception(
                        "Transit worker shutdown runtime error (id=%s worker_key=%s).",
                        debug_id,
                        key,
                    )
                    transit_workers.pop(key, None)
                    continue
            for thread in list(transit_retired_threads):
                if thread.isRunning():
                    thread.finished.connect(_finalize_transit_worker_shutdown)
                    thread.requestInterruption()
                    thread.quit()
            _finalize_transit_worker_shutdown()
            logger.debug(
                "Transit worker shutdown requests sent (id=%s active_workers=%s).",
                debug_id,
                len(transit_workers),
            )

        dialog.destroyed.connect(lambda _=None, key=popout_context_key: self._host._popout_summary_contexts.pop(key, None))
        dialog.set_async_shutdown(_begin_transit_worker_shutdown)

        def _refresh_summary() -> None:
            def _canonical_interpretation_house(body_name: str, fallback_house: int | None) -> int | None:
                angle_houses = {
                    "AS": 1,
                    "IC": 4,
                    "DS": 7,
                    "MC": 10,
                }
                return angle_houses.get(str(body_name), fallback_house)

            vertical_scrollbar = summary_output.verticalScrollBar()
            horizontal_scrollbar = summary_output.horizontalScrollBar()
            previous_vertical_position = vertical_scrollbar.value()
            previous_horizontal_position = horizontal_scrollbar.value()
            sort_mode = summary_sort_combo.currentText()
            lines = _summary_header_lines()
            aspect_info_map: dict[int, dict[str, object]] = {}
            calendar_info_map.clear()
            sections = _build_personal_transit_sections(sort_mode)
            for _section_title, _section_subtitle, entries, empty_mode in sections:
                lines.extend([_section_title, _section_subtitle, ""])
                if entries:
                    for hit, source_mode in entries[:80]:
                        key = _transit_range_key(source_mode, hit)
                        state = transit_ranges.setdefault(
                            key,
                            {
                                "expanded": False,
                                "resolving": False,
                                "resolved": False,
                                "failed": False,
                                "start": None,
                                "end": None,
                                "start_truncated_to_scope": False,
                                "end_truncated_to_scope": False,
                                "error": "",
                                "hit": hit,
                                "cache_key": _window_cache_key(source_mode, hit),
                                "mode": source_mode,
                                "include_time": include_time,
                            },
                        )
                        scan_config = _scan_config_for_hit(hit)
                        state["hit"] = hit
                        state["cache_key"] = _window_cache_key(source_mode, hit)
                        state["mode"] = source_mode
                        state["include_time"] = scan_config.include_time
                        suffix = "📆"
                        if state["resolving"]:
                            suffix = "📆 …"
                        elif state["failed"]:
                            error_text = state.get("error", "")
                            suffix = f"📆 ⚠ {error_text}" if error_text else "📆 ⚠"
                        elif state["resolved"]:
                            suffix = _format_transit_range(
                                state["start"],
                                state["end"],
                                include_time=bool(state.get("include_time", include_time)),
                                display_timezone=local_tz,
                                start_truncated_to_scope=bool(state.get("start_truncated_to_scope", False)),
                                end_truncated_to_scope=bool(state.get("end_truncated_to_scope", False)),
                            )
                        left_label = _format_popout_aspect_endpoint(hit.a, include_house=False)
                        right_label = _format_popout_aspect_endpoint(hit.b, include_house=True)
                        line = (
                            f"- {left_label:<26} {hit.aspect:<14} {right_label:<30} "
                            f"orb {_format_degree_minutes(hit.orb_deg, include_sign=False):<8}  ⓘ {suffix}"
                        )
                        aspect_type = str(hit.aspect).replace(" ", "_").lower()
                        angle = float(ASPECT_DEFS.get(aspect_type, {}).get("angle", 0.0))
                        aspect_info_map[len(lines)] = {
                            "p1": hit.a.name,
                            "p2": hit.b.name,
                            "type": str(hit.aspect),
                            "angle": angle,
                            "delta": float(hit.orb_deg),
                            "sign1": hit.a.sign,
                            "sign2": hit.b.sign,
                            "house1": _canonical_interpretation_house(hit.a.name, hit.a.house),
                            "house2": _canonical_interpretation_house(hit.b.name, hit.b.house),
                        }
                        icon_index = line.rfind("📆")
                        if icon_index >= 0:
                            calendar_info_map[len(lines)] = {
                                "key": key,
                                "icon_index": icon_index,
                            }
                        lines.append(line)
                else:
                    lines.append(f"- No {mode_labels.get(empty_mode, empty_mode)} aspects within configured orbs.")
                lines.append("")
            lines.extend(["", _range_status_text()])
            summary_output.setPlainText("\n".join(lines))
            popout_context["aspect_info_map"] = aspect_info_map
            def _restore_scroll_positions() -> None:
                vertical_scrollbar.setValue(min(previous_vertical_position, vertical_scrollbar.maximum()))
                horizontal_scrollbar.setValue(min(previous_horizontal_position, horizontal_scrollbar.maximum()))

            QTimer.singleShot(0, _restore_scroll_positions)
        transit_generation = 0

        def _on_window_thread_finished(key: tuple[str, str, str, str], generation: int) -> None:
            if generation != transit_generation:
                transit_workers.pop(key, None)
                _finalize_transit_worker_shutdown()
                return
            transit_workers.pop(key, None)
            _finalize_transit_worker_shutdown()
            _drain_preload_queue()

        def _stop_window_worker(key: tuple[str, str, str, str]) -> None:
            worker_entry = transit_workers.get(key)
            if worker_entry is not None:
                thread, _worker, _relay = worker_entry
                try:
                    thread.requestInterruption()
                    thread.quit()
                except RuntimeError:
                    transit_workers.pop(key, None)

        def _on_window_ready(key: tuple[str, str, str, str], start_dt: object, end_dt: object, metadata: object, generation: int) -> None:
            debug_id = _new_debug_action_id("transit_window_ready")
            if generation != transit_generation:
                logger.debug(
                    "Transit window ready ignored because worker generation is stale (id=%s key=%s generation=%s current=%s).",
                    debug_id,
                    key,
                    generation,
                    transit_generation,
                )
                return
            state = transit_ranges.get(key)
            if state is None:
                logger.debug(
                    "Transit window ready ignored because state was missing (id=%s key=%s).",
                    debug_id,
                    key,
                )
                return
            cache_key = state.get("cache_key")
            state["resolved"] = True
            state["resolving"] = False
            state["failed"] = False
            state["expanded"] = True
            state["start"] = start_dt
            state["end"] = end_dt
            if isinstance(metadata, dict):
                state["start_truncated_to_scope"] = bool(metadata.get("start_truncated_to_scope", False))
                state["end_truncated_to_scope"] = bool(metadata.get("end_truncated_to_scope", False))
            else:
                state["start_truncated_to_scope"] = False
                state["end_truncated_to_scope"] = False

            if isinstance(cache_key, tuple):
                _window_cache_put(cache_key, {"resolved": True, "failed": False, "start": start_dt, "end": end_dt, "start_truncated_to_scope": bool(state["start_truncated_to_scope"]), "end_truncated_to_scope": bool(state["end_truncated_to_scope"]), "error": ""})
            logger.debug(
                "Transit window resolved (id=%s key=%s start=%r end=%r).",
                debug_id,
                key,
                start_dt,
                end_dt,
            )
            _refresh_summary()
            _drain_preload_queue()

        def _on_window_failed(key: tuple[str, str, str, str], error_text: str, generation: int) -> None:
            debug_id = _new_debug_action_id("transit_window_failed")
            if generation != transit_generation:
                logger.debug(
                    "Transit window failure ignored because worker generation is stale (id=%s key=%s generation=%s current=%s error=%r).",
                    debug_id,
                    key,
                    generation,
                    transit_generation,
                    error_text,
                )
                return
            state = transit_ranges.get(key)
            if state is None:
                logger.debug(
                    "Transit window failure ignored because state was missing (id=%s key=%s error=%r).",
                    debug_id,
                    key,
                    error_text,
                )
                return
            cache_key = state.get("cache_key")
            state["resolved"] = False
            state["resolving"] = False
            state["start_truncated_to_scope"] = False
            state["end_truncated_to_scope"] = False
            state["failed"] = error_text != "Cancelled"
            state["error"] = "" if error_text == "Cancelled" else error_text

            if error_text != "Cancelled" and isinstance(cache_key, tuple):
                _window_cache_put(cache_key, {"resolved": False, "failed": True, "start": None, "end": None, "start_truncated_to_scope": False, "end_truncated_to_scope": False, "error": error_text})
            if error_text == "Cancelled":
                logger.info("Transit window cancelled (id=%s key=%s).", debug_id, key)
            else:
                logger.warning(
                    "Transit window failed (id=%s key=%s error=%r).",
                    debug_id,
                    key,
                    error_text,
                )
            _refresh_summary()
            _drain_preload_queue()

        MAX_TRANSIT_WINDOW_WORKERS = 2
        preload_queue: list[tuple[str, str, str, str]] = []

        def _start_window_worker(key: tuple[str, str, str, str], state: dict[str, object], *, refresh: bool) -> None:
            hit = state.get("hit")
            mode = str(state.get("mode", PERSONAL_TRANSIT_MODE_LIFE_FORECAST))
            if hit is None:
                return
            generation = transit_generation

            state["resolving"] = True
            state["failed"] = False
            state["error"] = ""
            state["start_truncated_to_scope"] = False
            state["end_truncated_to_scope"] = False
            if refresh:
                _refresh_summary()

            # Keep worker threads independent from dialog ownership so dialog teardown
            # cannot delete a still-running QThread wrapper.
            thread = QThread()
            scan_config = _scan_config_for_hit(hit)
            state["include_time"] = scan_config.include_time
            worker = TransitAspectWindowWorker(
                natal_chart,
                transit_chart.dt,
                transit_location,
                hit,
                mode_rules.get(mode, TRANSIT_ASPECT_RULES),
                step_hours=scan_config.scan_step_hours,
                precision_minutes=scan_config.scan_precision_minutes,
            )
            relay = TransitAspectWindowRelay(dialog)
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.finished.connect(relay.forward_ready, Qt.QueuedConnection)
            worker.failed.connect(relay.forward_failed, Qt.QueuedConnection)
            relay.ready.connect(
                lambda a, b, c, start_dt, end_dt, metadata, mode=mode, generation=generation: _on_window_ready(
                    (str(mode), str(a), str(b), str(c)),
                    start_dt,
                    end_dt,
                    metadata,
                    generation,
                )
            )
            relay.failed.connect(
                lambda a, b, c, error_text, mode=mode, generation=generation: _on_window_failed(
                    (str(mode), str(a), str(b), str(c)),
                    error_text,
                    generation,
                )
            )
            worker.finished.connect(thread.quit)
            worker.failed.connect(thread.quit)
            thread.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            thread.finished.connect(lambda key=key, generation=generation: _on_window_thread_finished(key, generation))
            thread.finished.connect(lambda thread=thread: transit_retired_threads.remove(thread) if thread in transit_retired_threads else None)
            transit_workers[key] = (thread, worker, relay)
            transit_retired_threads.append(thread)
            thread.start()

        def _drain_preload_queue() -> None:
            while preload_queue and len(transit_workers) < MAX_TRANSIT_WINDOW_WORKERS:
                queue_key = preload_queue.pop(0)
                state = transit_ranges.get(queue_key)
                if state is None:
                    continue
                if state.get("resolved") or state.get("resolving") or state.get("failed"):
                    continue
                _start_window_worker(queue_key, state, refresh=False)
            if not transit_workers:
                _refresh_summary()

        def _ensure_window_async(key: tuple[str, str, str, str], state: dict[str, object]) -> None:
            if state["resolved"]:
                state["expanded"] = True
                _refresh_summary()
                return
            if state["resolving"]:
                self._host.transit_panel_controller.record_transit_window_inflight_dedupe()
                return
            hit = state.get("hit")
            mode = str(state.get("mode", PERSONAL_TRANSIT_MODE_LIFE_FORECAST))
            if hit is None:
                return
            cache_key = state.get("cache_key")
            if isinstance(cache_key, tuple):
                cached_payload = _window_cache_get(cache_key)
                if isinstance(cached_payload, dict):
                    state["resolved"] = bool(cached_payload.get("resolved", False))
                    state["failed"] = bool(cached_payload.get("failed", False))
                    state["resolving"] = False
                    state["expanded"] = True
                    state["start"] = cached_payload.get("start")
                    state["end"] = cached_payload.get("end")
                    state["start_truncated_to_scope"] = bool(cached_payload.get("start_truncated_to_scope", False))
                    state["end_truncated_to_scope"] = bool(cached_payload.get("end_truncated_to_scope", False))
                    state["error"] = str(cached_payload.get("error", ""))
                    _refresh_summary()
                    return

            _start_window_worker(key, state, refresh=True)

        def _build_personal_transit_export_text() -> str:
            lines = _summary_header_lines()
            sort_mode = summary_sort_combo.currentText()
            sections = _build_personal_transit_sections(sort_mode)
            for section_title, section_subtitle, entries, empty_mode in sections:
                lines.extend([section_title, section_subtitle, ""])
                if entries:
                    for hit, source_mode in entries[:80]:
                        key = _transit_range_key(source_mode, hit)
                        state = transit_ranges.get(key, {})
                        start_dt = state.get("start")
                        end_dt = state.get("end")
                        start_truncated = bool(state.get("start_truncated_to_scope", False))
                        end_truncated = bool(state.get("end_truncated_to_scope", False))
                        resolved = bool(state.get("resolved", False))
                        failed = bool(state.get("failed", False))
                        error_text = str(state.get("error", "") or "")

                        if not resolved and not failed:
                            cache_key = _window_cache_key(source_mode, hit)
                            cached_payload = _window_cache_get(cache_key)
                            if isinstance(cached_payload, dict):
                                resolved = bool(cached_payload.get("resolved", False))
                                failed = bool(cached_payload.get("failed", False))
                                start_dt = cached_payload.get("start")
                                end_dt = cached_payload.get("end")
                                start_truncated = bool(cached_payload.get("start_truncated_to_scope", False))
                                end_truncated = bool(cached_payload.get("end_truncated_to_scope", False))
                                error_text = str(cached_payload.get("error", "") or "")

                        if not resolved and not failed:
                            try:
                                result = find_transit_aspect_window_result(
                                    natal_chart,
                                    transit_chart.dt,
                                    transit_location,
                                    hit,
                                    mode_rules.get(source_mode, TRANSIT_ASPECT_RULES),
                                    step_hours=_scan_config_for_hit(hit).scan_step_hours,
                                    precision_minutes=_scan_config_for_hit(hit).scan_precision_minutes,
                                )
                                if result.out_of_scope:
                                    failed = True
                                    error_text = "Transit date is outside the configured ephemeris scope."
                                else:
                                    start_dt = result.start
                                    end_dt = result.end
                                    start_truncated = bool(result.start_truncated_to_scope)
                                    end_truncated = bool(result.end_truncated_to_scope)
                                    resolved = True
                            except Exception:
                                failed = True
                                error_text = "window lookup failed"

                        if resolved:
                            row_include_time = bool(state.get("include_time", _scan_config_for_hit(hit).include_time))
                            window_text = _format_transit_range(
                                start_dt,
                                end_dt,
                                include_time=row_include_time,
                                display_timezone=local_tz,
                                start_truncated_to_scope=start_truncated,
                                end_truncated_to_scope=end_truncated,
                            )
                        elif failed:
                            window_text = f"Unavailable ({error_text})" if error_text else "Unavailable"
                        else:
                            window_text = "Unavailable"

                        left_label = _format_popout_aspect_endpoint(hit.a, include_house=False)
                        right_label = _format_popout_aspect_endpoint(hit.b, include_house=True)
                        lines.append(
                            f"- {left_label:<26} {hit.aspect:<14} {right_label:<30} "
                            f"orb {_format_degree_minutes(hit.orb_deg, include_sign=False):<8}  "
                            f"window {window_text}"
                        )
                else:
                    lines.append(f"- No {mode_labels.get(empty_mode, empty_mode)} aspects within configured orbs.")
                lines.append("")
            lines.extend(["", _range_status_text()])
            return "\n".join(lines)

        def _handle_calendar_click(cursor) -> bool:
            block_number = cursor.block().blockNumber()
            entry = calendar_info_map.get(block_number)
            if not entry:
                return False
            if cursor.positionInBlock() < entry["icon_index"]:
                return False
            key = entry["key"]
            state = transit_ranges.get(key)
            if state is None:
                return False
            if state["resolved"]:
                return True
            _ensure_window_async(key, state)
            return True

        def _arrest_transit_window_loads_for_update() -> None:
            nonlocal transit_generation, range_generation

            transit_generation += 1
            range_generation += 1
            preload_queue.clear()
            for key, (thread, _worker, _relay) in list(transit_workers.items()):
                try:
                    thread.requestInterruption()
                    thread.quit()
                except RuntimeError:
                    logger.debug(
                        "Transit worker was already unavailable while arresting loads for update (key=%s).",
                        key,
                    )
            transit_workers.clear()
            if range_thread is not None and range_thread.isRunning():
                range_thread.requestInterruption()
                range_thread.quit()

        def _on_update_chart() -> None:
            nonlocal transit_chart, transit_positions_in_natal_houses, aspect_hits_by_mode, transit_location, include_time, location_label, raw_location

            try:
                resolved_location = resolve_personal_transit_location(
                    popout_location_input.text(),
                    fallback_lat=transit_chart.lat,
                    fallback_lon=transit_chart.lon,
                    fallback_location_label=location_label,
                )
            except PersonalTransitLocationError as error:
                QMessageBox.warning(
                    dialog,
                    "Location lookup failed",
                    f"Could not resolve location '{popout_location_input.text().strip()}'.\n{error}",
                )
                return

            selected_date = popout_date_input.date()
            selected_time = popout_time_input.time()
            selected_local = datetime.datetime(
                selected_date.year(),
                selected_date.month(),
                selected_date.day(),
                selected_time.hour(),
                selected_time.minute(),
                tzinfo=local_tz,
            )
            raw_location_text = popout_location_input.text()

            try:
                recalculated = recalculate_personal_transit(
                    natal_chart=natal_chart,
                    selected_local_datetime=selected_local,
                    location=resolved_location,
                    raw_location=raw_location_text,
                )
            except Exception as exc:
                logger.exception("Failed to update personal transit chart.")
                QMessageBox.warning(
                    dialog,
                    "Update Chart",
                    f"Failed to update personal transit chart.\n\n{exc}",
                )
                _refresh_summary()
                return

            # Keep the current chart's range worker and export state intact if
            # recalculation fails. Only invalidate it once replacement chart
            # data has been produced successfully.
            _arrest_transit_window_loads_for_update()
            transit_chart = recalculated.transit_chart
            transit_positions_in_natal_houses = recalculated.transit_positions_in_natal_houses
            aspect_hits_by_mode = recalculated.aspect_hits_by_mode
            transit_location = (recalculated.transit_chart.lat, recalculated.transit_chart.lon)
            include_time = recalculated.include_time
            location_label = recalculated.location_label
            raw_location = recalculated.raw_location
            popout_location_input.setText(raw_location)
            transit_ranges.clear()
            calendar_info_map.clear()
            preload_queue.clear()
            _redraw_chart_wheel()
            _refresh_theme_view()
            preload_queue.extend([key for key, state in transit_ranges.items() if not state.get("resolved")])
            QTimer.singleShot(0, _drain_preload_queue)

        popout_context["custom_click_handler"] = _handle_calendar_click

        summary_sort_combo.currentTextChanged.connect(lambda _text: _refresh_summary())
        update_button.clicked.connect(_on_update_chart)
        _redraw_chart_wheel()
        _refresh_theme_view()
        preload_queue[:] = [key for key, state in transit_ranges.items() if not state.get("resolved")]
        QTimer.singleShot(0, _drain_preload_queue)

        dialog.resize(1320, 1080)
        self._host._register_popout_shortcuts(dialog)
        dialog.show()
        self._dialogs.append(dialog)
        dialog.destroyed.connect(
            lambda _=None, dialog=dialog: self._dialogs.remove(dialog)
            if dialog in self._dialogs
            else None
        )


    def show_transit_chart_popout(self, chart: Chart) -> None:
        dialog = QDialog(self._host)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.setMinimumSize(780, 780)
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        dialog.setLayout(layout)
        transit_scaffold = build_transit_popout_scaffold(layout)

        chart_info_output = self._host._build_popout_left_panel(
            transit_scaffold.aspects_layout,
            chart_info_placeholder="Click the ⓘ in chart summary text to see details/interpretation.",
            aspect_entries=list(
                iter_displayable_aspects(
                    getattr(chart, "aspects", []) or [],
                    use_houses=_chart_uses_houses(chart),
                    known_positions=getattr(chart, "positions", {}) or {},
                )
            ),
            export_file_stem=f"{_sanitize_export_token(chart.name)}-transit_aspect_distribution",
            weighted_score_for_entry=lambda entry: max(
                0.0,
                float(
                    _aspect_score(
                        entry,
                        planet_weights=(
                            getattr(chart, "dominant_planet_weights", None)
                            or _calculate_dominant_planet_weights(chart)
                        ),
                    )
                ),
            )
            if isinstance(entry, dict)
            else max(0.0, float(getattr(entry, "exactness", 0.0)) * float(getattr(entry, "weight", 0.0))),
            chart_info_layout=transit_scaffold.chart_info_layout,
        )

        right_layout = transit_scaffold.table_layout

        controls_layout = QGridLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setHorizontalSpacing(8)
        controls_layout.setVerticalSpacing(6)

        controls_layout.addWidget(QLabel("Date"), 0, 0)
        popout_date_input = QDateEdit()
        popout_date_input.setDisplayFormat("yyyy-MM-dd")
        popout_date_input.setCalendarPopup(True)
        popout_date_input.setDateRange(
            QDate(1900, 1, 1),
            QDate(2100, 12, 31),
        )
        controls_layout.addWidget(popout_date_input, 0, 1)

        controls_layout.addWidget(QLabel("Time"), 0, 2)
        popout_time_input = QTimeEdit()
        popout_time_input.setDisplayFormat("HH:mm")
        controls_layout.addWidget(popout_time_input, 0, 3)

        controls_layout.addWidget(QLabel("Place"), 1, 0)
        popout_location_input = QLineEdit()
        popout_location_input.setPlaceholderText("City, Country or lat, lon")
        controls_layout.addWidget(popout_location_input, 1, 1, 1, 3)

        update_button = QPushButton("Update Chart")
        controls_layout.addWidget(update_button, 0, 4, 2, 1)
        right_layout.addLayout(controls_layout)

        figure = Figure(figsize=(10.9, 10.9))
        canvas = FigureCanvas(figure)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        transit_scaffold.chart_drawing_layout.addWidget(canvas, 1)

        # Keep the Chart Data Output header row aligned with the left
        # popout panel's "Chart Info!" label so both text panels begin on
        # the same horizontal line.
        summary_controls = QHBoxLayout()
        summary_controls.setContentsMargins(0, 0, 0, 0)
        summary_controls.addStretch(1)
        summary_sort_label = QLabel("Aspects")
        summary_sort_label.setStyleSheet("font-weight: bold;")
        summary_sort_combo = QComboBox()
        summary_sort_combo.addItems(ASPECT_SORT_OPTIONS)
        summary_sort_combo.setCurrentText("Priority")
        summary_sort_combo.setMinimumWidth(140)
        summary_controls.addWidget(summary_sort_label)
        summary_controls.addWidget(summary_sort_combo)
        chart_data_header = QWidget()
        chart_data_header.setLayout(summary_controls)
        chart_data_header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        right_layout.addWidget(chart_data_header, 0)

        summary_output = ChartDataTableOutput()
        summary_output.setReadOnly(True)
        output_font = summary_output.font()
        summary_output.setFont(output_font)
        summary_output.setTabStopDistance(6)
        apply_chart_data_highlighter(summary_output)
        summary_output.setPlainText("")
        summary_output.setMinimumHeight(220)
        summary_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        summary_output.viewport().installEventFilter(self._host)
        right_layout.addWidget(summary_output, 3)

        theme_tabs = QTabWidget()
        transit_scaffold.theme_layout.addWidget(theme_tabs, 1)

        state: dict[str, object] = {
            "chart": chart,
            "location_label": getattr(self._host, "_transit_location_label", None) or "Unknown",
            "raw_location": getattr(self._host, "_transit_location_label", None) or "",
            "time_label": "unknown" if getattr(chart, "birthtime_unknown", False) else chart.dt.strftime("%H:%M"),
            "date_label": chart.dt.strftime("%m.%d.%Y") if chart.dt else "??.??.????",
        }

        if chart.dt:
            local_dt = chart.dt.astimezone(datetime.datetime.now().astimezone().tzinfo or datetime.timezone.utc)
            popout_date_input.setDate(QDate(local_dt.year, local_dt.month, local_dt.day))
            popout_time_input.setTime(QTime(local_dt.hour, local_dt.minute))
        popout_location_input.setText(str(state["raw_location"]))

        transit_file_stem = self._build_transit_export_file_stem(
            chart,
            chart_name_for_personal_transit=chart.name if chart.name.startswith("Personal Transit Chart for ") else None,
        )

        def _build_transit_export_text(chart_data_text: str) -> str:
            active_chart = state["chart"]
            assert isinstance(active_chart, Chart)
            return build_transit_chart_export_text(
                chart=active_chart,
                date_label=str(state["date_label"]),
                time_label=str(state["time_label"]),
                location_label=str(state["location_label"]),
                chart_data_text=chart_data_text,
            )

        summary_share_button = self._host._attach_popout_share_button(
            summary_output,
            transit_file_stem,
            export_text_provider=lambda: _build_transit_export_text(summary_output.toPlainText()),
        )

        popout_context_key = summary_output.viewport()
        popout_context: dict[str, object] = {
            "output_widget": summary_output,
            "chart_info_output": chart_info_output,
            "position_info_map": {},
            "aspect_info_map": {},
            "species_info_map": {},
            "summary_block_offset": 0,
            "share_button": summary_share_button,
        }
        self._host._popout_summary_contexts[popout_context_key] = popout_context
        dialog.destroyed.connect(
            lambda _=None, key=popout_context_key: self._host._popout_summary_contexts.pop(key, None)
        )

        def _refresh_summary() -> None:
            active_chart = state["chart"]
            assert isinstance(active_chart, Chart)
            sort_mode = summary_sort_combo.currentText()
            chart_summary_text, position_info_map, aspect_info_map, species_info_map = format_chart_text(
                active_chart,
                aspect_sort=sort_mode,
                **self._host._chart_data_visibility_options(),
            )
            summary_lines_local = chart_summary_text.splitlines()
            positions_start_index = next(
                (idx for idx, line in enumerate(summary_lines_local) if line.strip() in {"POSITIONS", "POSITIONS (Tropical)"}),
                0,
            )
            draconic_start_index = next(
                (
                    idx
                    for idx, line in enumerate(summary_lines_local)
                    if line.strip() in {"DRACONIC POSITIONS", "POSITIONS (Draconic)"}
                ),
                len(summary_lines_local),
            )
            visible_summary_lines = summary_lines_local[
                positions_start_index:draconic_start_index
            ]
            transit_visible_lines: list[str] = []
            for line in visible_summary_lines:
                stripped = line.strip()
                if stripped.startswith("🐣date:"):
                    transit_visible_lines.append(line.replace("🐣date:", "Date:", 1))
                elif stripped.startswith("🐣time:"):
                    transit_visible_lines.append(line.replace("🐣time:", "Time:", 1))
                elif stripped.startswith("🐣place:"):
                    transit_visible_lines.append(
                        f"🐣Location:   {state['location_label']}, {active_chart.lat:.4f}, {active_chart.lon:.4f}"
                    )
                else:
                    transit_visible_lines.append(line)
            summary_output.setPlainText("\n".join(transit_visible_lines))
            popout_context["position_info_map"] = position_info_map
            popout_context["aspect_info_map"] = aspect_info_map
            popout_context["species_info_map"] = species_info_map
            popout_context["summary_block_offset"] = positions_start_index
            self._set_global_theme_tabs(
                theme_tabs,
                list(iter_displayable_aspects(
                    getattr(active_chart, "aspects", []) or [],
                    use_houses=_chart_uses_houses(active_chart),
                    known_positions=getattr(active_chart, "positions", {}) or {},
                )),
                active_chart.dt,
                chart_info_output,
                self._host.transit_panel_controller.display_timezone,
            )

        def _redraw() -> None:
            active_chart = state["chart"]
            assert isinstance(active_chart, Chart)
            dialog.setWindowTitle(
                f"Transit Chart for {state['time_label']} on {active_chart.dt.strftime('%A') if active_chart.dt else 'Unknown day'}, {active_chart.dt.strftime('%Y-%m-%d') if active_chart.dt else 'Unknown date'} in {state['location_label']}"
            )
            figure.clear()
            draw_chart_wheel(
                figure,
                active_chart,
                canvas=canvas,
                wheel_padding=0.03,
                show_title=False,
                symbol_scale=0.7,
            )
            canvas.draw_idle()
            self._chart_by_dialog[dialog] = active_chart
            _refresh_summary()

        def _resolve_popout_location(raw_value: str) -> tuple[float, float, str] | None:
            value = raw_value.strip()
            if not value:
                active_chart = state["chart"]
                assert isinstance(active_chart, Chart)
                return float(active_chart.lat), float(active_chart.lon), str(state["location_label"])

            if "," in value:
                maybe_lat, maybe_lon = value.split(",", 1)
                try:
                    parsed_lat = float(maybe_lat.strip())
                    parsed_lon = float(maybe_lon.strip())
                    if -90.0 <= parsed_lat <= 90.0 and -180.0 <= parsed_lon <= 180.0:
                        return parsed_lat, parsed_lon, f"{parsed_lat:.4f}, {parsed_lon:.4f}"
                except ValueError:
                    pass

            try:
                lat, lon, resolved_label = geocode_location(value)
            except LocationLookupError as error:
                QMessageBox.warning(
                    dialog,
                    "Location lookup failed",
                    f"Could not resolve location '{value}'.\n{error}",
                )
                return None
            return float(lat), float(lon), resolved_label

        def _on_update_chart() -> None:
            resolved_location = _resolve_popout_location(popout_location_input.text())
            if resolved_location is None:
                return
            lat, lon, location_label = resolved_location

            local_tz = self._host.transit_panel_controller.display_timezone
            selected_date = popout_date_input.date()
            selected_time = popout_time_input.time()
            selected_local = datetime.datetime(
                selected_date.year(),
                selected_date.month(),
                selected_date.day(),
                selected_time.hour(),
                selected_time.minute(),
                tzinfo=local_tz,
            )
            selected_utc = selected_local.astimezone(datetime.timezone.utc)

            updated_chart = Chart(
                "🌍Transit View",
                selected_utc,
                lat,
                lon,
                tz=datetime.timezone.utc,
            )
            updated_chart.birthtime_unknown = False
            updated_chart.retcon_time_used = False

            state["chart"] = updated_chart
            state["location_label"] = location_label
            state["raw_location"] = popout_location_input.text().strip() or location_label
            state["time_label"] = updated_chart.dt.strftime("%H:%M") if updated_chart.dt else "unknown"
            state["date_label"] = updated_chart.dt.strftime("%m.%d.%Y") if updated_chart.dt else "??.??.????"

            _redraw()

        summary_sort_combo.currentTextChanged.connect(lambda _text: _refresh_summary())
        update_button.clicked.connect(_on_update_chart)
        _redraw()

        dialog.resize(1320, 1080)
        self._host._register_popout_shortcuts(dialog)

        dialog.show()
        self._dialogs.append(dialog)
        self._chart_by_dialog[dialog] = chart
        dialog.destroyed.connect(
            lambda _=None, dialog=dialog: self._dialogs.remove(dialog)
            if dialog in self._dialogs
            else None
        )
        dialog.destroyed.connect(
            lambda _=None, dialog=dialog: self._chart_by_dialog.pop(dialog, None)
        )
