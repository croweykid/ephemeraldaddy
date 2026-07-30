"""Shared dialog classes extracted from the legacy app module."""

# Includes Rectification

import datetime
import html
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QDate, QThread, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.core.interpretations import (
    EPHEMERIS_MAX_DATE,
    EPHEMERIS_MIN_DATE,
    FAMILIARITY_INDEX,
    PLANET_COLORS,
    ZODIAC_NAMES,
    max_familiarity_score,
    normalized_familiarity_score,
)
from ephemeraldaddy.core.retcon import RETCON_BODIES, RETCON_CRITERIA_BODIES
from ephemeraldaddy.core.timeutils import localize_naive_datetime
from ephemeraldaddy.gui.features.retcon.workers import RetconSearchWorker
from ephemeraldaddy.io.geocode import LocationLookupError, geocode_location
from ephemeraldaddy.gui.style import (
    apply_chart_info_link_cursor,
    apply_loud_selection_dropdown_menu,
    apply_shared_dropdown_style,
    configure_share_export_icon_button,
)


def _format_longitude(lon: float) -> str:
    lon = lon % 360.0
    deg = int(lon)
    minutes = int(round((lon - deg) * 60))
    if minutes == 60:
        deg += 1
        minutes = 0
    deg %= 360
    return f"{deg:03d}°{minutes:02d}'"


def _get_share_icon_path() -> str | None:
    module_root = Path(__file__).resolve().parents[2]
    icon_path = module_root / "graphics" / "share_icon2.png"
    if icon_path.exists():
        return str(icon_path)
    return None


class RectificationView(Enum):
    """The three formally supported visual states of Rectification Engine."""

    CRITERIA = "criteria"
    RESULTS = "results"
    REFINEMENT = "refinement"


class RetconEngineDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ephemeral Daddy: Astro App | Rectification Engine")
        self.setWindowFlag(Qt.Window, True)
        self.resize(780, 720)

        self._thread: QThread | None = None
        self._worker: RetconSearchWorker | None = None
        self._active_location_label = ""
        self._active_lat: float | None = None
        self._active_lon: float | None = None
        self._active_matches: list[dict] = []
        self._active_criteria: dict[str, str] = {}
        self._active_start_dt: datetime.datetime | None = None
        self._active_end_dt: datetime.datetime | None = None
        self._view = RectificationView.CRITERIA

        root = QVBoxLayout(self)

        def _make_bold_label(text: str) -> QLabel:
            label = QLabel(text)
            bold_font = QFont(label.font())
            bold_font.setBold(True)
            label.setFont(bold_font)
            return label

        # Criteria and Refinement share a panel; Results has its own page. The
        # explicit state distinguishes all three supported visual views.
        self.view_stack = QStackedWidget()
        root.addWidget(self.view_stack)

        self.criteria_panel = QGroupBox("Criteria Input")
        criteria_panel_layout = QVBoxLayout(self.criteria_panel)

        # Spacetime Criteria subpanel: location, date/time ranges, and search options.
        spacetime_group = QGroupBox("Spacetime Criteria")
        spacetime_layout = QVBoxLayout(spacetime_group)
        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        top_row.addWidget(_make_bold_label("Location"))
        self.place_edit = QLineEdit()
        self.place_edit.setPlaceholderText("Chicago, IL, USA")
        top_row.addWidget(self.place_edit, 2)
        top_row.addWidget(_make_bold_label("Date Range"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDateRange(
            QDate(
                EPHEMERIS_MIN_DATE.year,
                EPHEMERIS_MIN_DATE.month,
                EPHEMERIS_MIN_DATE.day,
            ),
            QDate(
                EPHEMERIS_MAX_DATE.year,
                EPHEMERIS_MAX_DATE.month,
                EPHEMERIS_MAX_DATE.day,
            ),
        )
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDateRange(
            QDate(
                EPHEMERIS_MIN_DATE.year,
                EPHEMERIS_MIN_DATE.month,
                EPHEMERIS_MIN_DATE.day,
            ),
            QDate(
                EPHEMERIS_MAX_DATE.year,
                EPHEMERIS_MAX_DATE.month,
                EPHEMERIS_MAX_DATE.day,
            ),
        )
        top_row.addWidget(self.start_date_edit)
        top_row.addWidget(QLabel("to"))
        top_row.addWidget(self.end_date_edit)
        spacetime_layout.addLayout(top_row)

        # Search Options stays left while Time Range is right-justified on this row.
        options_time_row = QHBoxLayout()
        options_time_row.setSpacing(10)
        options_time_row.addWidget(_make_bold_label("Search Options"))
        options_time_row.addWidget(QLabel("Step"))
        self.step_combo = QComboBox()
        for label, minutes in [("12 hrs", 720), ("1 day", 1440)]:
            self.step_combo.addItem(label, minutes)
        apply_shared_dropdown_style(self.step_combo)
        options_time_row.addWidget(self.step_combo)
        step_hint_label = QLabel("ⓘ")
        step_hint_label.setToolTip(
            "<i>Hint: Start with large steps and large spans of time; "
            "then narrow search field with successive passes.</i>"
        )
        apply_chart_info_link_cursor(step_hint_label)
        options_time_row.addWidget(step_hint_label)
        options_time_row.addWidget(QLabel("Max Results"))
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(1, 10000)
        options_time_row.addWidget(self.max_results_spin)
        options_time_row.addStretch(1)
        options_time_row.addWidget(_make_bold_label("Time Range"))
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat("HH:mm")
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setDisplayFormat("HH:mm")
        options_time_row.addWidget(self.start_time_edit)
        options_time_row.addWidget(QLabel("to"))
        options_time_row.addWidget(self.end_time_edit)
        spacetime_layout.addLayout(options_time_row)
        criteria_panel_layout.addWidget(spacetime_group)

        # Position Criteria subpanel: three columns keep every criterion above the fold.
        position_group = QGroupBox("Position Criteria")
        self._position_layout = QGridLayout(position_group)
        self._position_layout.setHorizontalSpacing(10)
        self._body_sign_combos: dict[str, QComboBox] = {}
        self._body_house_combos: dict[str, QComboBox] = {}
        self._refinement_widgets: list[QWidget] = []
        self._angle_widgets: dict[str, list[QWidget]] = {}
        self._rows_per_position_column = (len(RETCON_BODIES) + 2) // 3
        for column in range(3):
            header = QLabel("H")
            header.setAlignment(Qt.AlignCenter)
            header.setMaximumHeight(header.fontMetrics().height())
            self._position_layout.addWidget(header, 0, column * 3 + 2)
            self._refinement_widgets.append(header)
        for idx, body in enumerate(RETCON_CRITERIA_BODIES):
            self._add_position_criterion(body, idx)
        criteria_panel_layout.addWidget(position_group, 1)

        # Criteria Input Panel button menu.
        criteria_buttons = QHBoxLayout()
        criteria_buttons.addStretch(1)
        self.reset_button = QPushButton("Reset Criteria")
        self.reset_button.clicked.connect(self._reset_criteria)
        criteria_buttons.addWidget(self.reset_button)
        self.submit_button = QPushButton("Submit")
        self.submit_button.setDefault(True)
        self.submit_button.clicked.connect(self._on_submit)
        criteria_buttons.addWidget(self.submit_button)
        criteria_panel_layout.addLayout(criteria_buttons)
        self.view_stack.addWidget(self.criteria_panel)

        search_page = QWidget()
        search_page_layout = QVBoxLayout(search_page)

        # Search Summary panel records the submitted spacetime and position criteria.
        self.summary_group = QGroupBox("Search Summary")
        summary_layout = QVBoxLayout(self.summary_group)
        self.results_output = QTextEdit()
        self.results_output.setReadOnly(True)
        summary_layout.addWidget(self.results_output)
        summary_buttons = QHBoxLayout()
        self.export_button = QPushButton()
        configure_share_export_icon_button(
            self.export_button,
            share_icon_path=_get_share_icon_path(),
            tooltip="Export Rectification results as TXT or Markdown",
        )
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._on_export_results)
        summary_buttons.addWidget(self.export_button)
        summary_buttons.addStretch(1)
        self.edit_criteria_button = QPushButton("Edit Criteria")
        self.edit_criteria_button.clicked.connect(self._show_criteria_panel)
        summary_buttons.addWidget(self.edit_criteria_button)
        self.refine_houses_button = QPushButton("Refine by House Placement")
        self.refine_houses_button.clicked.connect(self._show_refinement_panel)
        summary_buttons.addWidget(self.refine_houses_button)
        summary_layout.addLayout(summary_buttons)
        search_page_layout.addWidget(self.summary_group)

        # Search Results panel owns progress, cancellation, matches, and chart creation.
        self.results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout(self.results_group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        results_layout.addWidget(self.progress_bar)
        status_row = QHBoxLayout()
        self.status_label = QLabel("")
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        self.cancel_button = QPushButton("Cancel Search")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel)
        status_row.addWidget(self.cancel_button)
        results_layout.addLayout(status_row)
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(
            lambda _item: self._open_selected_match()
        )
        results_layout.addWidget(self.results_list, 1)
        create_row = QHBoxLayout()
        self.create_chart_button = QPushButton("Create Chart from Selected Match")
        self.create_chart_button.setEnabled(False)
        self.create_chart_button.clicked.connect(self._open_selected_match)
        create_row.addStretch(1)
        create_row.addWidget(self.create_chart_button)
        results_layout.addLayout(create_row)
        search_page_layout.addWidget(self.results_group, 1)
        self.view_stack.addWidget(search_page)

        self._reset_criteria()
        self._apply_view(RectificationView.CRITERIA)

    def _add_position_criterion(self, body: str, index: int) -> None:
        label = QLabel("Midhaven" if body == "MC" else body)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setStyleSheet(
            "QLabel { background: transparent; "
            f"color: {PLANET_COLORS.get(body, '#FFFFFF')}; padding-right: 6px; }}"
        )
        sign_combo = QComboBox()
        sign_combo.addItems(["Any", *ZODIAC_NAMES])
        apply_loud_selection_dropdown_menu(sign_combo)
        sign_combo.setMaxVisibleItems(len(ZODIAC_NAMES) + 1)
        sign_combo.setMaximumWidth(
            sign_combo.fontMetrics().horizontalAdvance("M" * 15) + 28
        )
        house_combo = QComboBox()
        house_combo.addItems(["Any", *[str(house) for house in range(1, 13)]])
        apply_loud_selection_dropdown_menu(house_combo)
        house_combo.setFixedWidth(
            house_combo.fontMetrics().horizontalAdvance("000") + 24
        )
        if body in {"Ascendant", "MC"}:
            house_combo.setCurrentText("1" if body == "Ascendant" else "10")
            house_combo.setEnabled(False)

        column = index // self._rows_per_position_column
        row = index % self._rows_per_position_column
        self._position_layout.addWidget(label, row + 1, column * 3)
        self._position_layout.addWidget(sign_combo, row + 1, column * 3 + 1)
        self._position_layout.addWidget(house_combo, row + 1, column * 3 + 2)
        self._body_sign_combos[body] = sign_combo
        self._body_house_combos[body] = house_combo
        self._refinement_widgets.append(house_combo)
        if body in {"Ascendant", "MC"}:
            self._angle_widgets[body] = [label, sign_combo, house_combo]

    def _ensure_refinement_angle_widgets(self) -> None:
        for body in ("Ascendant", "MC"):
            if body not in self._angle_widgets:
                self._add_position_criterion(body, RETCON_BODIES.index(body))
                self._body_sign_combos[body].setCurrentText(
                    self._active_criteria.get(body, "Any")
                )

    def _remove_refinement_angle_widgets(self) -> None:
        for body, widgets in list(self._angle_widgets.items()):
            self._body_sign_combos.pop(body, None)
            self._body_house_combos.pop(body, None)
            for widget in widgets:
                if widget in self._refinement_widgets:
                    self._refinement_widgets.remove(widget)
                self._position_layout.removeWidget(widget)
                widget.deleteLater()
            del self._angle_widgets[body]

    def _reset_criteria(self) -> None:
        """Restore every Criteria Input Panel field to its initial value."""
        self.place_edit.clear()
        self.start_date_edit.setDate(
            QDate(
                EPHEMERIS_MIN_DATE.year,
                EPHEMERIS_MIN_DATE.month,
                EPHEMERIS_MIN_DATE.day,
            )
        )
        self.end_date_edit.setDate(QDate.currentDate())
        self.start_time_edit.setTime(datetime.time(0, 0))
        self.end_time_edit.setTime(datetime.time(23, 59))
        self.step_combo.setCurrentText("12 hrs")
        self.max_results_spin.setValue(100)
        for combo in self._body_sign_combos.values():
            combo.setCurrentText("Any")
        for body, combo in self._body_house_combos.items():
            combo.setCurrentText(
                "1" if body == "Ascendant" else "10" if body == "MC" else "Any"
            )
        self._active_matches = []
        self._active_criteria = {}
        self._apply_view(RectificationView.CRITERIA)

    def _show_criteria_panel(self) -> None:
        self._apply_view(RectificationView.CRITERIA)
        self.submit_button.setFocus()

    def _show_refinement_panel(self) -> None:
        if not self._active_matches:
            return
        self._apply_view(RectificationView.REFINEMENT)
        self.submit_button.setFocus()

    def _apply_view(self, view: RectificationView) -> None:
        previous_view = self._view
        if view is RectificationView.REFINEMENT:
            self._ensure_refinement_angle_widgets()
        elif view is RectificationView.CRITERIA:
            self._remove_refinement_angle_widgets()
        self._view = view
        self.view_stack.setCurrentIndex(1 if view is RectificationView.RESULTS else 0)
        refinement_visible = view is RectificationView.REFINEMENT
        self.place_edit.setEnabled(not refinement_visible)
        self.place_edit.setToolTip(
            "Location is fixed to the current result set during refinement."
            if refinement_visible
            else ""
        )
        for widget in self._refinement_widgets:
            widget.setVisible(refinement_visible)
        self.criteria_panel.setTitle(
            "Refine Criteria" if refinement_visible else "Criteria Input"
        )
        if view is RectificationView.REFINEMENT and previous_view is not view:
            self._set_step_options(
                [
                    ("30 min", 30),
                    ("15 min", 15),
                    ("10 min", 10),
                    ("5 min", 5),
                    ("1 min", 1),
                ]
            )
        elif view is RectificationView.CRITERIA and any(
            int(self.step_combo.itemData(index) or 0) < 720
            for index in range(self.step_combo.count())
        ):
            self._set_step_options([("12 hrs", 720), ("1 day", 1440)])

    def _set_step_options(self, options: list[tuple[str, int]]) -> None:
        self.step_combo.clear()
        for label, minutes in options:
            self.step_combo.addItem(label, minutes)

    def _criteria(self) -> dict[str, str]:
        criteria: dict[str, str] = {}
        for body, combo in self._body_sign_combos.items():
            sign = combo.currentText()
            if sign != "Any":
                criteria[body] = sign
        return criteria

    def _house_criteria(self) -> dict[str, int]:
        if self._view is not RectificationView.REFINEMENT:
            return {}
        return {
            body: int(combo.currentText())
            for body, combo in self._body_house_combos.items()
            if combo.currentText() != "Any"
        }

    def _on_submit(self) -> None:
        criteria = self._criteria()
        refining = self._view is RectificationView.REFINEMENT
        house_criteria = self._house_criteria()
        if not criteria:
            QMessageBox.information(
                self,
                "Rectification Engine",
                "Pick at least one body/sign criterion before running search.",
            )
            return

        place = self.place_edit.text().strip() or "Chicago, IL, USA"
        if refining and self._active_lat is not None and self._active_lon is not None:
            lat = self._active_lat
            lon = self._active_lon
            label = self._active_location_label or place
        else:
            try:
                lat, lon, label = geocode_location(place)
            except LocationLookupError:
                QMessageBox.warning(
                    self,
                    "Location not found",
                    "Could not geocode that location. Please try a more specific place.",
                )
                return

        if label and label != place:
            self.place_edit.setText(label)

        start_date = self.start_date_edit.date()
        end_date = self.end_date_edit.date()
        start_time = self.start_time_edit.time()
        end_time = self.end_time_edit.time()
        start_naive = datetime.datetime(
            start_date.year(),
            start_date.month(),
            start_date.day(),
            start_time.hour(),
            start_time.minute(),
        )
        end_naive = datetime.datetime(
            end_date.year(),
            end_date.month(),
            end_date.day(),
            end_time.hour(),
            end_time.minute(),
        )

        start_dt, _ = localize_naive_datetime(start_naive, lat, lon)
        end_dt, _ = localize_naive_datetime(end_naive, lat, lon)
        if end_dt < start_dt:
            QMessageBox.warning(
                self,
                "Rectification Engine",
                "End date/time must be on or after start date/time.",
            )
            return

        refinement_windows = None
        if refining:
            refinement_windows = []
            for match in self._active_matches:
                match_start = match.get("range_start", match.get("datetime"))
                match_end = match.get("range_end", match_start)
                if not isinstance(match_start, datetime.datetime) or not isinstance(
                    match_end, datetime.datetime
                ):
                    continue
                window_start = max(match_start, start_dt)
                window_end = min(match_end, end_dt)
                if window_start <= window_end:
                    refinement_windows.append((window_start, window_end))

        step_minutes = int(self.step_combo.currentData() or 720)
        max_results = self.max_results_spin.value()

        self._active_location_label = label
        self._active_lat = lat
        self._active_lon = lon
        self._active_matches = []
        self._active_criteria = dict(criteria)
        self._active_start_dt = start_dt
        self._active_end_dt = end_dt
        self.results_list.clear()
        self.create_chart_button.setEnabled(False)
        self.export_button.setEnabled(False)

        self.submit_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.edit_criteria_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Scanning ephemeris in background…")
        # self.results_output.setPlainText("Search running in background. You can continue using other windows.")
        self.results_output.setHtml(self._build_results_html([], is_final=False))
        self._apply_view(RectificationView.RESULTS)

        self._thread = QThread(self)
        self._worker = RetconSearchWorker(
            criteria,
            start_dt,
            end_dt,
            lat,
            lon,
            step_minutes,
            max_results,
            required_houses=house_criteria,
            candidate_windows=refinement_windows,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.match_found.connect(self._on_match_found)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._cleanup_worker)
        self._thread.start()

    def _on_cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.status_label.setText("Canceling search…")

    def _on_progress(self, index: int, total: int) -> None:
        if total <= 0:
            return
        pct = int((index / total) * 100)
        self.progress_bar.setValue(min(max(pct, 0), 100))

    def _format_match_line(self, idx: int, match: dict[str, object]) -> str:
        match_dt = match["datetime"]
        positions = match["positions"]
        body_text = ", ".join(
            f"{body} {_format_longitude(positions[body])}" for body in sorted(positions)
        )
        range_end = match.get("range_end")
        time_text = match_dt.strftime("%Y-%m-%d %H:%M %Z")
        if isinstance(range_end, datetime.datetime) and range_end > match_dt:
            time_text = f"{time_text} to {range_end.strftime('%Y-%m-%d %H:%M %Z')}"
        return f"{idx:03d}. {time_text} — {body_text}"

    def _build_results_html(self, matches: list[dict], *, is_final: bool) -> str:
        location_label = self._active_location_label or self.place_edit.text().strip()
        lat = self._active_lat
        lon = self._active_lon
        location_text = (
            f"Location: {location_label} ({lat:.4f}, {lon:.4f})"
            if lat is not None and lon is not None
            else f"Location: {location_label}"
        )
        criteria_text = ", ".join(
            f"{body} in {sign}" for body, sign in self._active_criteria.items()
        )

        lines = [
            html.escape(location_text),
            html.escape(f"Criteria: {criteria_text}"),
            html.escape(f"Matches: {len(matches)}"),
            # "",
        ]
        # for idx, match in enumerate(matches, 1):
        #     line = html.escape(self._format_match_line(idx, match))
        #     lines.append(line if is_final else f"<i>{line}</i>")

        if is_final and not matches:
            lines.append(
                html.escape(
                    "No matches found in that range. Try wider dates or fewer constraints."
                )
            )

        return "<br>".join(lines)

    def _on_match_found(self, match: dict[str, object]) -> None:
        self._active_matches.append(match)
        line = self._format_match_line(len(self._active_matches), match)
        self.results_list.addItem(line)
        self.results_output.setHtml(
            self._build_results_html(self._active_matches, is_final=False)
        )
        self.create_chart_button.setEnabled(bool(self._active_matches))

    def _cleanup_worker(self) -> None:
        self._thread = None
        self._worker = None

    def _on_failed(self, error_message: str) -> None:
        self.submit_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.edit_criteria_button.setEnabled(True)
        self.export_button.setEnabled(bool(self._active_matches))
        self.status_label.setText("Search failed.")
        QMessageBox.critical(
            self, "Rectification Engine error", f"Search failed:\n{error_message}"
        )

    def _on_finished(self, matches: list[dict]) -> None:
        self.submit_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.edit_criteria_button.setEnabled(True)

        if self._worker is not None and self._worker.is_cancelled():
            self.status_label.setText("Search canceled.")
            self.progress_bar.setValue(0)
        else:
            self.progress_bar.setValue(100)
            noun = "match" if len(matches) == 1 else "matches"
            self.status_label.setText(f"Search complete: {len(matches)} {noun}.")

        self._active_matches = matches
        self.results_list.clear()
        for idx, match in enumerate(matches, 1):
            line = self._format_match_line(idx, match)
            self.results_list.addItem(line)
        self.create_chart_button.setEnabled(bool(matches))
        self.export_button.setEnabled(bool(matches))
        self.results_output.setHtml(self._build_results_html(matches, is_final=True))

    def _export_payload(self) -> tuple[str, str]:
        location_label = (
            self._active_location_label or self.place_edit.text().strip() or "Unknown"
        )
        lat = self._active_lat
        lon = self._active_lon
        location_text = (
            f"{location_label} ({lat:.4f}, {lon:.4f})"
            if lat is not None and lon is not None
            else location_label
        )
        if self._active_start_dt is not None and self._active_end_dt is not None:
            range_text = (
                f"{self._active_start_dt.strftime('%Y-%m-%d %H:%M %Z')} "
                f"to {self._active_end_dt.strftime('%Y-%m-%d %H:%M %Z')}"
            )
        else:
            range_text = "Unknown"
        criteria_text = (
            ", ".join(
                f"{body} in {sign}" for body, sign in self._active_criteria.items()
            )
            or "None"
        )
        lines = [
            f"Location: {location_text}",
            f"Date & Time Range: {range_text}",
            f"Chart Criteria: {criteria_text}",
            f"Results Returned: {len(self._active_matches)}",
            "",
            "Results:",
        ]
        for idx, match in enumerate(self._active_matches, 1):
            lines.append(self._format_match_line(idx, match))
        txt_content = "\n".join(lines)

        md_lines = [
            "# Rectification Engine Search Export",
            "",
            f"- **Location:** {location_text}",
            f"- **Date & Time Range:** {range_text}",
            f"- **Chart Criteria:** {criteria_text}",
            f"- **Results Returned:** {len(self._active_matches)}",
            "",
            "## Results",
            "",
        ]
        for idx, match in enumerate(self._active_matches, 1):
            md_lines.append(f"{idx}. `{self._format_match_line(idx, match)}`")
        md_content = "\n".join(md_lines)
        return txt_content, md_content

    def _on_export_results(self) -> None:
        if not self._active_matches:
            QMessageBox.information(
                self,
                "Rectification Engine",
                "No completed search results are available to export yet.",
            )
            return
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Rectification Engine Search Results",
            "rectification-search-results.txt",
            "Text File (*.txt);;Markdown File (*.md)",
        )
        if not file_path:
            return
        txt_content, md_content = self._export_payload()
        use_markdown = "Markdown" in selected_filter or file_path.lower().endswith(
            ".md"
        )
        if use_markdown and not file_path.lower().endswith(".md"):
            file_path = f"{file_path}.md"
        if not use_markdown and not file_path.lower().endswith(".txt"):
            file_path = f"{file_path}.txt"
        payload = md_content if use_markdown else txt_content
        with open(file_path, "w", encoding="utf-8") as export_file:
            export_file.write(payload)
        QMessageBox.information(
            self, "Rectification Engine", f"Exported search results to:\n{file_path}"
        )

    def _open_selected_match(self) -> None:
        row = self.results_list.currentRow()
        if row < 0 or row >= len(self._active_matches):
            return
        match = self._active_matches[row]
        parent = self.parent()
        if parent is None or not hasattr(parent, "open_chart_from_retcon_match"):
            QMessageBox.warning(
                self, "Rectification Engine", "Unable to open the Chart Editor."
            )
            return
        location_label = (
            self._active_location_label
            or self.place_edit.text().strip()
            or "Chicago, IL, USA"
        )
        lat = self._active_lat
        lon = self._active_lon
        parent.open_chart_from_retcon_match(match, location_label, lat, lon)


class FamiliarityCalculatorDialog(QDialog):
    def __init__(self, selected_labels: list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Familiarity Calculator")
        self.setModal(False)
        self._rows: list[tuple[str, int, QCheckBox]] = []

        layout = QVBoxLayout(self)
        helper = QLabel("Tick anything that applies. Score is auto-calculated (1-10).")
        helper.setWordWrap(True)
        layout.addWidget(helper)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        grid = QGridLayout(scroll_widget)
        grid.setContentsMargins(0, 0, 0, 0)

        selected_set = set(selected_labels)
        for row_index, item in enumerate(FAMILIARITY_INDEX):
            label, weight = list(item.items())[0]
            checkbox = QCheckBox(f"{label} (+{weight})")
            checkbox.setChecked(label in selected_set)
            grid.addWidget(checkbox, row_index, 0)
            self._rows.append((label, weight, checkbox))

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        self.total_label = QLabel()
        layout.addWidget(self.total_label)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.accept)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_row.addWidget(apply_button)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        self._update_total_label()

        for _, _, checkbox in self._rows:
            checkbox.toggled.connect(self._update_total_label)

    def _update_total_label(self):
        total = self.selected_total()
        max_total = max(1, max_familiarity_score(FAMILIARITY_INDEX))
        score = max(1, min(10, round(normalized_familiarity_score(total))))
        self.total_label.setText(
            f"Selected points: {total}/{max_total} → Familiarity score: {score}"
        )

    def selected_labels(self) -> list[str]:
        return [label for label, _, checkbox in self._rows if checkbox.isChecked()]

    def selected_total(self) -> int:
        return sum(weight for _, weight, checkbox in self._rows if checkbox.isChecked())

    def calculated_score(self) -> int:
        max_total = max(1, max_familiarity_score(FAMILIARITY_INDEX))
        return max(
            1, min(10, round(normalized_familiarity_score(self.selected_total())))
        )
