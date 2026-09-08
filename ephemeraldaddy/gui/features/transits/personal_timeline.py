from __future__ import annotations

import calendar
import datetime
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.core.composite import (
    BodyPosition,
    COMPOSITE_ASPECT_TYPES,
    PERSONAL_TRANSIT_MAX_ORB_DEG,
    PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
    angular_distance,
    personal_transit_rules_for_mode,
)
from ephemeraldaddy.core.db import get_current_chart_uid, load_chart_by_uid
from ephemeraldaddy.core.ephemeris import planetary_longitude
from ephemeraldaddy.core.interpretations import (
    ASTEROIDS,
    BLACK_MOON_LILITH,
    EPHEMERIS_MAX_DATE,
    EPHEMERIS_MIN_DATE,
    MAJOR_ASPECTS,
    NODES,
    OUTER_PLANETS,
    PERSONAL,
)

DEFAULT_TIMELINE_YEARS = 120
DEFAULT_SCAN_STEP_DAYS = 2
_BOUNDARY_REFINEMENT_STEPS = 14
_SUPPLEMENTAL_MAJOR_BODIES = frozenset({"Jupiter", "Saturn", "Chiron"})

_BODY_DISPLAY_ORDER = (
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "Rahu",
    "Ketu",
    "Chiron",
    "Ceres",
    "Pallas",
    "Juno",
    "Vesta",
    "Lilith",
)

_ASPECT_LABELS = {
    "conjunction": "conjunct",
    "semisextile": "semisextile",
    "semisquare": "semisquare",
    "sextile": "sextile",
    "quintile": "quintile",
    "square": "square",
    "trine": "trine",
    "sesquiquadrate": "sesquiquadrate",
    "biquintile": "biquintile",
    "quincunx": "quincunx",
    "opposition": "opposite",
}


@dataclass(frozen=True, slots=True)
class TimelineTransitDefinition:
    transiting_body: str
    natal_body: str
    natal_longitude: float
    aspect_name: str
    aspect_angle: float
    orb_deg: float

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.transiting_body, self.natal_body, self.aspect_name)

    @property
    def label(self) -> str:
        aspect = _ASPECT_LABELS.get(self.aspect_name, self.aspect_name)
        return f"{self.transiting_body} {aspect} natal {self.natal_body}"


@dataclass(frozen=True, slots=True)
class PersonalTimelineWindow:
    chart_uid: str
    transit: TimelineTransitDefinition
    start: datetime.datetime
    end: datetime.datetime
    start_truncated: bool = False
    end_truncated: bool = False

    @property
    def midpoint(self) -> datetime.datetime:
        return self.start + ((self.end - self.start) / 2)

    @property
    def duration_days(self) -> float:
        return max(0.0, (self.end - self.start).total_seconds() / 86400.0)


class PersonalTimelineSelectionError(ValueError):
    pass


def _timeline_transiting_bodies() -> tuple[str, ...]:
    life_forecast_bodies = (
        set(OUTER_PLANETS) | set(NODES) | set(ASTEROIDS) | set(BLACK_MOON_LILITH)
    )
    allowed = life_forecast_bodies | set(_SUPPLEMENTAL_MAJOR_BODIES)
    ordered = [body for body in _BODY_DISPLAY_ORDER if body in allowed]
    ordered.extend(sorted(allowed.difference(ordered)))
    return tuple(ordered)


def _supplemental_definition_allowed(
    transit_name: str,
    natal_name: str,
    aspect_angle: int,
) -> bool:
    """Add classic slow-cycle transits omitted by the existing Life Forecast set."""
    if transit_name not in _SUPPLEMENTAL_MAJOR_BODIES:
        return False
    if aspect_angle not in MAJOR_ASPECTS:
        return False
    if transit_name in {"Jupiter", "Saturn"}:
        return natal_name in PERSONAL or natal_name in OUTER_PLANETS
    if transit_name == "Chiron":
        return natal_name in PERSONAL or natal_name == "Chiron"
    return False


def _build_transit_definitions(chart: Any) -> tuple[TimelineTransitDefinition, ...]:
    positions = dict(getattr(chart, "positions", {}) or {})
    if not positions:
        return ()

    life_rules = personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_LIFE_FORECAST)
    definitions: dict[tuple[str, str, str], TimelineTransitDefinition] = {}

    for transit_name in _timeline_transiting_bodies():
        transit_probe = BodyPosition(name=transit_name, lon_deg=0.0, layer="TRANSIT")
        for natal_name_raw, natal_longitude_raw in positions.items():
            if natal_longitude_raw is None:
                continue
            try:
                natal_longitude = float(natal_longitude_raw) % 360.0
            except (TypeError, ValueError):
                continue

            natal_name = str(natal_name_raw)
            natal_probe = BodyPosition(
                name=natal_name,
                lon_deg=natal_longitude,
                layer="NATAL",
            )
            existing_pair_allowed = bool(
                life_rules.pair_filter is None
                or life_rules.pair_filter(transit_probe, natal_probe, life_rules.context)
            )

            for aspect in COMPOSITE_ASPECT_TYPES:
                allowed_orb = 0.0
                if existing_pair_allowed:
                    allowed_orb = (
                        life_rules.orb_table(
                            transit_probe,
                            natal_probe,
                            aspect,
                            life_rules.context,
                        )
                        if life_rules.orb_table
                        else aspect.orb_deg
                    )

                if allowed_orb <= 0 and _supplemental_definition_allowed(
                    transit_name,
                    natal_name,
                    int(aspect.angle_deg),
                ):
                    allowed_orb = min(
                        float(aspect.orb_deg),
                        PERSONAL_TRANSIT_MAX_ORB_DEG,
                    )

                if allowed_orb <= 0:
                    continue

                definition = TimelineTransitDefinition(
                    transiting_body=transit_name,
                    natal_body=natal_name,
                    natal_longitude=natal_longitude,
                    aspect_name=aspect.name,
                    aspect_angle=float(aspect.angle_deg),
                    orb_deg=float(allowed_orb),
                )
                definitions[definition.key] = definition

    return tuple(definitions.values())


def _aspect_orb(
    transit_longitude: float,
    definition: TimelineTransitDefinition,
) -> float:
    separation = angular_distance(transit_longitude, definition.natal_longitude)
    return abs(float(separation) - definition.aspect_angle)


def _definition_is_active(
    when: datetime.datetime,
    definition: TimelineTransitDefinition,
) -> bool:
    longitude = planetary_longitude(when, definition.transiting_body)
    return bool(
        longitude is not None
        and _aspect_orb(float(longitude), definition) <= definition.orb_deg
    )


def _refine_boundary(
    outside: datetime.datetime,
    inside: datetime.datetime,
    definition: TimelineTransitDefinition,
) -> datetime.datetime:
    """Refine an outside/inside transition to approximately minute precision."""
    left = outside
    right = inside
    left_active = _definition_is_active(left, definition)
    right_active = _definition_is_active(right, definition)
    if left_active == right_active:
        return inside

    for _ in range(_BOUNDARY_REFINEMENT_STEPS):
        middle = left + ((right - left) / 2)
        middle_active = _definition_is_active(middle, definition)
        if middle_active == left_active:
            left = middle
        else:
            right = middle
    return right if right_active else left


def _add_years_clamped(value: datetime.datetime, years: int) -> datetime.datetime:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(month=2, day=28, year=value.year + years)


def _ephemeris_boundary(
    date_value: datetime.date,
    tzinfo: datetime.tzinfo,
    *,
    end_of_day: bool,
) -> datetime.datetime:
    time_value = datetime.time(23, 59, 59, 999999) if end_of_day else datetime.time.min
    return datetime.datetime.combine(date_value, time_value, tzinfo=tzinfo)


def _known_death_datetime(
    chart: Any,
    tzinfo: datetime.tzinfo,
) -> datetime.datetime | None:
    if not bool(getattr(chart, "is_deceased", False)):
        return None

    try:
        year = int(getattr(chart, "death_year", None) or 0)
    except (TypeError, ValueError):
        return None
    if year <= 0:
        return None

    try:
        month = int(getattr(chart, "death_month", None) or 0)
    except (TypeError, ValueError):
        month = 0
    try:
        day = int(getattr(chart, "death_day", None) or 0)
    except (TypeError, ValueError):
        day = 0

    if not 1 <= month <= 12:
        month = 12
        day = 31
    elif not 1 <= day <= calendar.monthrange(year, month)[1]:
        day = calendar.monthrange(year, month)[1]

    try:
        return datetime.datetime(year, month, day, 23, 59, 59, tzinfo=tzinfo)
    except ValueError:
        return None


def _timeline_bounds(
    chart: Any,
    birth: datetime.datetime,
    years: int,
) -> tuple[datetime.datetime, datetime.datetime]:
    ephemeris_start = _ephemeris_boundary(
        EPHEMERIS_MIN_DATE,
        birth.tzinfo,
        end_of_day=False,
    )
    ephemeris_end = _ephemeris_boundary(
        EPHEMERIS_MAX_DATE,
        birth.tzinfo,
        end_of_day=True,
    )
    start = max(birth, ephemeris_start)
    end = min(_add_years_clamped(birth, years), ephemeris_end)
    death = _known_death_datetime(chart, birth.tzinfo)
    if death is not None and death > start:
        end = min(end, death)
    return start, end


def generate_personal_timeline(
    chart_uid: str,
    chart: Any,
    *,
    years: int = DEFAULT_TIMELINE_YEARS,
    step_days: int = DEFAULT_SCAN_STEP_DAYS,
    progress: Callable[[int, int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> list[PersonalTimelineWindow]:
    """Generate continuous major-life transit date ranges for one Chart UID.

    The existing Personal Transit Life Forecast rules are authoritative. Jupiter,
    Saturn and Chiron major aspects are added because those classic long-cycle
    transits are not in the current Life Forecast transiting-body set.
    """
    normalized_uid = str(chart_uid or "").strip().upper()
    if not normalized_uid:
        raise ValueError("Personal Timeline requires a Chart UID.")

    birth = getattr(chart, "dt", None)
    if not isinstance(birth, datetime.datetime) or birth.tzinfo is None:
        raise ValueError(
            "The selected chart does not have a timezone-aware birth datetime."
        )
    if years <= 0 or step_days <= 0:
        raise ValueError("Timeline years and scan step must be greater than zero.")

    definitions = _build_transit_definitions(chart)
    if not definitions:
        return []

    start, end = _timeline_bounds(chart, birth, years)
    if end <= start:
        return []

    definition_lookup = {definition.key: definition for definition in definitions}
    definitions_by_body: dict[str, list[TimelineTransitDefinition]] = {}
    for definition in definitions:
        definitions_by_body.setdefault(definition.transiting_body, []).append(definition)

    step = datetime.timedelta(days=step_days)
    total_steps = max(1, int((end - start) / step) + 1)
    active_starts: dict[tuple[str, str, str], tuple[datetime.datetime, bool]] = {}
    previous_active: set[tuple[str, str, str]] = set()
    results: list[PersonalTimelineWindow] = []

    previous_dt = start
    current_dt = start
    step_index = 0

    while current_dt <= end:
        if cancelled is not None and cancelled():
            return []

        current_active: set[tuple[str, str, str]] = set()
        for transit_body, body_definitions in definitions_by_body.items():
            longitude = planetary_longitude(current_dt, transit_body)
            if longitude is None:
                continue
            longitude_value = float(longitude)
            for definition in body_definitions:
                if _aspect_orb(longitude_value, definition) <= definition.orb_deg:
                    current_active.add(definition.key)

        for key in current_active.difference(previous_active):
            definition = definition_lookup[key]
            if current_dt == start:
                active_starts[key] = (start, True)
            else:
                active_starts[key] = (
                    _refine_boundary(previous_dt, current_dt, definition),
                    False,
                )

        for key in previous_active.difference(current_active):
            start_info = active_starts.pop(key, None)
            if start_info is None:
                continue
            definition = definition_lookup[key]
            boundary = _refine_boundary(current_dt, previous_dt, definition)
            window_start, start_truncated = start_info
            if boundary >= window_start:
                results.append(
                    PersonalTimelineWindow(
                        chart_uid=normalized_uid,
                        transit=definition,
                        start=window_start,
                        end=boundary,
                        start_truncated=start_truncated,
                    )
                )

        previous_active = current_active
        previous_dt = current_dt
        if current_dt >= end:
            break

        current_dt = min(end, current_dt + step)
        step_index += 1
        if progress is not None and (step_index % 64 == 0 or current_dt >= end):
            progress(min(step_index, total_steps), total_steps)

    for key, (window_start, start_truncated) in active_starts.items():
        results.append(
            PersonalTimelineWindow(
                chart_uid=normalized_uid,
                transit=definition_lookup[key],
                start=window_start,
                end=end,
                start_truncated=start_truncated,
                end_truncated=True,
            )
        )

    results.sort(key=lambda item: (item.start, item.end, item.transit.label))
    return results


def _normalized_uid(value: object) -> str | None:
    text = str(value or "").strip().upper()
    return text or None


def _selected_chart_uid_for_owner(owner: QWidget) -> str:
    """Resolve Database View selection first, then Chart View current UID."""
    selected_uid_getter = getattr(owner, "_selected_chart_uids", None)
    if callable(selected_uid_getter):
        try:
            selected_uids = [
                uid
                for raw_uid in selected_uid_getter()
                if (uid := _normalized_uid(raw_uid)) is not None
            ]
        except Exception:
            selected_uids = []
        if len(selected_uids) == 1:
            return selected_uids[0]
        if len(selected_uids) > 1:
            raise PersonalTimelineSelectionError(
                "Select exactly one chart in Database View before opening Personal Timeline."
            )
        raise PersonalTimelineSelectionError(
            "Select a chart in Database View before opening Personal Timeline."
        )

    candidates: list[Any] = [owner]
    app_owner = getattr(owner, "_app_owner", None)
    if app_owner is not None and app_owner not in candidates:
        candidates.append(app_owner)
    owner_method = getattr(owner, "_owner_window", None)
    if callable(owner_method):
        try:
            resolved_owner = owner_method()
        except Exception:
            resolved_owner = None
        if resolved_owner is not None and resolved_owner not in candidates:
            candidates.append(resolved_owner)

    for candidate in candidates:
        uid_getter = getattr(candidate, "_current_chart_uid_for_navigation", None)
        if callable(uid_getter):
            try:
                uid = _normalized_uid(uid_getter())
            except Exception:
                uid = None
            if uid is not None:
                return uid

        latest_chart = getattr(candidate, "_latest_chart", None)
        uid = _normalized_uid(getattr(latest_chart, "chart_uid", None))
        if uid is not None:
            return uid

    uid = _normalized_uid(get_current_chart_uid())
    if uid is None:
        raise PersonalTimelineSelectionError(
            "Load a chart in Chart View before opening Personal Timeline."
        )
    return uid


class _PersonalTimelineWorker(QObject):
    progress = Signal(int, int)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, chart_uid: str, chart: Any) -> None:
        super().__init__()
        self.chart_uid = chart_uid
        self.chart = chart

    def run(self) -> None:
        thread = QThread.currentThread()
        try:
            windows = generate_personal_timeline(
                self.chart_uid,
                self.chart,
                progress=self.progress.emit,
                cancelled=thread.isInterruptionRequested,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(windows)


class PersonalTimelineWindowWidget(QMainWindow):
    """Non-modal window showing major life transit ranges for one Chart UID."""

    def __init__(
        self,
        chart_uid: str,
        chart: Any,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.Window)
        self.chart_uid = str(chart_uid).strip().upper()
        self.chart = chart
        self._thread: QThread | None = None
        self._worker: _PersonalTimelineWorker | None = None

        chart_name = str(getattr(chart, "name", "Unnamed chart") or "Unnamed chart")
        self.setWindowTitle(f"Personal Timeline — {chart_name}")
        self.resize(980, 720)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.setCentralWidget(central)

        title = QLabel(f"Personal Timeline — {chart_name}", central)
        title_font = title.font()
        title_font.setPointSize(max(12, title_font.pointSize() + 3))
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        uid_label = QLabel(f"Chart UID: {self.chart_uid}", central)
        uid_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(uid_label)

        self.status_label = QLabel("Generating major-life transit ranges…", central)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar(central)
        self.progress_bar.setRange(0, 0)
        layout.addWidget(self.progress_bar)

        self.tree = QTreeWidget(central)
        self.tree.setColumnCount(5)
        self.tree.setHeaderLabels(("Age", "Transit", "Start", "End", "Duration"))
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(False)
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.tree, 1)

        self._start_generation()

    def _start_generation(self) -> None:
        thread = QThread(self)
        worker = _PersonalTimelineWorker(self.chart_uid, self.chart)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(self._on_thread_finished)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_progress(self, current: int, total: int) -> None:
        if total <= 0:
            return
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        percent = int(round((current / total) * 100.0))
        self.status_label.setText(f"Generating major-life transit ranges… {percent}%")

    def _on_finished(self, windows: object) -> None:
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        timeline_windows = list(windows) if isinstance(windows, Iterable) else []
        self._populate(timeline_windows)
        self.status_label.setText(
            f"{len(timeline_windows):,} transit ranges. "
            "Life Forecast rules + Jupiter, Saturn and Chiron major aspects."
        )

    def _on_failed(self, message: str) -> None:
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Could not generate Personal Timeline: {message}")

    def _on_thread_finished(self) -> None:
        self._worker = None
        self._thread = None

    def _populate(self, windows: Iterable[PersonalTimelineWindow]) -> None:
        self.tree.clear()
        birth = getattr(self.chart, "dt", None)
        if not isinstance(birth, datetime.datetime):
            return

        for window in windows:
            age_years = max(
                0.0,
                (window.midpoint - birth).total_seconds() / (365.2425 * 86400.0),
            )
            duration = window.duration_days
            if duration >= 365.0:
                duration_text = f"{duration / 365.2425:.1f} y"
            elif duration >= 60.0:
                duration_text = f"{duration / 30.4375:.1f} mo"
            else:
                duration_text = f"{duration:.0f} d"

            self.tree.addTopLevelItem(
                QTreeWidgetItem(
                    (
                        f"{age_years:.1f}",
                        window.transit.label,
                        f"{window.start:%Y-%m-%d}{'*' if window.start_truncated else ''}",
                        f"{window.end:%Y-%m-%d}{'*' if window.end_truncated else ''}",
                        duration_text,
                    )
                )
            )

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        thread = self._thread
        if thread is not None and thread.isRunning():
            thread.requestInterruption()
        super().closeEvent(event)


def open_personal_timeline_for_window(
    owner: QWidget,
) -> PersonalTimelineWindowWidget | None:
    """Open a timeline for the authoritative Chart UID selected by this window."""
    try:
        chart_uid = _selected_chart_uid_for_owner(owner)
    except PersonalTimelineSelectionError as exc:
        QMessageBox.information(owner, "Personal Timeline", str(exc))
        return None

    try:
        chart = load_chart_by_uid(chart_uid)
    except Exception as exc:
        QMessageBox.warning(
            owner,
            "Personal Timeline",
            f"Could not load Chart UID {chart_uid}: {exc}",
        )
        return None

    timeline = PersonalTimelineWindowWidget(chart_uid, chart, parent=owner)
    open_windows = getattr(owner, "_personal_timeline_windows", None)
    if not isinstance(open_windows, list):
        open_windows = []
        setattr(owner, "_personal_timeline_windows", open_windows)
    open_windows.append(timeline)

    def _release(*_args: object) -> None:
        if timeline in open_windows:
            open_windows.remove(timeline)

    timeline.destroyed.connect(_release)
    timeline.show()
    timeline.raise_()
    timeline.activateWindow()
    return timeline
