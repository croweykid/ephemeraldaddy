"""Chart View right-panel UI for Time/Rectification Sensitivity."""

from __future__ import annotations

import re
from html import escape
from urllib.parse import quote
from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.analysis.time_sensitivity import (
    TimeSensitivityConfig,
    TimeSensitivityResult,
    birth_date_key_for_chart,
    compute_time_sensitivity,
    load_time_sensitivity_result_for_chart,
    save_time_sensitivity_result,
)
from ephemeraldaddy.analysis.human_design_reference import GATE_COLORS
from ephemeraldaddy.core.interpretations import (
    ELEMENT_COLORS,
    HOUSE_COLORS,
    MODE_COLORS,
    NAKSHATRA_PLANET_COLOR,
    PLANET_COLORS,
    PLANET_ORDER,
    SIGN_COLORS,
    SIGN_KEYWORDS,
)
from ephemeraldaddy.gui.features.charts.chart_analytics_popout import _display_body_name
from ephemeraldaddy.gui.style import (
    CHART_DATA_HIGHLIGHT_COLOR,
    COLLAPSIBLE_SECTION_CONTENT_STYLE,
    DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE,
    DATABASE_ANALYTICS_CONTENT_MARGINS,
    DATABASE_ANALYTICS_CONTENT_SPACING,
    configure_collapsible_header_toggle,
)


class TimeSensitivityFigureCanvas(FigureCanvas):
    """Matplotlib canvas that lets the Time Sensitivity panel keep scrolling under charts."""

    def wheelEvent(self, event: object) -> None:  # noqa: N802 - Qt API
        scroll_area = self._nearest_scroll_area()
        if scroll_area is None:
            super().wheelEvent(event)
            return
        pixel_delta = event.pixelDelta().y() if hasattr(event, "pixelDelta") else 0
        angle_delta = event.angleDelta().y() if hasattr(event, "angleDelta") else 0
        if pixel_delta or angle_delta:
            scrollbar = scroll_area.verticalScrollBar()
            if pixel_delta:
                scrollbar.setValue(scrollbar.value() - int(pixel_delta))
            else:
                steps = (
                    int(angle_delta / 120)
                    if abs(angle_delta) >= 120
                    else (1 if angle_delta > 0 else -1)
                )
                scrollbar.setValue(
                    scrollbar.value() - (steps * scrollbar.singleStep() * 3)
                )
            event.accept()
            return
        super().wheelEvent(event)

    def _nearest_scroll_area(self) -> QAbstractScrollArea | None:
        widget_parent = self.parentWidget()
        while widget_parent is not None:
            if isinstance(widget_parent, QAbstractScrollArea):
                return widget_parent
            widget_parent = widget_parent.parentWidget()
        return None


_TIME_SENSITIVITY_CHART_TITLES = {
    "dominant_planet_weights": "Dominant Body Weight Distribution",
    "dominant_sign_weights": "Dominant Sign Weight Distribution",
    "dominant_element_weights": "Dominant Element Weight Distribution",
    "dominant_house_weights": "Dominant House Weight Distribution",
    "dominant_mode_weights": "Dominant Mode Weight Distribution",
    "dominant_nakshatra_weights": "Dominant Nakshatra Weight Distribution",
}


def _likelihood_rows(
    result: TimeSensitivityResult, group_key: str
) -> list[tuple[str, float]]:
    """Return non-zero average raw-weight rows for Time Sensitivity charts."""
    ranges = result.numeric_ranges.get(group_key, {})
    rows = [
        (
            str(key),
            (float(payload.get("min", 0.0)) + float(payload.get("max", 0.0))) / 2.0,
        )
        for key, payload in ranges.items()
        if isinstance(payload, dict) and float(payload.get("max", 0.0)) > 0.0
    ]
    return sorted(rows, key=lambda item: (-item[1], item[0]))


def _raw_weight_range_rows(
    result: TimeSensitivityResult, group_key: str
) -> list[tuple[str, float, float]]:
    """Return labels with min/max raw weights across sampled charts."""
    ranges = result.numeric_ranges.get(group_key, {})
    rows = [
        (str(key), float(payload.get("min", 0.0)), float(payload.get("max", 0.0)))
        for key, payload in ranges.items()
        if isinstance(payload, dict) and float(payload.get("max", 0.0)) > 0.0
    ]
    return sorted(rows, key=lambda item: (-item[2], item[0]))


def _color_for_likelihood(group_key: str, label: str) -> str:
    return _factor_color(group_key, label)


def _display_label_for_likelihood(group_key: str, label: str) -> str:
    if group_key == "dominant_planet_weights":
        return _display_body_name(label)
    if group_key == "dominant_house_weights":
        return str(label).removeprefix("House ").strip()
    return label


def _draw_likelihood_chart(
    ax: Any,
    result: TimeSensitivityResult,
    group_key: str,
    on_factor_click: Any | None = None,
) -> None:
    rows = _raw_weight_range_rows(result, group_key)
    labels = [label for label, _minimum, _maximum in rows]
    display_labels = [
        _display_label_for_likelihood(group_key, label) for label in labels
    ]
    minimums = [minimum for _label, minimum, _maximum in rows]
    maximums = [maximum for _label, _minimum, maximum in rows]
    colors = [_color_for_likelihood(group_key, label) for label in labels]
    ax.set_facecolor("#111111")
    ax.figure.patch.set_facecolor("#111111")
    if not rows:
        ax.text(
            0.5,
            0.5,
            "No raw weight range data available.",
            ha="center",
            va="center",
            color="#f5f5f5",
        )
        ax.set_axis_off()
        return

    x_positions = list(range(len(rows)))
    bars = ax.bar(
        x_positions,
        maximums,
        color=colors,
        alpha=0.72,
        edgecolor="#f5f5f5",
        linewidth=0.25,
    )
    ax.bar(x_positions, minimums, color="#111111", alpha=0.50, edgecolor="none")
    hover_payloads = []
    clickable_artists = []
    for bar, label, display_label, minimum, maximum in zip(
        bars, labels, display_labels, minimums, maximums, strict=True
    ):
        bar.set_gid(f"time_sensitivity:{group_key}:{label}")
        bar.set_picker(True)
        setattr(bar, "_time_sensitivity_factor", label)
        clickable_artists.append((bar, label))
        hover_payloads.append(
            (bar, f"{display_label}\nmin {minimum:.0f} • max {maximum:.0f}")
        )
    _install_bar_hover(ax, hover_payloads)
    ax.set_xticks(x_positions, display_labels)
    for tick_label, label in zip(ax.get_xticklabels(), labels, strict=True):
        tick_label.set_picker(True)
        tick_label.set_gid(f"time_sensitivity:{group_key}:{label}:label")
        setattr(tick_label, "_time_sensitivity_factor", label)
        clickable_artists.append((tick_label, label))
    if callable(on_factor_click):
        _install_factor_click(ax, clickable_artists, on_factor_click)
    y_max = max(maximums) if maximums else 0.0
    ax.set_ylim(0, max(1.0, y_max * 1.12))
    ax.set_ylabel("raw weight range", color="#f5f5f5", fontsize=8)
    ax.set_title(
        _TIME_SENSITIVITY_CHART_TITLES.get(group_key, group_key),
        color="#f5f5f5",
        fontsize=10,
        fontweight="bold",
    )
    ax.tick_params(axis="x", colors="#f5f5f5", labelrotation=90, labelsize=8)
    ax.tick_params(axis="y", colors="#f5f5f5", labelsize=8)
    ax.grid(axis="y", color="#333333", linewidth=0.5, alpha=0.8)
    for spine in ax.spines.values():
        spine.set_color("#555555")
    ax.figure.tight_layout()


def _install_factor_click(
    ax: Any, clickable_artists: list[tuple[Any, str]], on_factor_click: Any
) -> None:
    """Make Time Sensitivity bars and x-axis labels update the popout info panel."""

    def on_click(event: Any) -> None:
        for artist, label in clickable_artists:
            contains, _details = artist.contains(event)
            if contains:
                on_factor_click(label)
                return

    ax.figure.canvas.mpl_connect("button_press_event", on_click)


def _install_bar_hover(ax: Any, hover_payloads: list[tuple[Any, str]]) -> None:
    """Attach uncluttered on-hover labels to bars for Qt matplotlib canvases."""
    annotation = ax.annotate(
        "",
        xy=(0, 0),
        xytext=(10, 10),
        textcoords="offset points",
        bbox={"boxstyle": "round", "fc": "#222222", "ec": "#f5f5f5", "alpha": 0.92},
        color="#f5f5f5",
        fontsize=8,
    )
    annotation.set_visible(False)

    def on_motion(event: Any) -> None:
        if event.inaxes != ax:
            if annotation.get_visible():
                annotation.set_visible(False)
                ax.figure.canvas.draw_idle()
            return
        for bar, label in hover_payloads:
            contains, _details = bar.contains(event)
            if contains:
                annotation.xy = (bar.get_x() + (bar.get_width() / 2), bar.get_height())
                annotation.set_text(label)
                annotation.set_visible(True)
                ax.figure.canvas.draw_idle()
                return
        if annotation.get_visible():
            annotation.set_visible(False)
            ax.figure.canvas.draw_idle()

    ax.figure.canvas.mpl_connect("motion_notify_event", on_motion)


def _group_title(group_key: str) -> str:
    titles = {
        "dominant_planet_weights": "Dominant Bodies",
        "dominant_sign_weights": "Dominant Signs",
        "dominant_house_weights": "Dominant Houses",
        "dominant_element_weights": "Dominant Elements",
        "dominant_mode_weights": "Dominant Modes",
        "dominant_nakshatra_weights": "Dominant Nakshatras",
    }
    if group_key in titles:
        return titles[group_key]
    return (
        group_key.replace("dominant_", "Dominant ")
        .replace("_weights", "")
        .replace("_", " ")
        .title()
    )


_NUMERIC_GROUP_LINK_KINDS = {
    "dominant_planet_weights": "planet",
    "dominant_sign_weights": "sign",
    "dominant_house_weights": "house",
    "dominant_element_weights": "element",
    "dominant_mode_weights": "mode",
    "dominant_nakshatra_weights": "nakshatra",
}


def _confidence_color(percent: float) -> str:
    """Return a dark-red→bright-green confidence color for a 0–100 percentage."""
    ratio = max(0.0, min(1.0, float(percent) / 100.0))
    start = (0x7A, 0x00, 0x00)
    end = (0x00, 0xFF, 0x00)
    red = round(start[0] + ((end[0] - start[0]) * ratio))
    green = round(start[1] + ((end[1] - start[1]) * ratio))
    blue = round(start[2] + ((end[2] - start[2]) * ratio))
    return f"#{red:02x}{green:02x}{blue:02x}"


def _confidence_percent(result: TimeSensitivityResult) -> float:
    """Return relative confidence in what can be ascertained despite unknown birth time."""
    confidence = result.overall.get("ascertainment_confidence", {})
    if isinstance(confidence, dict) and "percent" in confidence:
        return max(0.0, min(100.0, float(confidence.get("percent", 0.0))))
    return max(0.0, min(100.0, float(result.overall.get("stability_percent", 0.0))))


def _delta_intensity_color(value: float, values: list[float]) -> str:
    """Return the app-wide red→lime sensitivity color relative to peer deltas."""
    finite_values = [max(0.0, float(candidate)) for candidate in values]
    if not finite_values:
        return "#7a0000"
    minimum = min(finite_values)
    maximum = max(finite_values)
    if maximum <= minimum:
        ratio = 1.0 if float(value) > 0.0 else 0.0
    else:
        ratio = (max(0.0, float(value)) - minimum) / (maximum - minimum)
    ratio = max(0.0, min(1.0, ratio))
    start = (0x7A, 0x00, 0x00)
    end = (0xB7, 0xFF, 0x00)
    red = round(start[0] + ((end[0] - start[0]) * ratio))
    green = round(start[1] + ((end[1] - start[1]) * ratio))
    blue = round(start[2] + ((end[2] - start[2]) * ratio))
    return f"#{red:02x}{green:02x}{blue:02x}"


def _relative_value_color(value: float, peer_values: list[float]) -> str:
    """Return the red→lime color for a value ranked against the same metric's peers."""
    finite_values = [float(candidate) for candidate in peer_values]
    if not finite_values:
        return "#7a0000"
    minimum = min(finite_values)
    maximum = max(finite_values)
    if maximum <= minimum:
        ratio = 1.0
    else:
        ratio = (float(value) - minimum) / (maximum - minimum)
    ratio = max(0.0, min(1.0, ratio))
    start = (0x7A, 0x00, 0x00)
    end = (0xB7, 0xFF, 0x00)
    red = round(start[0] + ((end[0] - start[0]) * ratio))
    green = round(start[1] + ((end[1] - start[1]) * ratio))
    blue = round(start[2] + ((end[2] - start[2]) * ratio))
    return f"#{red:02x}{green:02x}{blue:02x}"


def _factor_color(group_key: str, key: str) -> str:
    if group_key == "dominant_planet_weights":
        return str(PLANET_COLORS.get(key, "#6fa8dc"))
    if group_key == "dominant_sign_weights":
        return str(SIGN_COLORS.get(key, "#6fa8dc"))
    if group_key == "dominant_house_weights":
        return str(HOUSE_COLORS.get(str(key).removeprefix("House ").strip(), "#6fa8dc"))
    if group_key == "dominant_element_weights":
        return str(ELEMENT_COLORS.get(str(key).title(), "#6fa8dc"))
    if group_key == "dominant_mode_weights":
        return str(MODE_COLORS.get(str(key).lower(), "#6fa8dc"))
    if group_key == "dominant_nakshatra_weights":
        entry = NAKSHATRA_PLANET_COLOR.get(str(key))
        if entry:
            return str(entry[1])
        return "#d7b5ff"
    return "#6fa8dc"


_COLOR_CODE_TERMS: dict[str, tuple[str, str, str]] = {
    **{
        str(name): (str(color), "sign", str(name))
        for name, color in SIGN_COLORS.items()
    },
    **{
        str(name): (str(color), "planet", str(name))
        for name, color in PLANET_COLORS.items()
    },
    **{
        str(name): (str(color), "element", str(name))
        for name, color in ELEMENT_COLORS.items()
    },
    **{
        str(name).title(): (str(color), "mode", str(name))
        for name, color in MODE_COLORS.items()
    },
    **{
        str(name): (str(color), "nakshatra", str(name))
        for name, (_planet, color) in NAKSHATRA_PLANET_COLOR.items()
    },
    **{
        f"House {house}": (str(color), "house", str(house))
        for house, color in HOUSE_COLORS.items()
    },
}

_COLOR_CODE_PATTERN = re.compile(
    r"(?<![\w-])("
    + "|".join(
        re.escape(term) for term in sorted(_COLOR_CODE_TERMS, key=len, reverse=True)
    )
    + r")(?![\w-])",
    re.IGNORECASE,
)


def _color_code_text(text: str, *, sign_link_kind: str = "sign") -> str:
    """Escape text and turn known astrological category names into Chart Info links."""
    escaped_text = escape(str(text))

    def replace(match: re.Match[str]) -> str:
        matched = match.group(0)
        payload = _COLOR_CODE_TERMS.get(matched)
        if payload is None:
            payload = next(
                (
                    candidate_payload
                    for candidate_name, candidate_payload in _COLOR_CODE_TERMS.items()
                    if candidate_name.lower() == matched.lower()
                ),
                ("#6fa8dc", "", matched),
            )
        color, kind, value = payload
        safe_matched = escape(matched)
        link_kind = sign_link_kind if kind == "sign" else kind
        href = f"distinguishing-factor:{link_kind}:{quote(value)}" if link_kind else ""
        if href:
            return (
                f"<a href='{href}' style='color:{escape(color, quote=True)}; text-decoration: none;'>"
                f"{safe_matched}</a>"
            )
        return f"<span style='color:{escape(color, quote=True)};'>{safe_matched}</span>"

    return _COLOR_CODE_PATTERN.sub(replace, escaped_text)



def _time_sensitivity_variable_item_html(result: TimeSensitivityResult, item: str) -> str:
    text = str(item)
    if text.startswith("Ascendant:"):
        prefix, values_text = text.split(":", 1)
        linked_values = []
        for sign in [part.strip() for part in values_text.split("/") if part.strip()]:
            color = escape(SIGN_COLORS.get(sign.title(), "#6fa8dc"), quote=True)
            linked_values.append(
                f"<a href='distinguishing-factor:ts-ascendant-sign:{quote(sign.title())}' "
                f"style='color:{color}; text-decoration: none;'>{escape(sign)}</a>"
            )
        return f"{escape(prefix)}: " + " / ".join(linked_values)
    return _color_code_text(text, sign_link_kind="ts-sign")


def time_sensitivity_categorical_spans(
    result: TimeSensitivityResult | None, category: str, value: str
) -> list[str]:
    """Return sampled Time Sensitivity spans for a categorical value."""
    overall = getattr(result, "overall", {}) if result is not None else {}
    spans_by_category = (
        overall.get("categorical_value_spans", {}) if isinstance(overall, dict) else {}
    )
    spans_by_value = (
        spans_by_category.get(category, {}) if isinstance(spans_by_category, dict) else {}
    )
    spans = (
        spans_by_value.get(str(value or "").strip().title(), [])
        if isinstance(spans_by_value, dict)
        else []
    )
    return [str(span) for span in spans if str(span).strip()]


def build_time_sensitivity_ascendant_sign_info_text(
    result: TimeSensitivityResult | None, sign_name: str
) -> str:
    """Return Chart Info text for a Time Sensitivity Ascendant sign link."""
    sign_key = str(sign_name or "").strip().title()
    sign_keywords = SIGN_KEYWORDS.get(sign_key, {})
    best_keywords = [
        str(item).strip() for item in sign_keywords.get("best", []) if str(item).strip()
    ]
    worst_keywords = [
        str(item).strip() for item in sign_keywords.get("worst", []) if str(item).strip()
    ]
    spans = time_sensitivity_categorical_spans(result, "Ascendant", sign_key)
    if spans:
        start = spans[0].split("–", 1)[0].strip()
        end = spans[-1].split("–", 1)[-1].strip()
        time_line = f"from {start} to {end}"
    else:
        time_line = "from n/a to n/a"
    lines = [
        f"Ascendant in {sign_key}",
        "",
        time_line,
        "",
        "Interfacing with the world in a way that is…",
    ]
    if best_keywords:
        lines.extend(["At best:", *(f"• {keyword}" for keyword in best_keywords)])
    if worst_keywords:
        if best_keywords:
            lines.append("")
        lines.extend(["At worst:", *(f"• {keyword}" for keyword in worst_keywords)])
    return "\n".join(lines)


def build_time_sensitivity_sign_info_text(
    result: TimeSensitivityResult | None, chart: Any, sign_name: str
) -> str:
    """Return Chart Info text for a non-Ascendant Time Sensitivity sign link."""
    sign_key = str(sign_name or "").strip().title()
    sign_keywords = SIGN_KEYWORDS.get(sign_key, {})
    best_keywords = [
        str(item).strip() for item in sign_keywords.get("best", []) if str(item).strip()
    ]
    worst_keywords = [
        str(item).strip() for item in sign_keywords.get("worst", []) if str(item).strip()
    ]
    placements = []
    possible = []
    if chart is not None:
        sign_by_body = chart.signs() if hasattr(chart, "signs") else {}
        for body in PLANET_ORDER:
            if str(sign_by_body.get(body, "")).strip().title() == sign_key:
                placements.append(_display_body_name(body))
        for category, label in (("Sun sign", "Sun"), ("Ascendant", "Ascendant")):
            if time_sensitivity_categorical_spans(result, category, sign_key):
                display_label = _display_body_name(label) if label != "Ascendant" else label
                if display_label not in placements and display_label not in possible:
                    possible.append(display_label)
    placement_line = ", ".join(placements)
    if placements:
        placement_line += "."
    if possible:
        possible_line = "Possibly " + ", ".join(possible)
        placement_line = f"{placement_line} {possible_line}" if placement_line else possible_line
    if not placement_line:
        placement_line = f"No chart placements in {sign_key}"
    lines = [sign_key, "", placement_line, ""]
    if best_keywords:
        lines.extend(["At best:", *(f"• {keyword}" for keyword in best_keywords)])
    if worst_keywords:
        if best_keywords:
            lines.append("")
        lines.extend(["At worst:", *(f"• {keyword}" for keyword in worst_keywords)])
    return "\n".join(lines)

def _header_html(label: str) -> str:
    return f"<div style='color:{CHART_DATA_HIGHLIGHT_COLOR}; font-weight:700; margin-top:8px;'>{escape(label)}</div>"


def _list_html(items: list[str]) -> str:
    return (
        "<ul style='margin-top:2px; margin-bottom:6px;'>"
        + "".join(f"<li>{item}</li>" for item in items)
        + "</ul>"
    )


def _factor_link(group_key: str, key: str) -> str:
    kind = _NUMERIC_GROUP_LINK_KINDS.get(group_key, "")
    value = str(key).removeprefix("House ").strip() if kind == "house" else str(key)
    return f"distinguishing-factor:{kind}:{quote(value)}" if kind else ""


def _format_time_list(values: Any, limit: int = 3) -> str:
    if not values:
        return "n/a"
    if isinstance(values, (list, tuple)):
        return ", ".join(str(value) for value in values[:limit]) or "n/a"
    return str(values)


def _single_time_value(values: Any) -> str:
    """Return one compact time value for peak/trench table cells."""
    if not values:
        return "n/a"
    first = str(values[0] if isinstance(values, (list, tuple)) else values)
    if "–" in first:
        first = first.split("–", 1)[0]
    return first.strip() or "n/a"


def _variability_scale_label(percent_delta_spread: float) -> str:
    """Return a compact label for the spread between min and max percent deltas."""
    spread = abs(float(percent_delta_spread))
    if spread < 5.0:
        return "minimal"
    if spread < 15.0:
        return "minor"
    if spread < 35.0:
        return "medium"
    if spread < 75.0:
        return "high"
    return "extreme"


def _variability_percent_spread(payload: dict[str, Any]) -> float:
    if "variability_percent" in payload:
        return abs(float(payload.get("variability_percent", 0.0)))
    max_decrease = float(payload.get("max_decrease_percent", 0.0))
    max_increase = float(payload.get("max_increase_percent", 0.0))
    return abs(max_increase - max_decrease)


def _variability_text(payload: dict[str, Any]) -> str:
    return _variability_scale_label(_variability_percent_spread(payload))


def _time_sensitivity_factor_info_html(
    result: TimeSensitivityResult, group_key: str, key: str
) -> str:
    payload = result.numeric_ranges.get(group_key, {}).get(key, {})
    if not isinstance(payload, dict):
        return "<div>No Time Sensitivity details available for that factor.</div>"
    display = _display_label_for_likelihood(group_key, key)
    color = escape(_factor_color(group_key, key), quote=True)
    minimum = float(payload.get("min", 0.0))
    maximum = float(payload.get("max", 0.0))
    trough_time = _single_time_value(
        payload.get("trough_times") or payload.get("trough_spans")
    )
    peak_time = _single_time_value(
        payload.get("peak_times") or payload.get("peak_spans")
    )
    return (
        "<div style='white-space:normal;'>"
        f"<div style='font-size:14px; font-weight:700; color:{color};'>{escape(display)}</div>"
        #"<table style='border-collapse:collapse; margin-top:6px; font-size:12px;'>"
        f"<b>Min dominance</b>{escape(f'{minimum:.0f}')} at {escape(trough_time)}</br>"
        f"<b>Max dominance</b>{escape(f'{maximum:.0f}')} at {escape(peak_time)}"
        #f"<tr><td><b>Trench time</b></td><td style='padding-left:12px;'>{escape(trough_time)}</td></tr>"
        #f"<tr><td><b>Peak time</b></td><td style='padding-left:12px;'>{escape(peak_time)}</td></tr>"
        #"</table>"
        "</div>"
    )


def _numeric_group_table_html(result: TimeSensitivityResult, group_key: str) -> str:
    ranges = result.numeric_ranges.get(group_key, {})
    meaningful = [
        (str(key), payload)
        for key, payload in ranges.items()
        if isinstance(payload, dict)
        and (
            float(payload.get("delta", 0.0)) > 0.0
            or float(payload.get("baseline", 0.0)) > 0.0
            or float(payload.get("max", 0.0)) > 0.0
        )
    ]
    meaningful.sort(key=lambda item: float(item[1].get("max", 0.0)), reverse=True)
    if not meaningful:
        return "<div>No weighted results available.</div>"
    min_values = [float(payload.get("min", 0.0)) for _key, payload in meaningful]
    max_values = [float(payload.get("max", 0.0)) for _key, payload in meaningful]
    decrease_values = [
        float(payload.get("max_decrease_percent", 0.0)) for _key, payload in meaningful
    ]
    increase_values = [
        float(payload.get("max_increase_percent", 0.0)) for _key, payload in meaningful
    ]
    rows = []
    row_backgrounds = ("#111111", "#2b2b2b")
    for row_index, (key, payload) in enumerate(meaningful):
        trough_time = _single_time_value(
            payload.get("trough_times") or payload.get("trough_spans")
        )
        peak_time = _single_time_value(
            payload.get("peak_times") or payload.get("peak_spans")
        )
        minimum = float(payload.get("min", 0.0))
        maximum = float(payload.get("max", 0.0))
        max_decrease = float(payload.get("max_decrease_percent", 0.0))
        max_increase = float(payload.get("max_increase_percent", 0.0))
        min_color = escape(_relative_value_color(minimum, min_values), quote=True)
        max_color = escape(_relative_value_color(maximum, max_values), quote=True)
        decrease_color = escape(
            _relative_value_color(max_decrease, decrease_values), quote=True
        )
        increase_color = escape(
            _relative_value_color(max_increase, increase_values), quote=True
        )
        row_background = row_backgrounds[row_index % len(row_backgrounds)]
        rows.append(
            f"<tr style='background-color:{row_background};'>"
            f"<td>{_factor_anchor(group_key, key)}</td>"
            f"<td align='right' style='color:{min_color};'>{escape(f'{minimum:.0f}')}</td>"
            f"<td align='right' style='color:{max_color};'>{escape(f'{maximum:.0f}')}</td>"
            f"<td>{escape(trough_time)}</td>"
            f"<td>{escape(peak_time)}</td>"
            f"<td align='right' style='color:{decrease_color};'>{escape(f'{max_decrease:.0f}')}</td>"
            f"<td align='right' style='color:{increase_color};'>{escape(f'{max_increase:.0f}')}</td>"
            f"<td>{escape(_variability_text(payload))}</td>"
            "</tr>"
        )
    return (
        "<table style='border-collapse:collapse; border:0; width:100%; font-size:11px;'>"
        "<thead><tr>"
        "<th align='left'>factor</th>"  # body/sign/nak./H/el./mode
        "<th align='right'>min</th>"
        "<th align='right'>max</th>"
        "<th align='center'>trench</th>"
        "<th align='center'>peak</th>"
        "<th align='right'>-%△</th>"
        "<th align='right'>+%△</th>"
        "<th align='left'>var.</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _factor_anchor(group_key: str, key: str) -> str:
    color = escape(_factor_color(group_key, key), quote=True)
    text = escape(
        _display_body_name(key) if group_key == "dominant_planet_weights" else str(key)
    )
    href = _factor_link(group_key, key)
    if not href:
        return f"<span style='color:{color};'>{text}</span>"
    return (
        f"<a href='{href}' style='color:{color}; text-decoration: none;'>" f"{text}</a>"
    )


def _gate_anchor(gate: str) -> str:
    gate_text = str(gate).strip()
    gate_number_text = gate_text.split(".", 1)[0].split("-", 1)[0]
    try:
        color = str(GATE_COLORS.get(int(gate_number_text), "#6fa8dc"))
    except ValueError:
        color = "#6fa8dc"
    safe_gate = escape(gate_text, quote=True)
    if "." in gate_text:
        gate_number, line_number = gate_text.split(".", 1)
        href = (
            f"distinguishing-factor:gate-line:{quote(gate_number)}:{quote(line_number)}"
        )
    elif "-" not in gate_text:
        href = f"distinguishing-factor:gate:{quote(gate_text)}"
    else:
        href = f"distinguishing-factor:hd-channel:{quote(gate_text)}"
    return (
        f"<a href='{href}' style='color:{escape(color, quote=True)}; text-decoration: none;'>"
        f"{safe_gate}</a>"
    )


def _hd_property_anchor(property_key: str, value: str) -> str:
    safe_value = escape(str(value), quote=True)
    href = (
        f"distinguishing-factor:hd-property:{quote(property_key)}:{quote(str(value))}"
    )
    return f"<a href='{href}' style='color:#d7b5ff; text-decoration:none;'>{safe_value}</a>"


def format_time_sensitivity_result_html(result: TimeSensitivityResult) -> str:
    """Return compact rich text for the Chart View Time Sensitivity panel."""
    return _summary_html(result) + _human_design_html(result)


def _summary_html(result: TimeSensitivityResult) -> str:
    """Return the overview/stability summary HTML."""
    overall = result.overall
    baseline_label = (
        f"{result.baseline_time} ({overall.get('baseline_source', 'baseline')})"
    )
    html_lines: list[str] = [
        f"<div><strong>Overall stability:</strong> {float(overall.get('stability_percent', 0)):.0f}%</div>",
        f"<div><strong>Max possible change from {escape(baseline_label)}:</strong> {float(overall.get('max_total_change_from_baseline_percent', 0)):.0f}%</div>",
        "<div><strong>Most sensitive:</strong> "
        + _color_code_text(", ".join(overall.get("most_sensitive", []) or ["n/a"]))
        + "</div>",
        "<div><strong>Least sensitive:</strong> "
        + _color_code_text(", ".join(overall.get("least_sensitive", []) or ["n/a"]))
        + "</div>",
        f"<div><strong>Samples:</strong> {result.sample_count} hypothetical standard charts + {result.sample_count} Human Design charts</div>",
        _header_html("Highly Stable:"),
    ]
    html_lines.append(
        _list_html(
            [
                _color_code_text(item, sign_link_kind="ts-sign")
                for item in (result.stable or ["No all-day stable highlights found."])
            ]
        )
    )
    html_lines.append(_header_html("Variable:"))
    html_lines.append(
        _list_html(
            [
                _time_sensitivity_variable_item_html(result, item)
                for item in (result.variable or ["No categorical variability found."])
            ]
        )
    )

    if result.warnings:
        html_lines.append(_header_html("Warnings:"))
        html_lines.append(_list_html([escape(warning) for warning in result.warnings]))
    return "<div style='white-space: normal;'>" + "\n".join(html_lines) + "</div>"


def _human_design_html(result: TimeSensitivityResult) -> str:
    """Return Human Design Time Sensitivity details with Chart Info links."""
    hd = result.human_design
    hd_items = []
    for key in ("gates", "lines", "channels"):
        summary = hd.get(key, {})
        always = (
            ", ".join(_gate_anchor(item) for item in summary.get("always", [])[:20])
            or "none"
        )
        sometimes = (
            ", ".join(_gate_anchor(item) for item in summary.get("sometimes", [])[:20])
            or "none"
        )
        hd_items.append(f"Definite {escape(key.title())}: {always}")
        hd_items.append(f"Possible {escape(key.title())}: {sometimes}")
    type_bits = [
        f"{_hd_property_anchor('type', str(k))} ({int(v)})"
        for k, v in hd.get("type_distribution", {}).items()
        if str(k)
    ]
    profile_bits = [
        f"{_hd_property_anchor('profile', str(k))} ({int(v)})"
        for k, v in hd.get("profile_distribution", {}).items()
        if str(k)
    ]
    hd_items.append("Possible Types: " + (", ".join(type_bits) or "none"))
    hd_items.append("Possible Profiles: " + (", ".join(profile_bits) or "none"))
    return "<div style='white-space: normal;'>" + _list_html(hd_items) + "</div>"


def _legacy_full_html(result: TimeSensitivityResult) -> str:
    """Return the older full inline summary used by tests and fallback display."""
    html_lines: list[str] = [_summary_html(result)]
    for group_key, ranges in result.numeric_ranges.items():
        if group_key in _NUMERIC_GROUP_LINK_KINDS:
            continue
        meaningful = [
            (key, payload)
            for key, payload in ranges.items()
            if float(payload.get("delta", 0.0)) > 0.0
            or float(payload.get("baseline", 0.0)) > 0.0
        ]
        meaningful.sort(
            key=lambda item: float(item[1].get("percent_delta", 0.0)), reverse=True
        )
        delta_values = [
            abs(float(payload.get("percent_delta", 0.0)))
            for _key, payload in meaningful
        ]
        min_values = [float(payload.get("min", 0.0)) for _key, payload in meaningful]
        max_values = [float(payload.get("max", 0.0)) for _key, payload in meaningful]
        html_lines.append(_header_html(_group_title(group_key)))
        group_items = []
        for key, payload in meaningful[:12]:
            appears_after = payload.get("appears_after")
            suffix = (
                f" appears after {appears_after}"
                if appears_after
                else f" {payload.get('label', '')}"
            )
            span_bits = []
            if payload.get("present_spans"):
                span_bits.append(
                    "present " + "; ".join(payload.get("present_spans", [])[:6])
                )
            if payload.get("peak_spans"):
                span_bits.append(
                    "peaks " + "; ".join(payload.get("peak_spans", [])[:6])
                )
            if payload.get("transition_windows"):
                span_bits.append(
                    "changes " + "; ".join(payload.get("transition_windows", [])[:8])
                )
            tooltip = " | ".join(span_bits) or "No sampled time-span changes."
            delta_color = escape(
                _delta_intensity_color(
                    abs(float(payload.get("percent_delta", 0.0))), delta_values
                ),
                quote=True,
            )
            minimum = float(payload.get("min", 0.0))
            maximum = float(payload.get("max", 0.0))
            min_color = escape(_relative_value_color(minimum, min_values), quote=True)
            max_color = escape(_relative_value_color(maximum, max_values), quote=True)
            group_items.append(
                "<span title='"
                + escape(tooltip, quote=True)
                + "'>"
                + f"{_factor_anchor(group_key, str(key))} "
                + f"<span style='color:{min_color};'>{escape(f'{minimum:.0f}')}</span>"
                + escape("–")
                + f"<span style='color:{max_color};'>{escape(f'{maximum:.0f}')}</span>"
                + escape(
                    f"   peak {', '.join(payload.get('peak_times', [])[:3]) or 'n/a'}   vs {result.baseline_time}: "
                )
                + f"<span style='color:{delta_color};'>"
                + escape(
                    f"{float(payload.get('max_decrease_percent', 0.0)):+.0f}% to {float(payload.get('max_increase_percent', 0.0)):+.0f}%"
                )
                + "</span>"
                + escape(f"{suffix}".replace("Highly variable", "high"))
                + "</span>"
            )
        html_lines.append(_list_html(group_items))

    html_lines.append(_header_html("Human Design"))
    html_lines.append(_human_design_html(result))
    return "<div style='white-space: normal;'>" + "\n".join(html_lines) + "</div>"


class TimeSensitivityPanel(QWidget):
    """Right-panel widget that computes sampled Time/Rectification Sensitivity."""

    def __init__(self, owner: object) -> None:
        super().__init__()
        self._owner = owner
        self._last_result: TimeSensitivityResult | None = None
        self._chart_date_key: str = ""
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignTop)
        self.setLayout(layout)

        title = QLabel("Time/Rectification Sensitivity")
        title.setStyleSheet("font-weight: 700; font-size: 13px;")
        layout.addWidget(title)

        self.confidence_label = QLabel("")
        self.confidence_label.setWordWrap(True)
        self.confidence_label.setVisible(False)
        layout.addWidget(self.confidence_label)

        description = QLabel(
            "Scans hypothetical birth times across the known birth day and summarizes how much the chart can change."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        self.compute_module = QWidget()
        compute_module_layout = QVBoxLayout()
        compute_module_layout.setContentsMargins(0, 0, 0, 0)
        compute_module_layout.setSpacing(6)
        self.compute_module.setLayout(compute_module_layout)

        refinement_row = QHBoxLayout()
        self.boundary_refinement_checkbox = QCheckBox("boundary refinement")
        self.boundary_refinement_checkbox.setEnabled(False)
        self.boundary_refinement_checkbox.setToolTip(
            "examines thresholds of change; takes longer but more accurate"
        )
        refinement_info = QLabel("ⓘ")
        refinement_info.setToolTip(
            "examines thresholds of change; takes longer but more accurate"
        )
        refinement_row.addWidget(self.boundary_refinement_checkbox)
        refinement_row.addWidget(refinement_info)
        refinement_row.addStretch(1)
        compute_module_layout.addLayout(refinement_row)

        controls = QHBoxLayout()
        self.interval_combo = QComboBox()
        self.interval_combo.addItem("30 min intervals", 30)
        self.compute_button = QPushButton("Compute Range")
        self.compute_button.clicked.connect(self.compute_range)
        controls.addWidget(self.interval_combo)
        controls.addWidget(self.compute_button)
        compute_module_layout.addLayout(controls)
        layout.addWidget(self.compute_module)

        self._chart_canvases: dict[str, FigureCanvas] = {}
        self._chart_sections: dict[str, QWidget] = {}
        self._charts_layout = QVBoxLayout()
        self._charts_layout.setContentsMargins(0, 0, 0, 0)
        self._charts_layout.setSpacing(8)
        layout.addLayout(self._charts_layout)

        self.output = QTextBrowser()
        self.output.setReadOnly(True)
        self.output.setOpenExternalLinks(False)
        self.output.setOpenLinks(False)
        self.output.anchorClicked.connect(self._open_chart_info_link)
        self.output.setMinimumHeight(80)
        self.output.setPlainText(
            "Click Compute Range to scan 49 sampled times: every 30 minutes plus 23:59."
        )
        layout.addWidget(self.output)

    def _current_chart(self) -> Any | None:
        return getattr(self._owner, "_latest_chart", None)

    def _current_config(self) -> TimeSensitivityConfig:
        return TimeSensitivityConfig(
            interval_minutes=int(self.interval_combo.currentData() or 30),
            include_day_end=True,
            baseline_time=None,
            boundary_refinement=False,
        )

    def _set_confidence_for_result(self, result: TimeSensitivityResult | None) -> None:
        chart = self._current_chart()
        if (
            result is None
            or chart is None
            or not bool(getattr(chart, "birthtime_unknown", False))
        ):
            self.confidence_label.clear()
            self.confidence_label.setVisible(False)
            return
        confidence = _confidence_percent(result)
        color = escape(_confidence_color(confidence), quote=True)
        self.confidence_label.setText(
            f"<i><span style='color:{color};'>Confidence: {confidence:.0f}%</span></i>"
        )
        self.confidence_label.setToolTip(
            "Confidence estimates how much useful chart information remains ascertainable across the sampled day: "
            "planetary signs, angle/house ambiguity, Human Design stability, element/mode/nakshatra stability, "
            "dominance consistency, and weighted-score volatility."
        )
        self.confidence_label.setVisible(True)

    def refresh_for_current_chart(self) -> None:
        chart = self._current_chart()
        date_key = birth_date_key_for_chart(chart) if chart is not None else ""
        if date_key == self._chart_date_key:
            self._set_confidence_for_result(self._last_result)
            return
        self._chart_date_key = date_key
        self._last_result = None
        if chart is None:
            self.compute_module.setVisible(False)
            self._set_confidence_for_result(None)
            self.output.setPlainText("No active chart is loaded.")
            self._clear_weight_sections()
            return
        saved = load_time_sensitivity_result_for_chart(chart, self._current_config())
        if saved is not None:
            self._last_result = saved
            self._set_confidence_for_result(saved)
            self.output.setHtml(format_time_sensitivity_result_html(saved))
            self._render_weight_sections(saved)
            self.compute_module.setVisible(False)
            return
        self._set_confidence_for_result(None)
        self.compute_module.setVisible(bool(date_key))
        if date_key:
            self.output.setPlainText(
                f"No saved Time/Rectification Sensitivity range for {date_key}. "
                "Click Compute Range to scan 49 sampled times: every 30 minutes plus 23:59."
            )
        else:
            self.output.setPlainText(
                "No usable birth date found for Time/Rectification Sensitivity storage."
            )
        self._clear_weight_sections()

    def compute_range(self) -> None:
        chart = self._current_chart()
        if chart is None:
            self.compute_module.setVisible(False)
            self._set_confidence_for_result(None)
            self.output.setPlainText("No active chart is loaded.")
            return
        self.compute_button.setEnabled(False)
        self.output.setPlainText("Computing Time/Rectification Sensitivity…")
        try:
            config = self._current_config()
            self._last_result = compute_time_sensitivity(chart, config)
            self._chart_date_key = birth_date_key_for_chart(chart)
            save_time_sensitivity_result(self._last_result)
            self._set_confidence_for_result(self._last_result)
            self.output.setHtml(format_time_sensitivity_result_html(self._last_result))
            self._render_weight_sections(self._last_result)
            self.compute_module.setVisible(False)
        except Exception as exc:
            self._last_result = None
            self._set_confidence_for_result(None)
            self.output.setPlainText(
                f"Unable to compute Time/Rectification Sensitivity:\n{exc}"
            )
            self._clear_weight_sections()
        finally:
            self.compute_button.setEnabled(True)

    def _open_chart_info_link(self, url: QUrl) -> None:
        target = url.toString()
        set_mode = getattr(self._owner, "_set_chart_info_panel_mode", None)
        if callable(set_mode):
            set_mode("chart_info")
        handler = getattr(self._owner, "_on_distinguishing_factor_link_activated", None)
        if callable(handler):
            handler(target)

    def _clear_weight_sections(self) -> None:
        for section in self._chart_sections.values():
            section.setParent(None)
            section.deleteLater()
        self._chart_sections = {}
        self._chart_canvases = {}
        self.output.show()

    def _add_html_section(
        self, section_key: str, title: str, html: str, *, expanded: bool = True
    ) -> QWidget:
        section = QWidget()
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(0)
        toggle = QToolButton(section)
        configure_collapsible_header_toggle(
            toggle,
            title=title,
            expanded=expanded,
            style_sheet=DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE,
        )
        content = QWidget(section)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(*DATABASE_ANALYTICS_CONTENT_MARGINS)
        content_layout.setSpacing(DATABASE_ANALYTICS_CONTENT_SPACING)
        content.setStyleSheet(COLLAPSIBLE_SECTION_CONTENT_STYLE)
        content.setVisible(expanded)
        toggle.toggled.connect(
            lambda checked, body=content, button=toggle: (
                body.setVisible(checked),
                button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow),
            )
        )
        section_layout.addWidget(toggle)
        section_layout.addWidget(content)
        browser = QTextBrowser(content)
        browser.setReadOnly(True)
        browser.setOpenExternalLinks(False)
        browser.setOpenLinks(False)
        browser.anchorClicked.connect(self._open_chart_info_link)
        browser.setFrameShape(QFrame.NoFrame)
        browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        browser.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        browser.setHtml(html)
        browser.document().setTextWidth(max(1, browser.viewport().width()))
        browser.document().adjustSize()
        height = int(browser.document().size().height()) + 18
        max_height = 16777215 if section_key == "human_design" else 700
        browser.setFixedHeight(max(48, min(max_height, height)))
        content_layout.addWidget(browser)
        self._charts_layout.addWidget(section)
        self._chart_sections[section_key] = section
        return section

    def _render_weight_sections(self, result: TimeSensitivityResult) -> None:
        self._clear_weight_sections()
        self.output.hide()
        self._add_html_section(
            "summary", "Overall Time Sensitivity", _summary_html(result), expanded=True
        )
        for group_key in (
            "dominant_planet_weights",
            "dominant_sign_weights",
            "dominant_element_weights",
            "dominant_house_weights",
            "dominant_mode_weights",
            "dominant_nakshatra_weights",
        ):
            table_html = _numeric_group_table_html(result, group_key)
            if not table_html.startswith("<table"):
                continue
            section = QWidget()
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(0)
            toggle = QToolButton(section)
            configure_collapsible_header_toggle(
                toggle,
                title=_group_title(group_key),
                expanded=True,
                style_sheet=DATABASE_ANALYTICS_COLLAPSIBLE_TOGGLE_STYLE,
            )
            content = QWidget(section)
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(*DATABASE_ANALYTICS_CONTENT_MARGINS)
            content_layout.setSpacing(DATABASE_ANALYTICS_CONTENT_SPACING)
            content.setStyleSheet(COLLAPSIBLE_SECTION_CONTENT_STYLE)
            toggle.toggled.connect(
                lambda checked, body=content, button=toggle: (
                    body.setVisible(checked),
                    button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow),
                )
            )
            section_layout.addWidget(toggle)
            section_layout.addWidget(content)

            canvas = None
            if group_key in _TIME_SENSITIVITY_CHART_TITLES:
                figure = Figure(figsize=(5.5, 2.8))
                ax = figure.add_subplot(111)
                _draw_likelihood_chart(ax, result, group_key)
                canvas = TimeSensitivityFigureCanvas(figure)
                canvas.setMinimumHeight(250)
                canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                canvas.setToolTip(
                    "Click to open a larger Time Sensitivity raw-weight range popout."
                )
                canvas.mpl_connect(
                    "button_press_event",
                    lambda _event, key=group_key: self._show_likelihood_popout(key),
                )
                content_layout.addWidget(canvas)

            table = QTextBrowser(content)
            table.setReadOnly(True)
            table.setOpenExternalLinks(False)
            table.setOpenLinks(False)
            table.anchorClicked.connect(self._open_chart_info_link)
            table.setFrameShape(QFrame.NoFrame)
            table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
            table.setHtml(_header_html(_group_title(group_key)) + table_html)
            table.document().setTextWidth(max(1, table.viewport().width()))
            table.document().adjustSize()
            table_height = int(table.document().size().height()) + 14
            table.setFixedHeight(max(82, min(900, table_height)))
            content_layout.addWidget(table)

            self._charts_layout.addWidget(section)
            if canvas is not None:
                canvas.draw_idle()
                self._chart_canvases[group_key] = canvas
            self._chart_sections[group_key] = section
        self._add_html_section(
            "human_design", "Human Design", _human_design_html(result), expanded=False
        )

    def _show_likelihood_popout(self, group_key: str) -> None:
        result = self._last_result
        if result is None:
            return
        dialog = QDialog(self)
        title = _TIME_SENSITIVITY_CHART_TITLES.get(group_key, "Dominance Likelihood")
        dialog.setWindowTitle(title)
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.setMinimumSize(820, 560)
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        figure = Figure(figsize=(8.5, 4.6))
        ax = figure.add_subplot(111)
        canvas = TimeSensitivityFigureCanvas(figure)
        info = QTextEdit()
        info.setReadOnly(True)

        def show_factor_info(label: str) -> None:
            info.setHtml(_time_sensitivity_factor_info_html(result, group_key, label))

        _draw_likelihood_chart(ax, result, group_key, on_factor_click=show_factor_info)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(canvas, 1)
        info.setHtml(
            "<b>Raw weight range:</b> each bar shows the maximum raw weight reached by that factor; "
            "the darker base marks its minimum raw weight across the sampled charts. Click a bar "
            "or x-axis label to show that factor's min/max dominance plus peak and trench times."
        )
        info.setMaximumHeight(96)
        layout.addWidget(info)
        canvas.draw_idle()
        register = getattr(self._owner, "_register_popout_shortcuts", None)
        if callable(register):
            register(dialog)
        dialog.show()
