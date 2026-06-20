from __future__ import annotations

import datetime
import logging
from collections import OrderedDict
from typing import Any

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtCore import QDate, QEventLoop, Qt, QTime, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtPositioning import QGeoPositionInfoSource
from PySide6.QtWidgets import (
    QCheckBox,
    QCompleter,
    QDateEdit,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.composite import (
    PERSONAL_TRANSIT_MODE_DAILY_VIBE,
    PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
    assign_houses,
    compute_aspects,
    normalize_chart,
    personal_transit_rules_for_mode,
)
from ephemeraldaddy.core.db import (
    EPHEMERIS_MAX_DATE,
    EPHEMERIS_MIN_DATE,
    list_charts,
    load_chart,
)
from ephemeraldaddy.graphics.wheel_plot import draw_chart_wheel
from ephemeraldaddy.gui.features.charts.chart_data_output import (
    ChartDataTooltipOutput,
    apply_chart_data_highlighter,
)
from ephemeraldaddy.gui.features.charts.text_summary import format_compact_transit_chart_text
from ephemeraldaddy.gui.style import DATABASE_VIEW_PANEL_HEADER_STYLE, apply_popout_cursor
from ephemeraldaddy.io.geocode import LocationLookupError, geocode_location

logger = logging.getLogger(__name__)

TRANSIT_WINDOW_CACHE_LIMIT = 512


class TransitPanelController:
    """Owns the Manage Charts Transit View panel and its UI-facing state.

    The controller intentionally installs legacy attributes on the host dialog so
    existing event filters and popout code can continue to interoperate while the
    Transit View feature is moved out of ``app.py``.
    """

    def __init__(self, host: Any, *, get_popout_window_icon_path: Any | None = None) -> None:
        self.host = host
        self._get_popout_window_icon_path = get_popout_window_icon_path
        self._install_legacy_state()

    def _install_legacy_state(self) -> None:
        h = self.host
        h._transit_chart_canvases = {}
        h._transit_popout_dialogs = []
        h._transit_popout_chart_by_dialog = {}
        h._personal_transit_generation_in_progress = False
        h._transit_window_result_cache = OrderedDict()
        h._transit_window_metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "inflight_dedupes": 0,
            "completed_requests": 0,
        }
        h._transit_location_label = "0.0, 0.0"
        h._transit_lat = 0.0
        h._transit_lon = 0.0
        h._transit_location_source = "default"
        h._personal_transit_chart_lookup = {}

    def build_panel(self) -> QWidget:
        h = self.host
        panel = QWidget()
        panel.setMinimumWidth(260)
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)
        panel.setLayout(layout)

        title = QLabel("🌍Transit View")
        title.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
        layout.addWidget(title)

        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(6)

        h.transit_date_input = QDateEdit()
        h.transit_date_input.setDisplayFormat("yyyy-MM-dd")
        h.transit_date_input.setCalendarPopup(True)
        h.transit_date_input.setDateRange(
            QDate(EPHEMERIS_MIN_DATE.year, EPHEMERIS_MIN_DATE.month, EPHEMERIS_MIN_DATE.day),
            QDate(EPHEMERIS_MAX_DATE.year, EPHEMERIS_MAX_DATE.month, EPHEMERIS_MAX_DATE.day),
        )
        h.transit_date_input.setDate(QDate.currentDate())
        h.transit_date_input.dateChanged.connect(lambda _date: self.refresh_panel())
        controls_layout.addWidget(h.transit_date_input)

        h.transit_time_input = QTimeEdit()
        h.transit_time_input.setDisplayFormat("HH:mm")
        h.transit_time_input.setTime(QTime.currentTime())
        h.transit_time_input.timeChanged.connect(lambda _time: self.refresh_panel())
        controls_layout.addWidget(h.transit_time_input)

        layout.addLayout(controls_layout)

        location_layout = QHBoxLayout()
        location_layout.setContentsMargins(0, 0, 0, 0)
        location_layout.setSpacing(6)

        h.transit_location_input = QLineEdit()
        h.transit_location_input.setPlaceholderText("Location (city or lat,lon)")
        h.transit_location_input.installEventFilter(h)
        location_layout.addWidget(h.transit_location_input, 1)

        h.transit_location_button = QPushButton("Set")
        h.transit_location_button.clicked.connect(self.on_location_submitted)
        location_layout.addWidget(h.transit_location_button)

        layout.addLayout(location_layout)

        h.transit_location_label = QLabel("Location: 0.0, 0.0 (UTC)")
        h.transit_location_label.setStyleSheet("font-size: 11px; color: #a5a5a5; padding: 0 2px 4px 2px;")
        layout.addWidget(h.transit_location_label)

        personal_transit_controls_layout = QHBoxLayout()
        personal_transit_controls_layout.setContentsMargins(0, 0, 0, 0)
        personal_transit_controls_layout.setSpacing(6)

        h.personal_transit_chart_input = QLineEdit()
        h.personal_transit_chart_input.setPlaceholderText("Enter chart name here!")
        h.personal_transit_chart_input.returnPressed.connect(self.on_personal_transit_enter_pressed)
        personal_transit_controls_layout.addWidget(h.personal_transit_chart_input, 1)

        h.generate_personal_transit_button = QPushButton("Generate Personal Transit")
        h.generate_personal_transit_button.setStyleSheet(
            "QPushButton { background-color: #6f8f6f; color: #e9efe9; border: 1px solid #4f6850; border-radius: 4px; padding: 4px 10px;}"
            "QPushButton:hover { background-color: #789a77; }"
            "QPushButton:pressed { background-color: #5f7d5f; }"
        )
        h.generate_personal_transit_button.clicked.connect(self.on_personal_transit_generate_clicked)
        personal_transit_controls_layout.addWidget(h.generate_personal_transit_button)

        layout.addLayout(personal_transit_controls_layout)

        h.transit_use_time_checkbox = QCheckBox("Use exact time")
        h.transit_use_time_checkbox.setChecked(True)
        h.transit_use_time_checkbox.toggled.connect(self.on_use_time_toggled)
        layout.addWidget(h.transit_use_time_checkbox)

        self.refresh_personal_transit_chart_options()

        h.todays_transits_updated_label = QLabel("")
        h.todays_transits_updated_label.setWordWrap(True)
        h.todays_transits_updated_label.setStyleSheet("font-size: 11px; color: #a5a5a5; padding: 0 2px 4px 2px;")
        layout.addWidget(h.todays_transits_updated_label)

        h.todays_transits_chart_container = QWidget()
        h.todays_transits_chart_layout = QVBoxLayout()
        h.todays_transits_chart_layout.setContentsMargins(0, 0, 0, 0)
        h.todays_transits_chart_layout.setAlignment(Qt.AlignTop)
        h.todays_transits_chart_container.setLayout(h.todays_transits_chart_layout)
        layout.addWidget(h.todays_transits_chart_container)

        h.todays_transits_output = ChartDataTooltipOutput()
        h.todays_transits_output.setReadOnly(True)
        output_font = h.todays_transits_output.font()
        output_font.setPointSize(9)
        h.todays_transits_output.setFont(output_font)
        h.todays_transits_output.setTabStopDistance(6)
        apply_chart_data_highlighter(h.todays_transits_output)
        h.todays_transits_output.setPlaceholderText("Transit chart summary will appear here.")
        h.todays_transits_output.setMinimumHeight(140)
        h.todays_transits_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(h.todays_transits_output, 1)

        refresh_button = QPushButton("Refresh Transit View")
        refresh_button.clicked.connect(self.refresh_panel)
        layout.addWidget(refresh_button)
        return panel

    def apply_location(self, *, show_errors: bool = True) -> None:
        h = self.host
        raw_value = h.transit_location_input.text().strip()
        if not raw_value:
            self.refresh_panel(); return
        parsed_lat = parsed_lon = None
        if "," in raw_value:
            maybe_lat, maybe_lon = raw_value.split(",", 1)
            try:
                parsed_lat = float(maybe_lat.strip()); parsed_lon = float(maybe_lon.strip())
            except ValueError:
                parsed_lat = parsed_lon = None
        if parsed_lat is not None and parsed_lon is not None:
            if not (-90.0 <= parsed_lat <= 90.0 and -180.0 <= parsed_lon <= 180.0):
                if show_errors:
                    QMessageBox.warning(h, "Invalid coordinates", "Latitude must be between -90 and 90, and longitude between -180 and 180.")
                return
            h._transit_lat = parsed_lat; h._transit_lon = parsed_lon
            h._transit_location_label = f"{parsed_lat:.4f}, {parsed_lon:.4f}"
            h._transit_location_source = "manual"
            self.save_location_preference(raw_value); self.refresh_panel(); return
        try:
            lat, lon, resolved_label = geocode_location(raw_value)
        except LocationLookupError as error:
            if show_errors:
                QMessageBox.warning(h, "Location lookup failed", f"Could not resolve location '{raw_value}'.\n{error}")
            return
        h._transit_lat = float(lat); h._transit_lon = float(lon)
        h._transit_location_label = resolved_label; h._transit_location_source = "manual"
        self.save_location_preference(raw_value); self.refresh_panel()

    def on_location_submitted(self, *_args: object) -> None:
        self.apply_location()

    def initialize_location_defaults(self) -> None:
        h = self.host
        gps_location = self.resolve_gps_location()
        if gps_location is not None:
            h._transit_lat, h._transit_lon = gps_location
            h._transit_location_label = "Current Location (GPS)"
            h._transit_location_source = "gps"
            return
        stored_location = h._settings.value("manage_charts/transit_last_location")
        if isinstance(stored_location, str) and stored_location.strip():
            h.transit_location_input.setText(stored_location.strip())
            self.apply_location(show_errors=False)

    def save_location_preference(self, raw_location: str) -> None:
        self.host._settings.setValue("manage_charts/transit_last_location", raw_location.strip())

    def resolve_gps_location(self) -> tuple[float, float] | None:
        h = self.host
        source = QGeoPositionInfoSource.createDefaultSource(h)
        if source is None: return None
        loop = QEventLoop(h); result: dict[str, float] = {}
        def _capture_position(info) -> None:
            if info.isValid():
                coordinate = info.coordinate()
                if coordinate.isValid():
                    result["lat"] = float(coordinate.latitude()); result["lon"] = float(coordinate.longitude())
            if loop.isRunning(): loop.quit()
        def _stop_waiting(*_args) -> None:
            if loop.isRunning(): loop.quit()
        source.positionUpdated.connect(_capture_position); source.errorOccurred.connect(_stop_waiting); source.startUpdates()
        timeout_timer = QTimer(h); timeout_timer.setSingleShot(True); timeout_timer.timeout.connect(_stop_waiting); timeout_timer.start(2500)
        loop.exec(); source.stopUpdates(); timeout_timer.stop()
        if "lat" not in result or "lon" not in result: return None
        return result["lat"], result["lon"]

    def refresh_panel(self) -> None:
        h = self.host
        if not hasattr(h, "todays_transits_chart_layout"): return
        h._clear_layout(h.todays_transits_chart_layout); h._transit_chart_canvases.clear()
        selected_utc, include_time = self.selected_datetime_utc()
        chart = Chart("🌍Transit View", selected_utc, h._transit_lat, h._transit_lon, tz=datetime.timezone.utc)
        chart.birth_place = h._transit_location_label; chart.birthtime_unknown = not include_time; chart.retcon_time_used = False
        figure = Figure(figsize=(3.8, 3.8)); canvas = FigureCanvas(figure)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding); apply_popout_cursor(canvas)
        draw_chart_wheel(figure, chart, canvas=canvas, wheel_padding=0.03, show_title=False, symbol_scale=0.7, wheel_scale=1.3)
        canvas.draw_idle(); canvas.setMinimumSize(230, 230)
        chart_click_container = QWidget(); chart_click_layout = QGridLayout(); chart_click_layout.setContentsMargins(0,0,0,0); chart_click_layout.setSpacing(0)
        chart_click_container.setLayout(chart_click_layout); apply_popout_cursor(chart_click_container); chart_click_layout.addWidget(canvas,0,0)
        popout_hint = QLabel(chart_click_container); popout_hint.setAttribute(Qt.WA_TransparentForMouseEvents, True); popout_hint.setStyleSheet("background: transparent;")
        popout_icon_path = (
            self._get_popout_window_icon_path()
            if self._get_popout_window_icon_path is not None
            else None
        )
        if popout_icon_path:
            popout_pixmap = QPixmap(popout_icon_path)
            if not popout_pixmap.isNull():
                popout_hint.setPixmap(popout_pixmap.scaled(22,22,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        popout_hint.setToolTip("Open transit chart popout"); chart_click_layout.addWidget(popout_hint,0,0,Qt.AlignTop | Qt.AlignRight)
        canvas.installEventFilter(h); chart_click_container.installEventFilter(h)
        h._transit_chart_canvases[canvas] = chart; h._transit_chart_canvases[chart_click_container] = chart
        h.todays_transits_chart_layout.addWidget(chart_click_container)
        summary, tooltip_spans = format_compact_transit_chart_text(chart, h._transit_location_label)
        h.todays_transits_output.setPlainText(summary); h.todays_transits_output.set_tooltip_spans(tooltip_spans)
        local_tz = datetime.datetime.now().astimezone().tzinfo or datetime.timezone.utc
        local_now = selected_utc.astimezone(local_tz)
        source_hint = " [GPS]" if h._transit_location_source == "gps" else " [Saved]" if h._transit_location_source == "manual" else ""
        h.transit_location_label.setText(f"Location: {h._transit_location_label}{source_hint} | Lat/Lon: {h._transit_lat:.4f}, {h._transit_lon:.4f}")
        if include_time:
            h.todays_transits_updated_label.setText(f"Selected local time: {local_now.strftime('%Y-%m-%d %H:%M %Z')}")
        else:
            h.todays_transits_updated_label.setText(f"Selected date (time omitted): {local_now.strftime('%Y-%m-%d')}")

    def refresh_personal_transit_chart_options(self) -> None:
        h = self.host; h._personal_transit_chart_lookup = {}; choices: list[str] = []
        for row in list_charts():
            chart_id, name, alias, *_rest = row
            display_name = name.strip() if isinstance(name, str) and name.strip() else f"Chart {chart_id}"
            if alias: display_name = f"{display_name} ({alias})"
            key = f"{display_name}  [#{chart_id}]"; h._personal_transit_chart_lookup[key] = int(chart_id); choices.append(key)
        completer = QCompleter(choices, h.personal_transit_chart_input)
        completer.setCaseSensitivity(Qt.CaseInsensitive); completer.setFilterMode(Qt.MatchContains)
        completer.activated[str].connect(self.on_personal_transit_completer_activated)
        h.personal_transit_chart_input.setCompleter(completer)

    def on_use_time_toggled(self, use_time: bool) -> None:
        self.host.transit_time_input.setEnabled(use_time); self.refresh_panel()

    def selected_datetime_utc(self) -> tuple[datetime.datetime, bool]:
        h = self.host; local_tz = datetime.datetime.now().astimezone().tzinfo or datetime.timezone.utc
        include_time = h.transit_use_time_checkbox.isChecked()
        selected_date = h.transit_date_input.date(); selected_time = h.transit_time_input.time() if include_time else QTime(12, 0)
        selected_local = datetime.datetime(selected_date.year(), selected_date.month(), selected_date.day(), selected_time.hour(), selected_time.minute(), tzinfo=local_tz)
        return selected_local.astimezone(datetime.timezone.utc), include_time

    def resolve_personal_transit_chart_id(self) -> int | None:
        h = self.host; raw = h.personal_transit_chart_input.text().strip()
        if not raw: return None
        chart_id = h._personal_transit_chart_lookup.get(raw)
        if chart_id is not None: return chart_id
        for label, candidate_id in h._personal_transit_chart_lookup.items():
            if raw.lower() == label.lower(): return candidate_id
        return None

    def matching_personal_transit_labels(self, raw: str) -> list[str]:
        labels = list(self.host._personal_transit_chart_lookup.keys()); query = raw.strip().lower()
        return labels if not query else [label for label in labels if query in label.lower()]

    def on_personal_transit_completer_activated(self, label: str) -> None:
        selected_label = label.strip()
        if not selected_label: return
        h = self.host; h.personal_transit_chart_input.setText(selected_label); h.personal_transit_chart_input.setCursorPosition(len(selected_label))

    def on_personal_transit_generate_clicked(self, *_args: object) -> None:
        self.on_personal_transit_enter_pressed()

    def on_personal_transit_enter_pressed(self) -> None:
        h = self.host; raw = h.personal_transit_chart_input.text().strip(); chart_id = self.resolve_personal_transit_chart_id()
        if chart_id is not None:
            self.generate_personal_transit(); return
        matches = self.matching_personal_transit_labels(raw)
        if not matches:
            QMessageBox.warning(h, "Generate Personal Transit", "Select a saved chart from autocomplete before generating."); return
        first_match = matches[0]; h.personal_transit_chart_input.setText(first_match); h.personal_transit_chart_input.setCursorPosition(len(first_match))
        if len(matches) == 1: self.generate_personal_transit()

    def generate_personal_transit(self) -> None:
        h = self.host
        if h._personal_transit_generation_in_progress: return
        chart_id = self.resolve_personal_transit_chart_id()
        if chart_id is None:
            QMessageBox.warning(h, "Generate Personal Transit", "Select a saved chart from autocomplete before generating."); return
        try:
            natal_chart = load_chart(chart_id)
        except ValueError as exc:
            QMessageBox.warning(h, "Generate Personal Transit", str(exc)); return
        try:
            h._personal_transit_generation_in_progress = True
            transit_datetime_utc, include_time = self.selected_datetime_utc(); place_label = getattr(h, "_transit_location_label", "Unknown")
            timestamp_label = transit_datetime_utc.strftime("%Y-%m-%d %H:%M UTC") if include_time else transit_datetime_utc.strftime("%Y-%m-%d")
            transit_chart = Chart(f"Personal Transit Chart for {natal_chart.name} on {timestamp_label} @ {place_label}", transit_datetime_utc, h._transit_lat, h._transit_lon, tz=datetime.timezone.utc)
            transit_chart.birth_place = place_label; transit_chart.birthtime_unknown = not include_time; transit_chart.retcon_time_used = False
            natal_normalized = normalize_chart(natal_chart, chart_id=chart_id, chart_type="natal"); transit_normalized = normalize_chart(transit_chart, chart_type="transit")
            transit_in_natal = assign_houses(transit_normalized.bodies, natal_normalized.houses, layer="TRANSIT")
            natal_targets = assign_houses(natal_normalized.bodies, natal_normalized.houses, layer="NATAL")
            life_forecast_hits = compute_aspects(transit_in_natal.values(), natal_targets.values(), personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_LIFE_FORECAST))
            daily_vibe_hits = compute_aspects(transit_in_natal.values(), natal_targets.values(), personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_DAILY_VIBE))
            h._show_personal_transit_chart_popout(natal_chart, transit_chart, transit_in_natal, {PERSONAL_TRANSIT_MODE_LIFE_FORECAST: life_forecast_hits, PERSONAL_TRANSIT_MODE_DAILY_VIBE: daily_vibe_hits}, include_time=include_time)
        except Exception as exc:
            logger.exception("Failed to generate personal transit for chart_id=%s", chart_id)
            QMessageBox.critical(h, "Generate Personal Transit", f"Failed to generate personal transit chart.\n\n{exc}")
        finally:
            h._personal_transit_generation_in_progress = False
