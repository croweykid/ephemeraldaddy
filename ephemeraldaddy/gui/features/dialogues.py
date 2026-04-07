"""Shared dialog classes extracted from the legacy app module."""

import datetime
import html

from PySide6.QtCore import QDate, QThread, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.core.interpretations import (
    EPHEMERIS_MAX_DATE,
    EPHEMERIS_MIN_DATE,
    FAMILIARITY_INDEX,
    ZODIAC_NAMES,
    max_familiarity_score,
    normalized_familiarity_score,
)
from ephemeraldaddy.core.retcon import RETCON_BODIES
from ephemeraldaddy.core.timeutils import localize_naive_datetime
from ephemeraldaddy.gui.features.retcon.workers import RetconSearchWorker
from ephemeraldaddy.io.geocode import LocationLookupError, geocode_location
from ephemeraldaddy.gui.style import MIDDLE_PANEL_ACCENT_COLOR


def _format_longitude(lon: float) -> str:
    lon = lon % 360.0
    deg = int(lon)
    minutes = int(round((lon - deg) * 60))
    if minutes == 60:
        deg += 1
        minutes = 0
    deg %= 360
    return f"{deg:03d}°{minutes:02d}'"


class RetconEngineDialog(QDialog):
    _DEFINED_POSITION_STYLE = (
        "QComboBox {"
        f"background-color: {MIDDLE_PANEL_ACCENT_COLOR};"
        "color: #111111;"
        "border: 1px solid #555555;"
        "padding: 2px 6px;"
        "}"
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ephemeral Daddy: Astro App | Retcon Engine")
        self.setWindowFlag(Qt.Window, True)
        self.resize(780, 720)

        self._thread: QThread | None = None
        self._worker: RetconSearchWorker | None = None
        self._active_location_label = ""
        self._active_lat: float | None = None
        self._active_lon: float | None = None
        self._active_matches: list[dict] = []
        self._active_criteria: dict[str, str] = {}

        root = QVBoxLayout()
        self.setLayout(root)

        form = QFormLayout()
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        top_row.addWidget(QLabel("Location"))
        self.place_edit = QLineEdit()
        self.place_edit.setPlaceholderText("Chicago, IL, USA")
        self.place_edit.setMinimumWidth(460)
        top_row.addWidget(self.place_edit, 2)

        top_row.addWidget(QLabel("Date range"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDateRange(
            QDate(EPHEMERIS_MIN_DATE.year, EPHEMERIS_MIN_DATE.month, EPHEMERIS_MIN_DATE.day),
            QDate(EPHEMERIS_MAX_DATE.year, EPHEMERIS_MAX_DATE.month, EPHEMERIS_MAX_DATE.day),
        )
        self.start_date_edit.setDate(QDate(EPHEMERIS_MIN_DATE.year, EPHEMERIS_MIN_DATE.month, EPHEMERIS_MIN_DATE.day))
        top_row.addWidget(self.start_date_edit)
        top_row.addWidget(QLabel("to"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDateRange(
            QDate(EPHEMERIS_MIN_DATE.year, EPHEMERIS_MIN_DATE.month, EPHEMERIS_MIN_DATE.day),
            QDate(EPHEMERIS_MAX_DATE.year, EPHEMERIS_MAX_DATE.month, EPHEMERIS_MAX_DATE.day),
        )
        self.end_date_edit.setDate(QDate.currentDate())
        top_row.addWidget(self.end_date_edit)
        top_row.addStretch(1)
        form.addRow(top_row)

        options_row = QHBoxLayout()
        self.step_combo = QComboBox()
        step_options = [
            ("1 min", 1),
            ("5 min", 5),
            ("10 min", 10),
            ("20 min", 20),
            ("60 min", 60),
            ("4 hrs", 240),
            ("12 hrs", 720),
            ("1 day", 1440),
        ]
        for label, minutes in step_options:
            self.step_combo.addItem(label, minutes)
        self.step_combo.setCurrentText("1 day")
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(1, 10000)
        self.max_results_spin.setValue(100)
        options_row.addWidget(QLabel("Step (minutes)"))
        options_row.addWidget(self.step_combo)
        step_hint_label = QLabel("ⓘ")
        step_hint_label.setToolTip(
            '<i>Hint: Start with large steps and large spans of time; '
            "then narrow search field with successive passes.</i>"
        )
        step_hint_label.setCursor(Qt.PointingHandCursor)
        options_row.addWidget(step_hint_label)
        options_row.addSpacing(12)
        options_row.addWidget(QLabel("Max results"))
        options_row.addWidget(self.max_results_spin)
        options_row.addStretch(1)
        form.addRow("Search options", options_row)

        root.addLayout(form)

        selectors_group = QGroupBox("Sign criteria")
        selectors_layout = QGridLayout()
        selectors_layout.setHorizontalSpacing(10)
        self._body_sign_combos: dict[str, QComboBox] = {}
        sign_options = ["Any", *ZODIAC_NAMES]
        for idx, body in enumerate(RETCON_BODIES):
            label = QLabel(body)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            label.setStyleSheet("QLabel { background: transparent; padding-right: 6px; }")
            combo = QComboBox()
            combo.addItems(sign_options)
            combo.setCurrentText("Any")
            combo.currentTextChanged.connect(self._update_defined_position_styles)
            row = idx // 2
            col = (idx % 2) * 2
            selectors_layout.addWidget(label, row, col)
            selectors_layout.addWidget(combo, row, col + 1)
            self._body_sign_combos[body] = combo
        selectors_group.setLayout(selectors_layout)

        selectors_scroll = QScrollArea()
        selectors_scroll.setWidgetResizable(True)
        selectors_scroll.setWidget(selectors_group)
        selectors_scroll.setMinimumHeight(360)
        root.addWidget(selectors_scroll, 1)

        controls_row = QHBoxLayout()
        controls_row.addStretch(1)
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self._on_submit)
        controls_row.addWidget(self.submit_button, 0, Qt.AlignRight)
        self.cancel_button = QPushButton("Cancel search")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel)
        controls_row.addWidget(self.cancel_button, 0, Qt.AlignRight)
        root.addLayout(controls_row)

        self.status_label = QLabel("Ready.")
        root.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)

        self.results_output = QTextEdit()
        self.results_output.setReadOnly(True)
        self.results_output.setPlaceholderText(
            "Retcon matches will appear here after you press Submit."
        )
        root.addWidget(self.results_output, 1)

        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(lambda _item: self._open_selected_match())
        root.addWidget(self.results_list, 1)

        create_row = QHBoxLayout()
        self.create_chart_button = QPushButton("Create Chart from Selected Match")
        self.create_chart_button.setEnabled(False)
        self.create_chart_button.clicked.connect(self._open_selected_match)
        create_row.addWidget(self.create_chart_button, 0, Qt.AlignLeft)
        create_row.addStretch(1)
        root.addLayout(create_row)

        self._update_defined_position_styles()

    def _update_defined_position_styles(self, *_args) -> None:
        for combo in self._body_sign_combos.values():
            is_defined = combo.currentText() != "Any"
            combo.setStyleSheet(self._DEFINED_POSITION_STYLE if is_defined else "")

    def _criteria(self) -> dict[str, str]:
        criteria: dict[str, str] = {}
        for body, combo in self._body_sign_combos.items():
            sign = combo.currentText()
            if sign != "Any":
                criteria[body] = sign
        return criteria

    def _on_submit(self) -> None:
        criteria = self._criteria()
        if not criteria:
            QMessageBox.information(
                self,
                "Retcon Engine",
                "Pick at least one body/sign criterion before running search.",
            )
            return

        place = self.place_edit.text().strip() or "Chicago, IL, USA"
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
        start_naive = datetime.datetime(start_date.year(), start_date.month(), start_date.day(), 0, 0)
        end_naive = datetime.datetime(end_date.year(), end_date.month(), end_date.day(), 23, 59)

        start_dt, _ = localize_naive_datetime(start_naive, lat, lon)
        end_dt, _ = localize_naive_datetime(end_naive, lat, lon)
        if end_dt < start_dt:
            QMessageBox.warning(
                self,
                "Retcon Engine",
                "End date must be on or after start date.",
            )
            return

        step_minutes = int(self.step_combo.currentData() or 1440)
        max_results = self.max_results_spin.value()

        self._active_location_label = label
        self._active_lat = lat
        self._active_lon = lon
        self._active_matches = []
        self._active_criteria = dict(criteria)
        self.results_list.clear()
        self.create_chart_button.setEnabled(False)

        self.submit_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Scanning ephemeris in background…")
        #self.results_output.setPlainText("Search running in background. You can continue using other windows.")
        self.results_output.setHtml(self._build_results_html([], is_final=False))

        self._thread = QThread(self)
        self._worker = RetconSearchWorker(
            criteria,
            start_dt,
            end_dt,
            lat,
            lon,
            step_minutes,
            max_results,
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
        body_text = ", ".join(f"{body} {_format_longitude(positions[body])}" for body in sorted(positions))
        return f"{idx:03d}. {match_dt.strftime('%Y-%m-%d %H:%M %Z')} — {body_text}"

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
            "",
        ]
        for idx, match in enumerate(matches, 1):
            line = html.escape(self._format_match_line(idx, match))
            lines.append(line if is_final else f"<i>{line}</i>")

        if is_final and not matches:
            lines.append(html.escape("No matches found in that range. Try wider dates or fewer constraints."))

        return "<br>".join(lines)

    def _on_match_found(self, match: dict[str, object]) -> None:
        self._active_matches.append(match)
        line = self._format_match_line(len(self._active_matches), match)
        self.results_list.addItem(line)
        self.results_output.setHtml(self._build_results_html(self._active_matches, is_final=False))
        self.create_chart_button.setEnabled(bool(self._active_matches))

    def _cleanup_worker(self) -> None:
        self._thread = None
        self._worker = None

    def _on_failed(self, error_message: str) -> None:
        self.submit_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Search failed.")
        QMessageBox.critical(self, "Retcon Engine error", f"Search failed:\n{error_message}")

    def _on_finished(self, matches: list[dict]) -> None:
        self.submit_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        if self._worker is not None and self._worker.is_cancelled():
            self.status_label.setText("Search canceled.")
            self.progress_bar.setValue(0)
            self.progress_bar.setValue(100)
        self.status_label.setText(f"Search complete: {len(matches)} match(es).")

        self._active_matches = matches
        self.results_list.clear()
        for idx, match in enumerate(matches, 1):
            line = self._format_match_line(idx, match)
            self.results_list.addItem(line)
        self.create_chart_button.setEnabled(bool(matches))
        self.results_output.setHtml(self._build_results_html(matches, is_final=True))

    def _open_selected_match(self) -> None:
        row = self.results_list.currentRow()
        if row < 0 or row >= len(self._active_matches):
            return
        match = self._active_matches[row]
        parent = self.parent()
        if parent is None or not hasattr(parent, "open_chart_from_retcon_match"):
            QMessageBox.warning(self, "Retcon Engine", "Unable to open the chart view.")
            return
        location_label = self._active_location_label or self.place_edit.text().strip() or "Chicago, IL, USA"
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
        return max(1, min(10, round(normalized_familiarity_score(self.selected_total()))))
