"""Guide to the Galaxy help dialog and ephemeris-backed timing explorer."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from functools import lru_cache
from math import cos, pi, sin
from typing import Callable

from ephemeraldaddy.core.interpretations import ZODIAC_NAMES
SECONDS = lambda n: _dt.timedelta(seconds=n)
MINUTES = lambda n: _dt.timedelta(minutes=n)
HOURS = lambda n: _dt.timedelta(hours=n)
DAYS = lambda n: _dt.timedelta(days=n)
INFINITY = float("inf")

TIMELINE_BUCKETS = (
    {"label": "minute-scale", "max_days": 1 / 24},
    {"label": "hour-scale", "max_days": 1},
    {"label": "day-scale", "max_days": 14},
    {"label": "month-scale", "max_days": 365 / 2},
    {"label": "year-scale", "max_days": 365 * 3},
    {"label": "multi-year", "max_days": 365 * 10},
    {"label": "decade-scale", "max_days": INFINITY},
)

BODY_UI_META = {
    "Sun": {
        "group": "luminary",
        "default_window_years": 300,
        "sample_step": HOURS(6),
        "boundary_tolerance": MINUTES(1),
        "supports_retrograde_panel": False,
        "supports_speed_plot": True,
        "kind": "apparent_solar_position",
        "notes": "Astrologically treated as a luminary; astronomically this is Earth's apparent solar longitude.",
    },
    "Moon": {
        "group": "luminary",
        "default_window_years": 300,
        "sample_step": MINUTES(30),
        "boundary_tolerance": SECONDS(30),
        "supports_retrograde_panel": False,
        "supports_speed_plot": True,
        "kind": "physical_body",
        "notes": "Fastest common chart factor; sign changes are visible on a day-scale.",
    },
    "Mercury": {"group": "planet", "default_window_years": 300, "sample_step": HOURS(3), "boundary_tolerance": MINUTES(1), "supports_retrograde_panel": True, "supports_speed_plot": True, "kind": "physical_body", "notes": "Frequent apparent retrograde loops can extend sign stays."},
    "Venus": {"group": "planet", "default_window_years": 300, "sample_step": HOURS(6), "boundary_tolerance": MINUTES(1), "supports_retrograde_panel": True, "supports_speed_plot": True, "kind": "physical_body", "notes": "Retrograde loops are less frequent but can greatly stretch a stay."},
    "Mars": {"group": "planet", "default_window_years": 300, "sample_step": HOURS(12), "boundary_tolerance": MINUTES(1), "supports_retrograde_panel": True, "supports_speed_plot": True, "kind": "physical_body", "notes": "Its retrograde cycle creates large anomalies compared with its usual sign pace."},
    "Jupiter": {"group": "planet", "default_window_years": 300, "sample_step": DAYS(1), "boundary_tolerance": MINUTES(2), "supports_retrograde_panel": True, "supports_speed_plot": True, "kind": "physical_body", "notes": "Usually a year-scale placement, with boundary back-and-forth around retrograde."},
    "Saturn": {"group": "planet", "default_window_years": 300, "sample_step": DAYS(1), "boundary_tolerance": MINUTES(2), "supports_retrograde_panel": True, "supports_speed_plot": True, "kind": "physical_body", "notes": "Usually multi-year by sign, with periodic retrograde revisits."},
    "Uranus": {"group": "planet", "default_window_years": 300, "sample_step": DAYS(2), "boundary_tolerance": MINUTES(5), "supports_retrograde_panel": True, "supports_speed_plot": True, "kind": "physical_body", "notes": "A generational body; sign timing varies because its orbit is not uniform from Earth's view."},
    "Neptune": {"group": "planet", "default_window_years": 300, "sample_step": DAYS(3), "boundary_tolerance": MINUTES(5), "supports_retrograde_panel": True, "supports_speed_plot": True, "kind": "physical_body", "notes": "A decade-scale/generational body with slow apparent motion."},
    "Pluto": {"group": "planet", "default_window_years": 300, "sample_step": DAYS(3), "boundary_tolerance": MINUTES(5), "supports_retrograde_panel": True, "supports_speed_plot": True, "kind": "physical_body", "notes": "Highly irregular sign durations because Pluto's orbit is eccentric."},
    "Chiron": {"group": "small_body", "default_window_years": 300, "sample_step": DAYS(1), "boundary_tolerance": MINUTES(2), "supports_retrograde_panel": True, "supports_speed_plot": True, "kind": "small_body", "notes": "A minor body used astrologically; availability depends on Swiss Ephemeris minor-body data."},
    "Ceres": {"group": "asteroid", "default_window_years": 300, "sample_step": DAYS(1), "boundary_tolerance": MINUTES(2), "supports_retrograde_panel": True, "supports_speed_plot": True, "kind": "small_body", "notes": "A physical asteroid/dwarf-planet-class small body used by some astrologers; ephemeris availability depends on Swiss asteroid data."},
    "Pallas": {"group": "asteroid", "default_window_years": 300, "sample_step": DAYS(1), "boundary_tolerance": MINUTES(2), "supports_retrograde_panel": True, "supports_speed_plot": True, "kind": "small_body", "notes": "A physical asteroid used astrologically; not a classical planet."},
    "Juno": {"group": "asteroid", "default_window_years": 300, "sample_step": DAYS(1), "boundary_tolerance": MINUTES(2), "supports_retrograde_panel": True, "supports_speed_plot": True, "kind": "small_body", "notes": "A physical asteroid used astrologically; apparent retrograde can produce sign revisits."},
    "Vesta": {"group": "asteroid", "default_window_years": 300, "sample_step": DAYS(1), "boundary_tolerance": MINUTES(2), "supports_retrograde_panel": True, "supports_speed_plot": True, "kind": "small_body", "notes": "A physical asteroid used astrologically; availability depends on Swiss asteroid data."},
    "Mean Lilith": {"group": "calculated_point", "default_window_years": 300, "sample_step": HOURS(6), "boundary_tolerance": MINUTES(1), "supports_retrograde_panel": False, "supports_speed_plot": True, "kind": "mathematical_point", "notes": "Mean lunar apogee: an averaged mathematical point, not a physical object."},
    "True Lilith": {"group": "calculated_point", "default_window_years": 300, "sample_step": HOURS(6), "boundary_tolerance": MINUTES(1), "supports_retrograde_panel": True, "supports_speed_plot": True, "kind": "mathematical_point", "notes": "Osculating lunar apogee: a calculated point that can jump and loop more noticeably."},
    "Natural Lilith": {"group": "calculated_point", "default_window_years": 300, "sample_step": DAYS(1), "boundary_tolerance": MINUTES(1), "supports_retrograde_panel": False, "supports_speed_plot": False, "kind": "astrological_only", "notes": "A tradition-specific astrological-only Lilith label; this app does not currently expose a distinct astronomical or Swiss Ephemeris calculation for it."},
}

DISPLAY_BODIES = tuple(BODY_UI_META.keys())
_MODEL_BODIES = tuple(name for name in DISPLAY_BODIES if name not in {"Mean Lilith", "True Lilith", "Natural Lilith"})
_UNSUPPORTED_RANGE_BODIES = {"Natural Lilith"}


@dataclass(frozen=True)
class SignRange:
    sign: str
    start: _dt.datetime
    end: _dt.datetime
    open_start: bool = False
    open_end: bool = False

    @property
    def is_complete(self) -> bool:
        return not self.open_start and not self.open_end

    @property
    def duration_days(self) -> float:
        return (self.end - self.start).total_seconds() / 86400.0


def _sign_for_longitude(longitude: float) -> str:
    return ZODIAC_NAMES[int((longitude % 360.0) // 30.0)]


def _timeline_label(days: float) -> str:
    for bucket in TIMELINE_BUCKETS:
        if days <= float(bucket["max_days"]):
            return str(bucket["label"])
    return "decade-scale"


def _body_longitude(moment: _dt.datetime, body_name: str) -> float | None:
    from ephemeraldaddy.core import ephemeris

    if body_name == "Mean Lilith":
        previous = ephemeris.get_lilith_calculation_mode()
        try:
            ephemeris.set_lilith_calculation_mode(ephemeris.LILITH_CALCULATION_MEAN)
            return ephemeris.planetary_longitude(moment, "Lilith")
        finally:
            ephemeris.set_lilith_calculation_mode(previous)
    if body_name == "True Lilith":
        previous = ephemeris.get_lilith_calculation_mode()
        try:
            ephemeris.set_lilith_calculation_mode(ephemeris.LILITH_CALCULATION_TRUE)
            return ephemeris.planetary_longitude(moment, "Lilith")
        finally:
            ephemeris.set_lilith_calculation_mode(previous)
    return ephemeris.planetary_longitude(moment, body_name)


def _refine_boundary(body_name: str, before: _dt.datetime, after: _dt.datetime, from_sign: str, tolerance: _dt.timedelta) -> _dt.datetime:
    lo = before
    hi = after
    while hi - lo > tolerance:
        mid = lo + (hi - lo) / 2
        lon = _body_longitude(mid, body_name)
        if lon is None:
            break
        if _sign_for_longitude(lon) == from_sign:
            lo = mid
        else:
            hi = mid
    return hi


@lru_cache(maxsize=96)
def sign_ranges_for_body(
    body_name: str,
    sign_name: str,
    past_window_years: int = 300,
    future_window_years: int = 100,
) -> tuple[SignRange, ...]:
    if body_name in _UNSUPPORTED_RANGE_BODIES:
        return ()
    meta = BODY_UI_META[body_name]
    step = meta["sample_step"]
    tolerance = meta["boundary_tolerance"]
    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)
    start = now - _dt.timedelta(days=int(past_window_years * 365.2425))
    end = now + _dt.timedelta(days=int(future_window_years * 365.2425))
    cursor = start
    first_lon = _body_longitude(cursor, body_name)
    if first_lon is None:
        return ()
    current_sign = _sign_for_longitude(first_lon)
    current_start = cursor
    current_open_start = True
    ranges: list[SignRange] = []
    while cursor < end:
        probe = min(cursor + step, end)
        lon = _body_longitude(probe, body_name)
        if lon is None:
            cursor = probe
            continue
        probe_sign = _sign_for_longitude(lon)
        if probe_sign != current_sign:
            boundary = _refine_boundary(body_name, cursor, probe, current_sign, tolerance)
            if current_sign == sign_name:
                ranges.append(
                    SignRange(
                        current_sign,
                        current_start,
                        boundary,
                        open_start=current_open_start,
                    )
                )
            current_sign = probe_sign
            current_start = boundary
            current_open_start = False
        cursor = probe
    if current_sign == sign_name:
        ranges.append(
            SignRange(
                current_sign,
                current_start,
                end,
                open_start=current_open_start,
                open_end=True,
            )
        )
    return tuple(ranges)


def _format_dt(moment: _dt.datetime) -> str:
    return moment.astimezone(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _duration_text(days: float) -> str:
    if days < 1 / 24:
        return f"{days * 1440:.0f} minutes"
    if days < 2:
        return f"{days * 24:.1f} hours"
    if days < 90:
        return f"{days:.1f} days"
    if days < 730:
        return f"{days / 30.436875:.1f} months"
    return f"{days / 365.2425:.1f} years"


def _build_ranges_html(body_name: str, sign_name: str, ranges: tuple[SignRange, ...]) -> str:
    meta = BODY_UI_META[body_name]
    header = (
        f"<h2>{body_name} in {sign_name}</h2>"
        f"<p><strong>Kind:</strong> {meta['kind']} • <strong>Group:</strong> {meta['group']} • "
        f"<p><strong>Kind:</strong> {meta['kind']} • <strong>Group:</strong> {meta['group']} • "
        f"<strong>Retrograde panel:</strong> {'yes' if meta['supports_retrograde_panel'] else 'no'} • "
        f"<strong>Speed plot:</strong> {'yes' if meta['supports_speed_plot'] else 'no'}</p>"
        f"<p>{meta['notes']}</p>"
    )
    if body_name in _UNSUPPORTED_RANGE_BODIES:
        return header + "<p><em>No date-range lookup is available because this is not currently represented by the app ephemeris as a distinct object or point.</em></p>"
    if not ranges:
        return header + "<p><em>No ranges were available from the built-in ephemeris for this body/sign/window.</em></p>"
    complete_ranges = tuple(item for item in ranges if item.is_complete)
    open_count = len(ranges) - len(complete_ranges)
    if complete_ranges:
        durations = [item.duration_days for item in complete_ranges]
        shortest = min(durations)
        longest = max(durations)
        sorted_durations = sorted(durations)
        typical = sorted_durations[len(sorted_durations) // 2]
        summary = (
            "<h3>400-year summary (300 past / 100 future)</h3>"
            f"<p><strong>Complete occurrences:</strong> {len(complete_ranges)}<br/>"
            f"<strong>Open edge intervals excluded:</strong> {open_count}<br/>"
            f"<strong>Shortest:</strong> {_duration_text(shortest)} ({_timeline_label(shortest)})<br/>"
            f"<strong>Modal-ish / median:</strong> {_duration_text(typical)} ({_timeline_label(typical)})<br/>"
            f"<strong>Longest:</strong> {_duration_text(longest)} ({_timeline_label(longest)})</p>"
        )
    else:
        summary = (
            "<h3>400-year summary (300 past / 100 future)</h3>"
            f"<p><strong>Complete occurrences:</strong> 0<br/>"
            f"<strong>Open edge intervals excluded:</strong> {open_count}</p>"
            "<p><em>The selected body/sign only appeared as a leading or trailing open interval in this window, "
            "so no complete duration summary is shown.</em></p>"
        )
    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)
    preferred_display_end = now + _dt.timedelta(days=int(50 * 365.2425))
    display_ranges = [item for item in ranges if item.start <= preferred_display_end][-80:]
    if len(display_ranges) < 80:
        display_ranges.extend(item for item in ranges if item.start > preferred_display_end)
        display_ranges = display_ranges[:80]

    rows = []
    for item in display_ranges:
        start_text = "open before scan" if item.open_start else _format_dt(item.start)
        end_text = "still in sign at scan end" if item.open_end else _format_dt(item.end)
        duration_text = (
            "open interval; excluded from summary"
            if not item.is_complete
            else _duration_text(item.duration_days)
        )
        scale_text = "open" if not item.is_complete else _timeline_label(item.duration_days)
        rows.append(
            "<tr>"
            f"<td>{start_text}</td>"
            f"<td>{end_text}</td>"
            f"<td>{duration_text}</td>"
            f"<td>{scale_text}</td>"
            "</tr>"
        )
    omitted = ""
    if len(ranges) > len(display_ranges):
        omitted = f"<p><em>Showing 80 of {len(ranges)} ranges to keep the panel readable, ending near 50 years in the future when available.</em></p>"
    return header + summary + omitted + "<table border='1' cellspacing='0' cellpadding='4'><tr><th>Start</th><th>End</th><th>Duration</th><th>Scale</th></tr>" + "".join(rows) + "</table>"


def _show_sidereal_discussion_help(owner: "QWidget") -> None:
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

    dialog = QDialog(owner)
    dialog.setModal(False)
    dialog.setWindowTitle("Sidereal Discussion")
    dialog.resize(560, 360)
    layout = QVBoxLayout(dialog)
    label = QLabel(
        "<h2>Sidereal Discussion</h2>"
        "<p>This help page is intentionally blank for now.</p>"
        "<p>Future notes can compare tropical and sidereal reference frames, ayanāṃśa choices, "
        "and why astrological traditions do not always map one-to-one onto astronomy.</p>"
    )
    label.setWordWrap(True)
    layout.addWidget(label, 1)
    buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=dialog)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.show()

    def _show_discussion_help(owner: "QWidget") -> None:
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

        dialog = QDialog(owner)
        dialog.setModal(False)
        dialog.setWindowTitle("Heliocentric Astrology")
        dialog.resize(560, 360)
        layout = QVBoxLayout(dialog)
        label = QLabel(
            "<h2>Heliocentric Astrology</h2>"
            "<p>Aristarchus of Samos, 3rd century BCE was the earliest known heliocentrist in the then-hybrid discipline of astrology/astronomy.</p>"
            "<p>His own heliocentric work is lost, but Archimedes preserves the claim that Aristarchus proposed the fixed stars and Sun remain still while Earth revolves around the Sun.</p>"
        )
        label.setWordWrap(True)
        layout.addWidget(label, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=dialog)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.show()


def show_guide_to_the_galaxy(owner: "QWidget") -> None:
    from PySide6.QtCore import QPointF, QRectF, QTimer, Qt
    from PySide6.QtGui import QColor, QFont, QPainter, QPen
    from PySide6.QtWidgets import (
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QTextBrowser,
        QVBoxLayout,
        QWidget,
    )

    model_bodies = [
        {"name": "Moon", "period": 27.32, "distance": 0.18, "color": "#d7dde8", "size": 6},
        {"name": "Mercury", "period": 87.97, "distance": 0.30, "color": "#b9a58d", "size": 6},
        {"name": "Venus", "period": 224.70, "distance": 0.40, "color": "#e4c477", "size": 7},
        {"name": "Sun", "period": 365.25, "distance": 0.52, "color": "#ffcc45", "size": 9},
        {"name": "Mars", "period": 686.98, "distance": 0.62, "color": "#d46a4c", "size": 7},
        {"name": "Jupiter", "period": 4332.59, "distance": 0.73, "color": "#d2a679", "size": 10},
        {"name": "Saturn", "period": 10759.22, "distance": 0.83, "color": "#c5b070", "size": 9},
        {"name": "Uranus", "period": 30688.5, "distance": 0.91, "color": "#78c7d8", "size": 8},
        {"name": "Neptune", "period": 60182.0, "distance": 0.98, "color": "#5c7dff", "size": 8},
        {"name": "Pluto", "period": 90560.0, "distance": 1.05, "color": "#b8a6a0", "size": 5},
        {"name": "Chiron", "period": 18470.0, "distance": 0.68, "color": "#b2e06f", "size": 6},
    ]

    class SolarSystemModel(QWidget):
        def __init__(self, on_select: Callable[[str], None], parent=None):
            super().__init__(parent)
            self.setMinimumSize(520, 520)
            self.setMouseTracking(True)
            self._time_days = 0.0
            self._dragging = False
            self._drag_start_x = 0.0
            self._drag_start_time = 0.0
            self._paused = False
            self._selected = "Earth"
            self._on_select = on_select
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(33)

        def _tick(self):
            if not self._paused and not self._dragging:
                self._time_days += 3.0
                self.update()

        def _body_positions(self):
            rect = self.rect().adjusted(34, 34, -34, -34)
            center = QPointF(rect.center())
            max_radius = min(rect.width(), rect.height()) / 2.0 * 0.86
            positions = []
            for body in model_bodies:
                radius = max_radius * float(body["distance"]) / 1.05
                angle = (self._time_days / float(body["period"]) * 2.0 * pi) - pi / 2.0
                point = QPointF(center.x() + cos(angle) * radius, center.y() + sin(angle) * radius)
                positions.append((body, point, radius))
            return center, positions

        def paintEvent(self, event):  # noqa: ANN001 - Qt override signature varies.
            super().paintEvent(event)
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillRect(self.rect(), QColor("#08101f"))
            center, positions = self._body_positions()
            painter.setPen(QPen(QColor("#2f4265"), 1))
            for _body, _point, radius in positions:
                painter.drawEllipse(center, radius, radius)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#65a7ff"))
            painter.drawEllipse(center, 11, 11)
            painter.setPen(QColor("#dbe7ff"))
            painter.drawText(QRectF(center.x() - 28, center.y() + 14, 56, 18), Qt.AlignCenter, "Earth")
            for body, point, _radius in positions:
                size = int(body["size"])
                painter.setBrush(QColor(str(body["color"])))
                painter.setPen(QPen(QColor("#ffffff") if body["name"] == self._selected else QColor("#18253f"), 2))
                painter.drawEllipse(point, size, size)
                painter.setPen(QColor("#dbe7ff"))
                painter.drawText(QRectF(point.x() - 38, point.y() + size + 2, 76, 18), Qt.AlignCenter, str(body["name"]))
            painter.setFont(QFont("", 9))
            painter.setPen(QColor("#9fb5d9"))
            painter.drawText(14, self.height() - 18, f"Drag left/right to scrub time • click bodies • model days elapsed: {int(self._time_days):,}")

        def mousePressEvent(self, event):  # noqa: ANN001
            if event.button() == Qt.LeftButton:
                self._dragging = True
                self._paused = True
                self._drag_start_x = event.position().x()
                self._drag_start_time = self._time_days
                center, positions = self._body_positions()
                if (event.position() - center).manhattanLength() < 16:
                    self._selected = "Earth"
                for body, point, _radius in positions:
                    if (event.position() - point).manhattanLength() <= int(body["size"]) + 8:
                        self._selected = str(body["name"])
                        self._on_select(self._selected)
                self.update()
            super().mousePressEvent(event)

        def mouseMoveEvent(self, event):  # noqa: ANN001
            if self._dragging:
                self._time_days = max(0.0, self._drag_start_time + (event.position().x() - self._drag_start_x) * 10.0)
                self.update()
            super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event):  # noqa: ANN001
            if event.button() == Qt.LeftButton:
                self._dragging = False
                self._paused = False
            super().mouseReleaseEvent(event)

    dialog = QDialog(owner)
    dialog.setModal(False)
    dialog.setWindowTitle("Guide to the Galaxy")
    dialog.resize(1180, 760)
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel("<h1>Guide to the Galaxy</h1>"))
    subhead = QTextBrowser(dialog)
    subhead.setOpenExternalLinks(False)
    subhead.setMaximumHeight(96)
    subhead.setHtml(
        "<p><em>This is not astronomy. The two are connected, but astronomy is an empirical, materialist science that has been quite differentiated since at least the 1700s. Astrology is subjective metaphysics and many people would deem it a pseudoscience in the pejorative sense. They do reference many of the same basic tools, but they are not entirely in accord. For instance, the <a href='ephemeraldaddy://help/sidereal-discussion'>sidereal discussion</a>.</em></p>"
        "<p>You will notice that the model below reflects observed cosmic phenomena from the perspective of Earth (geocentric model), rather than a literal heliocentric model. The broad tradition of astrology predates the concept of heliocentrism, as far as most remaining <a href='ephemeraldaddy://help/heliocentric_astrology'>historical sources</a> indicate. That said, geocentric astrology is not automatically the same claim as 'geocentric physics'. A birth chart is cast from the native’s location on Earth, so geocentric coordinates make practical sense even in a heliocentric solar system.<p>"
        "<p>Nevertheless, it's worth noting that ancient astrologers usually were not making that modern distinction cleanly. Most probably assumed the geocentric cosmos was physically true, because that was the dominant educated model. This is a significant argument against mainstream adoption of astrology as a viable model for explaining any aspects of reality besides those which emerge out of faith-based and/or subconscious psychological projections.</p>"
        "<p>Regardless, as far as the developer of this app has been able to personally determine, many aspects of it seem to correlate beyond expected standard deviation reliably enough to warrant further scrutiny, and so I for one am not entirely deterred by its anachronisms. It's possible that some systems function well by using relative rather than absolute observations. I would contend that if there is any validity to astrology, it is only because tropical astrology (specifically) is far more about earthly cycles mapped to celestial patterns rather than the cosmos themselves, a fact which tropical astrologers of any quality acknowledge. The great schism between astrology and astronomy arguably arose out of the distinction that astronomy studied the sky for the sky's sake, whereas in astrology, said cosmos were primarily used as (increasingly symbolic and mythologized) reference points for seasonal shifts, noteworthy impacts on temperature, weather, lighting. From this standpoint, the prior's validity conceivably remains in tact.</p>"
    )
    subhead.anchorClicked.connect(lambda _url: _show_sidereal_discussion_help(dialog))
    layout.addWidget(subhead)

    row = QHBoxLayout()
    controls = QHBoxLayout()
    body_combo = QComboBox(dialog)
    body_combo.addItems(DISPLAY_BODIES)
    sign_combo = QComboBox(dialog)
    sign_combo.addItems(ZODIAC_NAMES)
    calculate_button = QPushButton("Show 300y past / 100y future sign ranges", dialog)
    controls.addWidget(QLabel("Body / point:"))
    controls.addWidget(body_combo)
    controls.addWidget(QLabel("Sign:"))
    controls.addWidget(sign_combo)
    controls.addWidget(calculate_button)

    right = QVBoxLayout()
    right.addLayout(controls)
    explain = QTextBrowser(dialog)
    explain.setOpenExternalLinks(False)
    explain.setHtml(
        "<h2>Compressed model caveat</h2>"
        "<p>The solar system is far vaster than any comfortable screen model. Orbit sizes, planet sizes, "
        "and speeds are deliberately compressed so the pattern is legible. Earth is fixed at the center "
        "because this is illustrating how astrology interprets sky positions from here on Earth.</p>"
        "<h2>Timeline buckets</h2>"
        "<p>We classify sign occupancy as minute-scale, hour-scale, day-scale, month-scale, year-scale, "
        "multi-year, or decade-scale. Irregular apparent cycles usually come from retrograde loops, eccentric "
        "orbits, or calculated points rather than a planet literally reversing direction in space.</p>"
        "<h2>Astrology versus astronomy vocabulary</h2>"
        "<p><strong>Retrograde</strong> in astrology is geocentric apparent backward motion against the zodiac. "
        "Astronomically, the body does not usually reverse its orbit; the effect comes from changing Earth-body-Sun geometry. "
        "Lilith variants are mathematical lunar-apogee conventions or tradition-specific labels, not physical planets.</p>"
    )
    right.addWidget(explain, 1)

    def choose_body(name: str) -> None:
        index = body_combo.findText(name)
        if index >= 0:
            body_combo.setCurrentIndex(index)

    model = SolarSystemModel(choose_body, dialog)
    row.addWidget(model, 3)
    row.addLayout(right, 2)
    layout.addLayout(row, 1)

    def refresh_ranges() -> None:
        body = body_combo.currentText()
        sign = sign_combo.currentText()
        calculate_button.setEnabled(False)
        calculate_button.setText("Calculating…")
        try:
            ranges = sign_ranges_for_body(body, sign, BODY_UI_META[body]["default_window_years"], 100)
            explain.setHtml(_build_ranges_html(body, sign, ranges))
        except Exception as exc:  # defensive UI boundary for optional ephemeris data
            explain.setHtml(f"<h2>{body} in {sign}</h2><p><em>Could not calculate ranges from the built-in ephemeris: {exc}</em></p>")
        finally:
            calculate_button.setEnabled(True)
            calculate_button.setText("Show 300y past / 100y future sign ranges")

    calculate_button.clicked.connect(refresh_ranges)
    buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=dialog)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.show()
