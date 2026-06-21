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
    SIGN_COLORS,
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


_TIME_SENSITIVITY_CHART_TITLES = {
    "dominant_planet_weights": "Dominant Body Weight Distribution",
    "dominant_sign_weights": "Dominant Sign Weight Distribution",
}


def _likelihood_rows(result: TimeSensitivityResult, group_key: str) -> list[tuple[str, float]]:
    """Return non-zero average raw-weight rows for Time Sensitivity charts."""
    ranges = result.numeric_ranges.get(group_key, {})
    rows = [
        (str(key), (float(payload.get("min", 0.0)) + float(payload.get("max", 0.0))) / 2.0)
        for key, payload in ranges.items()
        if isinstance(payload, dict) and float(payload.get("max", 0.0)) > 0.0
    ]
    return sorted(rows, key=lambda item: (-item[1], item[0]))


def _raw_weight_range_rows(result: TimeSensitivityResult, group_key: str) -> list[tuple[str, float, float]]:
    """Return labels with min/max raw weights across sampled charts."""
    ranges = result.numeric_ranges.get(group_key, {})
    rows = [
        (str(key), float(payload.get("min", 0.0)), float(payload.get("max", 0.0)))
        for key, payload in ranges.items()
        if isinstance(payload, dict) and float(payload.get("max", 0.0)) > 0.0
    ]
    return sorted(rows, key=lambda item: (-item[2], item[0]))


def _color_for_likelihood(group_key: str, label: str) -> str:
    if group_key == "dominant_sign_weights":
        return str(SIGN_COLORS.get(label, "#6fa8dc"))
    return str(PLANET_COLORS.get(label, "#6fa8dc"))


def _display_label_for_likelihood(group_key: str, label: str) -> str:
    if group_key == "dominant_planet_weights":
        return _display_body_name(label)
    return label


def _draw_likelihood_chart(ax: Any, result: TimeSensitivityResult, group_key: str) -> None:
    rows = _raw_weight_range_rows(result, group_key)
    labels = [label for label, _minimum, _maximum in rows]
    display_labels = [_display_label_for_likelihood(group_key, label) for label in labels]
    minimums = [minimum for _label, minimum, _maximum in rows]
    maximums = [maximum for _label, _minimum, maximum in rows]
    colors = [_color_for_likelihood(group_key, label) for label in labels]
    ax.set_facecolor("#111111")
    ax.figure.patch.set_facecolor("#111111")
    if not rows:
        ax.text(0.5, 0.5, "No raw weight range data available.", ha="center", va="center", color="#f5f5f5")
        ax.set_axis_off()
        return

    x_positions = list(range(len(rows)))
    bars = ax.bar(x_positions, maximums, color=colors, alpha=0.72, edgecolor="#f5f5f5", linewidth=0.25)
    ax.bar(x_positions, minimums, color="#111111", alpha=0.50, edgecolor="none")
    hover_payloads = []
    for bar, label, display_label, minimum, maximum in zip(bars, labels, display_labels, minimums, maximums, strict=True):
        bar.set_gid(f"time_sensitivity:{group_key}:{label}")
        bar.set_picker(True)
        hover_payloads.append((bar, f"{display_label}\nmin {minimum:.0f} • max {maximum:.0f}"))
    _install_bar_hover(ax, hover_payloads)
    ax.set_xticks(x_positions, display_labels)
    y_max = max(maximums) if maximums else 0.0
    ax.set_ylim(0, max(1.0, y_max * 1.12))
    ax.set_ylabel("raw weight range", color="#f5f5f5", fontsize=8)
    ax.set_title(_TIME_SENSITIVITY_CHART_TITLES.get(group_key, group_key), color="#f5f5f5", fontsize=10, fontweight="bold")
    ax.tick_params(axis="x", colors="#f5f5f5", labelrotation=90, labelsize=8)
    ax.tick_params(axis="y", colors="#f5f5f5", labelsize=8)
    ax.grid(axis="y", color="#333333", linewidth=0.5, alpha=0.8)
    for spine in ax.spines.values():
        spine.set_color("#555555")
    ax.figure.tight_layout()


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
    return group_key.replace("dominant_", "Dominant ").replace("_weights", "").replace("_", " ").title()


_NUMERIC_GROUP_LINK_KINDS = {
    "dominant_planet_weights": "planet",
    "dominant_sign_weights": "sign",
    "dominant_house_weights": "house",
    "dominant_element_weights": "element",
    "dominant_mode_weights": "mode",
    "dominant_nakshatra_weights": "nakshatra",
}


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
    **{str(name): (str(color), "sign", str(name)) for name, color in SIGN_COLORS.items()},
    **{str(name): (str(color), "planet", str(name)) for name, color in PLANET_COLORS.items()},
    **{str(name): (str(color), "element", str(name)) for name, color in ELEMENT_COLORS.items()},
    **{str(name).title(): (str(color), "mode", str(name)) for name, color in MODE_COLORS.items()},
    **{str(name): (str(color), "nakshatra", str(name)) for name, (_planet, color) in NAKSHATRA_PLANET_COLOR.items()},
    **{f"House {house}": (str(color), "house", str(house)) for house, color in HOUSE_COLORS.items()},
}

_COLOR_CODE_PATTERN = re.compile(
    r"(?<![\w-])("
    + "|".join(re.escape(term) for term in sorted(_COLOR_CODE_TERMS, key=len, reverse=True))
    + r")(?![\w-])",
    re.IGNORECASE,
)


def _color_code_text(text: str) -> str:
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
        href = f"distinguishing-factor:{kind}:{quote(value)}" if kind else ""
        if href:
            return (
                f"<a href='{href}' style='color:{escape(color, quote=True)}; text-decoration: none;'>"
                f"{safe_matched}</a>"
            )
        return f"<span style='color:{escape(color, quote=True)};'>{safe_matched}</span>"

    return _COLOR_CODE_PATTERN.sub(replace, escaped_text)

def _header_html(label: str) -> str:
    return f"<div style='color:{CHART_DATA_HIGHLIGHT_COLOR}; font-weight:700; margin-top:8px;'>{escape(label)}</div>"


def _list_html(items: list[str]) -> str:
    return "<ul style='margin-top:2px; margin-bottom:6px;'>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


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


def _span_start_end(values: Any) -> tuple[str, str]:
    """Return the first displayed span split into start/end time cells."""
    if not values:
        return "n/a", "n/a"
    first = str(values[0] if isinstance(values, (list, tuple)) else values)
    if "–" in first:
        start, end = first.split("–", 1)
        return start.strip() or "n/a", end.strip() or "n/a"
    return first.strip() or "n/a", first.strip() or "n/a"


def _variability_text(payload: dict[str, Any]) -> str:
    return str(payload.get("label", "")).replace("Highly variable", "high") or "n/a"


def _numeric_group_table_html(result: TimeSensitivityResult, group_key: str) -> str:
    ranges = result.numeric_ranges.get(group_key, {})
    meaningful = [
        (str(key), payload)
        for key, payload in ranges.items()
        if isinstance(payload, dict)
        and (float(payload.get("delta", 0.0)) > 0.0 or float(payload.get("baseline", 0.0)) > 0.0 or float(payload.get("max", 0.0)) > 0.0)
    ]
    meaningful.sort(key=lambda item: float(item[1].get("max", 0.0)), reverse=True)
    if not meaningful:
        return "<div>No weighted results available.</div>"
    min_values = [float(payload.get("min", 0.0)) for _key, payload in meaningful]
    max_values = [float(payload.get("max", 0.0)) for _key, payload in meaningful]
    decrease_values = [float(payload.get("max_decrease_percent", 0.0)) for _key, payload in meaningful]
    increase_values = [float(payload.get("max_increase_percent", 0.0)) for _key, payload in meaningful]
    rows = []
    for key, payload in meaningful:
        trough_start, trough_end = _span_start_end(payload.get("trough_spans") or payload.get("trough_times"))
        peak_start, peak_end = _span_start_end(payload.get("peak_spans") or payload.get("peak_times"))
        minimum = float(payload.get("min", 0.0))
        maximum = float(payload.get("max", 0.0))
        max_decrease = float(payload.get("max_decrease_percent", 0.0))
        max_increase = float(payload.get("max_increase_percent", 0.0))
        min_color = escape(_relative_value_color(minimum, min_values), quote=True)
        max_color = escape(_relative_value_color(maximum, max_values), quote=True)
        decrease_color = escape(_relative_value_color(max_decrease, decrease_values), quote=True)
        increase_color = escape(_relative_value_color(max_increase, increase_values), quote=True)
        rows.append(
            "<tr>"
            f"<td>{_factor_anchor(group_key, key)}</td>"
            f"<td align='right' style='color:{min_color};'>{escape(f'{minimum:.0f}')}</td>"
            f"<td align='right' style='color:{max_color};'>{escape(f'{maximum:.0f}')}</td>"
            f"<td>{escape(trough_start)}</td>"
            f"<td>{escape(trough_end)}</td>"
            f"<td>{escape(peak_start)}</td>"
            f"<td>{escape(peak_end)}</td>"
            f"<td align='right' style='color:{decrease_color};'>{escape(f'{max_decrease:.0f}')}</td>"
            f"<td align='right' style='color:{increase_color};'>{escape(f'{max_increase:.0f}')}</td>"
            f"<td>{escape(_variability_text(payload))}</td>"
            "</tr>"
        )
    return (
        "<table style='border-collapse:collapse; border:0; width:100%; font-size:11px;'>"
        "<thead><tr>"
        "<th align='left'>factor</th>" #body/sign/nak./H/el./mode
        "<th align='right'>min</th>"
        "<th align='right'>max</th>"
        "<th align='center' colspan='2'>trench</th>"
        "<th align='center' colspan='2'>peak</th>"
        "<th align='right'>-%△</th>"
        "<th align='right'>+%△</th>"
        "<th align='left'>var.</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )

def _factor_anchor(group_key: str, key: str) -> str:
    color = escape(_factor_color(group_key, key), quote=True)
    text = escape(_display_body_name(key) if group_key == "dominant_planet_weights" else str(key))
    href = _factor_link(group_key, key)
    if not href:
        return f"<span style='color:{color};'>{text}</span>"
    return (
        f"<a href='{href}' style='color:{color}; text-decoration: none;'>"
        f"{text}</a>"
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
        href = f"distinguishing-factor:gate-line:{quote(gate_number)}:{quote(line_number)}"
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
    href = f"distinguishing-factor:hd-property:{quote(property_key)}:{quote(str(value))}"
    return f"<a href='{href}' style='color:#d7b5ff; text-decoration:none;'>{safe_value}</a>"


def format_time_sensitivity_result_html(result: TimeSensitivityResult) -> str:
    """Return compact rich text for the Chart View Time Sensitivity panel."""
    return _summary_html(result) + _human_design_html(result)


def _summary_html(result: TimeSensitivityResult) -> str:
    """Return the overview/stability summary HTML."""
    overall = result.overall
    baseline_label = f"{result.baseline_time} ({overall.get('baseline_source', 'baseline')})"
    html_lines: list[str] = [
        f"<div><strong>Overall stability:</strong> {float(overall.get('stability_percent', 0)):.0f}%</div>",
        f"<div><strong>Max possible change from {escape(baseline_label)}:</strong> {float(overall.get('max_total_change_from_baseline_percent', 0)):.0f}%</div>",
        "<div><strong>Most sensitive:</strong> " + _color_code_text(", ".join(overall.get("most_sensitive", []) or ["n/a"])) + "</div>",
        "<div><strong>Least sensitive:</strong> " + _color_code_text(", ".join(overall.get("least_sensitive", []) or ["n/a"])) + "</div>",
        f"<div><strong>Samples:</strong> {result.sample_count} hypothetical standard charts + {result.sample_count} Human Design charts</div>",
        _header_html("Highly Stable:"),
    ]
    html_lines.append(_list_html([_color_code_text(item) for item in (result.stable or ["No all-day stable highlights found."])]))
    html_lines.append(_header_html("Variable:"))
    html_lines.append(_list_html([_color_code_text(item) for item in (result.variable or ["No categorical variability found."])]))

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
        always = ", ".join(_gate_anchor(item) for item in summary.get("always", [])[:20]) or "none"
        sometimes = ", ".join(_gate_anchor(item) for item in summary.get("sometimes", [])[:20]) or "none"
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
            if float(payload.get("delta", 0.0)) > 0.0 or float(payload.get("baseline", 0.0)) > 0.0
        ]
        meaningful.sort(key=lambda item: float(item[1].get("percent_delta", 0.0)), reverse=True)
        delta_values = [abs(float(payload.get("percent_delta", 0.0))) for _key, payload in meaningful]
        min_values = [float(payload.get("min", 0.0)) for _key, payload in meaningful]
        max_values = [float(payload.get("max", 0.0)) for _key, payload in meaningful]
        html_lines.append(_header_html(_group_title(group_key)))
        group_items = []
        for key, payload in meaningful[:12]:
            appears_after = payload.get("appears_after")
            suffix = f" appears after {appears_after}" if appears_after else f" {payload.get('label', '')}"
            span_bits = []
            if payload.get("present_spans"):
                span_bits.append("present " + "; ".join(payload.get("present_spans", [])[:6]))
            if payload.get("peak_spans"):
                span_bits.append("peaks " + "; ".join(payload.get("peak_spans", [])[:6]))
            if payload.get("transition_windows"):
                span_bits.append("changes " + "; ".join(payload.get("transition_windows", [])[:8]))
            tooltip = " | ".join(span_bits) or "No sampled time-span changes."
            delta_color = escape(_delta_intensity_color(abs(float(payload.get("percent_delta", 0.0))), delta_values), quote=True)
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
                + escape(f"   peak {', '.join(payload.get('peak_times', [])[:3]) or 'n/a'}   vs {result.baseline_time}: ")
                + f"<span style='color:{delta_color};'>"
                + escape(f"{float(payload.get('max_decrease_percent', 0.0)):+.0f}% to {float(payload.get('max_increase_percent', 0.0)):+.0f}%")
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
        self.boundary_refinement_checkbox.setToolTip("examines thresholds of change; takes longer but more accurate")
        refinement_info = QLabel("ⓘ")
        refinement_info.setToolTip("examines thresholds of change; takes longer but more accurate")
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
        self.output.setPlainText("Click Compute Range to scan 49 sampled times: every 30 minutes plus 23:59.")
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

    def refresh_for_current_chart(self) -> None:
        chart = self._current_chart()
        date_key = birth_date_key_for_chart(chart) if chart is not None else ""
        if date_key == self._chart_date_key:
            return
        self._chart_date_key = date_key
        self._last_result = None
        if chart is None:
            self.compute_module.setVisible(False)
            self.output.setPlainText("No active chart is loaded.")
            self._clear_weight_sections()
            return
        saved = load_time_sensitivity_result_for_chart(chart, self._current_config())
        if saved is not None:
            self._last_result = saved
            self.output.setHtml(format_time_sensitivity_result_html(saved))
            self._render_weight_sections(saved)
            self.compute_module.setVisible(False)
            return
        self.compute_module.setVisible(bool(date_key))
        if date_key:
            self.output.setPlainText(
                f"No saved Time/Rectification Sensitivity range for {date_key}. "
                "Click Compute Range to scan 49 sampled times: every 30 minutes plus 23:59."
            )
        else:
            self.output.setPlainText("No usable birth date found for Time/Rectification Sensitivity storage.")
        self._clear_weight_sections()

    def compute_range(self) -> None:
        chart = self._current_chart()
        if chart is None:
            self.compute_module.setVisible(False)
            self.output.setPlainText("No active chart is loaded.")
            return
        self.compute_button.setEnabled(False)
        self.output.setPlainText("Computing Time/Rectification Sensitivity…")
        try:
            config = self._current_config()
            self._last_result = compute_time_sensitivity(chart, config)
            self._chart_date_key = birth_date_key_for_chart(chart)
            save_time_sensitivity_result(self._last_result)
            self.output.setHtml(format_time_sensitivity_result_html(self._last_result))
            self._render_weight_sections(self._last_result)
            self.compute_module.setVisible(False)
        except Exception as exc:
            self._last_result = None
            self.output.setPlainText(f"Unable to compute Time/Rectification Sensitivity:\n{exc}")
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

    def _add_html_section(self, section_key: str, title: str, html: str, *, expanded: bool = True) -> QWidget:
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
        browser.setHtml(html)
        browser.document().adjustSize()
        height = int(browser.document().size().height()) + 12
        browser.setFixedHeight(max(48, min(700, height)))
        content_layout.addWidget(browser)
        self._charts_layout.addWidget(section)
        self._chart_sections[section_key] = section
        return section

    def _render_weight_sections(self, result: TimeSensitivityResult) -> None:
        self._clear_weight_sections()
        self.output.hide()
        self._add_html_section("summary", "Overall Time Sensitivity", _summary_html(result), expanded=True)
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
            if group_key in {"dominant_planet_weights", "dominant_sign_weights"}:
                figure = Figure(figsize=(5.5, 2.8))
                ax = figure.add_subplot(111)
                _draw_likelihood_chart(ax, result, group_key)
                canvas = FigureCanvas(figure)
                canvas.setMinimumHeight(250)
                canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                canvas.setToolTip("Click to open a larger Time Sensitivity raw-weight range popout.")
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
            table.setHtml(_header_html(_group_title(group_key)) + table_html)
            table.document().adjustSize()
            table_height = int(table.document().size().height()) + 14
            table.setFixedHeight(max(82, min(900, table_height)))
            content_layout.addWidget(table)

            self._charts_layout.addWidget(section)
            if canvas is not None:
                canvas.draw_idle()
                self._chart_canvases[group_key] = canvas
            self._chart_sections[group_key] = section
        self._add_html_section("human_design", "Human Design", _human_design_html(result), expanded=False)

    def _show_likelihood_popout(self, group_key: str) -> None:
        if self._last_result is None:
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
        _draw_likelihood_chart(ax, self._last_result, group_key)
        canvas = FigureCanvas(figure)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(canvas, 1)
        info = QTextEdit()
        info.setReadOnly(True)
        info.setHtml(
            "<b>Raw weight range:</b> each bar shows the maximum raw weight reached by that factor; "
            "the darker base marks its minimum raw weight across the sampled charts. Hover a bar "
            "to see the exact rounded min/max values."
        )
        info.setMaximumHeight(96)
        layout.addWidget(info)
        canvas.draw_idle()
        register = getattr(self._owner, "_register_popout_shortcuts", None)
        if callable(register):
            register(dialog)
        dialog.show()
