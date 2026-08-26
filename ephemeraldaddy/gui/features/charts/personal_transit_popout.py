"""Personal-transit popout helpers to keep app.py lightweight."""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QToolTip

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.composite import (
    PERSONAL_TRANSIT_MODE_DAILY_VIBE,
    PERSONAL_TRANSIT_MODE_LIFE_FORECAST,
    assign_houses,
    compute_aspects,
    normalize_chart,
    personal_transit_rules_for_mode,
)
from ephemeraldaddy.gui.features.transits.diagnostics import (
    log_natal_derived_cache_diagnostic,
)
from ephemeraldaddy.io.geocode import LocationLookupError, geocode_location
from ephemeraldaddy.gui.style import format_chart_header

OUT_OF_SIGN_WARNING = "⚠️"
OUT_OF_SIGN_TOOLTIP = "Out of sign limits, but within orbital limits."
_SIGN_NAMES = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)
_SIGN_DISTANCE_BY_ASPECT = {
    "conjunction": 0,
    "semisextile": 1,
    "sextile": 2,
    "square": 3,
    "trine": 4,
    "quincunx": 5,
    "opposition": 6,
}
_ASPECT_LINE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(name.replace("_", " ")) for name in _SIGN_DISTANCE_BY_ASPECT) + r")\b",
    re.IGNORECASE,
)
_SIGN_LINE_PATTERN = re.compile(
    r"\b(" + "|".join(_SIGN_NAMES) + r")\b",
    re.IGNORECASE,
)


class PersonalTransitLocationError(ValueError):
    """Raised when a personal-transit location cannot be resolved."""


@dataclass(frozen=True)
class PersonalTransitRecalculationResult:
    transit_chart: Chart
    transit_positions_in_natal_houses: dict[str, Any]
    aspect_hits_by_mode: dict[str, list[Any]]
    location_label: str
    raw_location: str
    include_time: bool


def _zodiac_sign_index(longitude: Any) -> int | None:
    try:
        return int((float(longitude) % 360.0) // 30.0) % 12
    except (TypeError, ValueError):
        return None


def _sign_name_index(sign_name: str) -> int | None:
    normalized = sign_name.strip().casefold()
    for index, candidate in enumerate(_SIGN_NAMES):
        if candidate.casefold() == normalized:
            return index
    return None


def _sign_distance(left_index: int, right_index: int) -> int:
    raw_distance = abs(left_index - right_index)
    return min(raw_distance, 12 - raw_distance)


def is_out_of_sign_personal_transit_aspect(hit: Any) -> bool:
    """Return True when exact orb math yields an aspect across non-matching signs.

    Only aspects with an ordinary sign-distance counterpart are classified.
    Harmonics such as quintile/biquintile and 45°/135° aspects have no single
    canonical sign separation, so they are never labeled out-of-sign here.
    """
    aspect_key = str(getattr(hit, "aspect", "")).strip().replace(" ", "_").lower()
    expected_distance = _SIGN_DISTANCE_BY_ASPECT.get(aspect_key)
    if expected_distance is None:
        return False

    left_index = _zodiac_sign_index(getattr(getattr(hit, "a", None), "lon_deg", None))
    right_index = _zodiac_sign_index(getattr(getattr(hit, "b", None), "lon_deg", None))
    if left_index is None or right_index is None:
        return False

    return _sign_distance(left_index, right_index) != expected_distance


def append_out_of_sign_warning(
    line: str,
    hit: Any,
) -> tuple[str, dict[str, object] | None]:
    """Append the Personal Transit warning and return its hover-span metadata."""
    if not is_out_of_sign_personal_transit_aspect(hit):
        return line, None
    base_line = line.rstrip()
    decorated = f"{base_line} {OUT_OF_SIGN_WARNING}"
    warning_start = len(decorated) - len(OUT_OF_SIGN_WARNING)
    return decorated, {
        "span_start": warning_start,
        "span_end": warning_start + len(OUT_OF_SIGN_WARNING),
        "tooltip": OUT_OF_SIGN_TOOLTIP,
    }


def _text_line_is_out_of_sign_aspect(line: str) -> bool:
    """Classify an already validated Personal Transit display row by its signs."""
    if OUT_OF_SIGN_WARNING in line:
        return False
    aspect_match = _ASPECT_LINE_PATTERN.search(line)
    if aspect_match is None:
        return False
    aspect_key = aspect_match.group(1).replace(" ", "_").lower()
    expected_distance = _SIGN_DISTANCE_BY_ASPECT.get(aspect_key)
    if expected_distance is None:
        return False

    signs = _SIGN_LINE_PATTERN.findall(line)
    if len(signs) < 2:
        return False
    left_index = _sign_name_index(signs[0])
    right_index = _sign_name_index(signs[1])
    if left_index is None or right_index is None:
        return False
    return _sign_distance(left_index, right_index) != expected_distance


def decorate_personal_transit_output_text(text: str) -> str:
    """Append warning markers to out-of-sign Personal Transit aspect rows."""
    if "Personal Transit (Transit → Natal)" not in text:
        return text
    lines = text.splitlines()
    decorated = [
        f"{line.rstrip()} {OUT_OF_SIGN_WARNING}"
        if _text_line_is_out_of_sign_aspect(line)
        else line
        for line in lines
    ]
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(decorated) + suffix


class _PersonalTransitWarningTooltipFilter(QObject):
    def eventFilter(self, watched, event) -> bool:  # noqa: ANN001 - Qt event types vary.
        if event.type() == QEvent.Type.MouseMove and isinstance(watched, QPlainTextEdit):
            cursor = watched.cursorForPosition(event.position().toPoint())
            line = cursor.block().text()
            warning_start = line.rfind(OUT_OF_SIGN_WARNING)
            column = cursor.positionInBlock()
            if warning_start >= 0 and warning_start <= column <= warning_start + len(OUT_OF_SIGN_WARNING):
                global_position = (
                    event.globalPosition().toPoint()
                    if hasattr(event, "globalPosition")
                    else event.globalPos()
                )
                QToolTip.showText(global_position, OUT_OF_SIGN_TOOLTIP, watched)
                return False
            QToolTip.hideText()
        elif event.type() == QEvent.Type.Leave:
            QToolTip.hideText()
        return super().eventFilter(watched, event)


def _install_personal_transit_output_warning_support() -> None:
    """Attach warning decoration to the Personal Transit popout's text output.

    The popout renderer still lives in the large app module. This keeps the
    aspect-specific behavior in the extracted Personal Transit feature module
    while using the existing plain-text output widget unchanged.
    """
    app = QApplication.instance()
    if app is None:
        return

    for widget in app.allWidgets():
        if not isinstance(widget, QPlainTextEdit):
            continue
        window_title = str(widget.window().windowTitle() or "").casefold()
        if "personal transit" not in window_title:
            continue
        if bool(widget.property("personalTransitOutOfSignSupport")):
            continue

        widget.setProperty("personalTransitOutOfSignSupport", True)
        widget.setMouseTracking(True)
        tooltip_filter = _PersonalTransitWarningTooltipFilter(widget)
        widget.installEventFilter(tooltip_filter)
        widget._personal_transit_warning_tooltip_filter = tooltip_filter
        state = {"decorating": False}

        def _decorate_output(*_args: object, output: QPlainTextEdit = widget, guard: dict[str, bool] = state) -> None:
            if guard["decorating"]:
                return
            current_text = output.toPlainText()
            decorated_text = decorate_personal_transit_output_text(current_text)
            if decorated_text == current_text:
                return
            vertical_scroll = output.verticalScrollBar().value()
            horizontal_scroll = output.horizontalScrollBar().value()
            guard["decorating"] = True
            try:
                output.setPlainText(decorated_text)
                output.verticalScrollBar().setValue(vertical_scroll)
                output.horizontalScrollBar().setValue(horizontal_scroll)
            finally:
                guard["decorating"] = False

        widget.textChanged.connect(_decorate_output)
        widget._personal_transit_warning_decorator = _decorate_output
        _decorate_output()


def resolve_personal_transit_location(
    raw_value: str,
    *,
    fallback_lat: float,
    fallback_lon: float,
    fallback_location_label: str,
) -> tuple[float, float, str]:
    value = raw_value.strip()
    if not value:
        return float(fallback_lat), float(fallback_lon), str(fallback_location_label)

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
        raise PersonalTransitLocationError(str(error)) from error
    return float(lat), float(lon), resolved_label


def build_personal_transit_header_lines(
    *,
    natal_chart_name: str,
    transit_chart: Chart,
    location_label: str,
    include_time: bool,
    local_tz: datetime.tzinfo,
) -> list[str]:
    # The renderer invokes this helper immediately before replacing the summary
    # text, so install the warning decorator before that setPlainText call.
    _install_personal_transit_output_warning_support()

    local_dt = transit_chart.dt.astimezone(local_tz)
    date_label = local_dt.strftime("%m.%d.%Y")
    time_label = local_dt.strftime("%H:%M") if include_time else "omitted"
    timezone_label = local_dt.strftime("%Z") or str(local_tz)
    return [
        "Personal Transit (Transit → Natal)",
        "",
        f"Name:      {natal_chart_name}",
        format_chart_header(
            "when_where",
            date=date_label,
            time=time_label,
            timezone=timezone_label,
            location=location_label,
            lat=transit_chart.lat,
            lon=transit_chart.lon,
        ),
        "",
    ]


def recalculate_personal_transit(
    *,
    natal_chart: Chart,
    selected_local_datetime: datetime.datetime,
    location: tuple[float, float, str],
    raw_location: str,
) -> PersonalTransitRecalculationResult:
    # The popout can be recalculated long after it first opened. Revalidate the
    # natal derived state at the calculation boundary instead of assuming the
    # object still reflects canonical birth data.
    log_natal_derived_cache_diagnostic(natal_chart)

    lat, lon, location_label = location
    selected_utc = selected_local_datetime.astimezone(datetime.timezone.utc)
    include_time = True
    timestamp_label = selected_utc.strftime("%Y-%m-%d %H:%M UTC")
    personal_transit_name = (
        f"Personal Transit Chart for {natal_chart.name} on {timestamp_label} @ {location_label}"
    )
    transit_chart = Chart(
        personal_transit_name,
        selected_utc,
        lat,
        lon,
        tz=datetime.timezone.utc,
    )
    transit_chart.birth_place = location_label
    transit_chart.birthtime_unknown = not include_time
    transit_chart.retcon_time_used = False

    transit_normalized = normalize_chart(transit_chart, chart_type="transit")
    natal_normalized = normalize_chart(natal_chart, chart_type="natal")
    transit_in_natal = assign_houses(
        transit_normalized.bodies,
        natal_normalized.houses,
        layer="TRANSIT",
    )
    natal_targets = assign_houses(
        natal_normalized.bodies,
        natal_normalized.houses,
        layer="NATAL",
    )
    aspect_hits_by_mode = {
        PERSONAL_TRANSIT_MODE_LIFE_FORECAST: compute_aspects(
            transit_in_natal.values(),
            natal_targets.values(),
            personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_LIFE_FORECAST),
        ),
        PERSONAL_TRANSIT_MODE_DAILY_VIBE: compute_aspects(
            transit_in_natal.values(),
            natal_targets.values(),
            personal_transit_rules_for_mode(PERSONAL_TRANSIT_MODE_DAILY_VIBE),
        ),
    }

    return PersonalTransitRecalculationResult(
        transit_chart=transit_chart,
        transit_positions_in_natal_houses=transit_in_natal,
        aspect_hits_by_mode=aspect_hits_by_mode,
        location_label=location_label,
        raw_location=raw_location.strip() or location_label,
        include_time=include_time,
    )
