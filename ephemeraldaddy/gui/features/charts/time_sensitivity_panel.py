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
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
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
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR


_TIME_SENSITIVITY_CHART_TITLES = {
    "dominant_planet_weights": "Dominant Body Likelihood",
    "dominant_sign_weights": "Dominant Sign Likelihood",
}


def _likelihood_rows(result: TimeSensitivityResult, group_key: str) -> list[tuple[str, float]]:
    """Return dominance-likelihood rows, falling back to max-weight range data for old saves."""
    likelihoods = (result.overall.get("dominance_likelihoods") or {}).get(group_key, {})
    if isinstance(likelihoods, dict) and likelihoods:
        rows = [
            (str(key), float(payload.get("percent", 0.0)))
            for key, payload in likelihoods.items()
            if isinstance(payload, dict)
        ]
        return sorted(rows, key=lambda item: (-item[1], item[0]))

    ranges = result.numeric_ranges.get(group_key, {})
    rows = [
        (str(key), float(payload.get("max", 0.0)))
        for key, payload in ranges.items()
        if isinstance(payload, dict) and float(payload.get("max", 0.0)) > 0.0
    ]
    total = sum(value for _key, value in rows)
    if total <= 0.0:
        return []
    return sorted(
        [(key, (value / total) * 100.0) for key, value in rows],
        key=lambda item: (-item[1], item[0]),
    )


def _color_for_likelihood(group_key: str, label: str) -> str:
    if group_key == "dominant_sign_weights":
        return str(SIGN_COLORS.get(label, "#6fa8dc"))
    return str(PLANET_COLORS.get(label, "#6fa8dc"))


def _display_label_for_likelihood(group_key: str, label: str) -> str:
    if group_key == "dominant_planet_weights":
        return _display_body_name(label)
    return label


def _draw_likelihood_chart(ax: Any, result: TimeSensitivityResult, group_key: str) -> None:
    rows = _likelihood_rows(result, group_key)
    labels = [label for label, _percent in rows]
    display_labels = [_display_label_for_likelihood(group_key, label) for label in labels]
    values = [percent for _label, percent in rows]
    colors = [_color_for_likelihood(group_key, label) for label in labels]
    ax.set_facecolor("#111111")
    ax.figure.patch.set_facecolor("#111111")
    if not rows:
        ax.text(0.5, 0.5, "No dominance likelihood data available.", ha="center", va="center", color="#f5f5f5")
        ax.set_axis_off()
        return

    bars = ax.bar(display_labels, values, color=colors, alpha=0.72, edgecolor="#f5f5f5", linewidth=0.25)
    for bar, label, percent in zip(bars, labels, values, strict=True):
        bar.set_gid(f"time_sensitivity:{group_key}:{label}")
        bar.set_picker(True)
        # Opacity+ stacking: a translucent full-height cap shows the remaining uncertainty
        # across the 49 Time Sensitivity sampled charts.
        ax.bar(
            bar.get_x() + (bar.get_width() / 2),
            max(0.0, 100.0 - percent),
            width=bar.get_width(),
            bottom=percent,
            color=_color_for_likelihood(group_key, label),
            alpha=0.18,
            edgecolor="none",
            align="center",
        )
        ax.text(
            bar.get_x() + (bar.get_width() / 2),
            min(100.0, percent + 2.0),
            f"{percent:.0f}%",
            ha="center",
            va="bottom",
            color="#f5f5f5",
            fontsize=8,
            fontweight="bold",
        )
    ax.set_ylim(0, 105)
    ax.set_ylabel("% of sampled charts", color="#f5f5f5", fontsize=8)
    ax.set_title(_TIME_SENSITIVITY_CHART_TITLES.get(group_key, group_key), color="#f5f5f5", fontsize=10, fontweight="bold")
    ax.tick_params(axis="x", colors="#f5f5f5", labelrotation=45, labelsize=8)
    ax.tick_params(axis="y", colors="#f5f5f5", labelsize=8)
    ax.grid(axis="y", color="#333333", linewidth=0.5, alpha=0.8)
    for spine in ax.spines.values():
        spine.set_color("#555555")
    ax.figure.tight_layout()


def _group_title(group_key: str) -> str:
    titles = {
        "dominant_planet_weights": "Dominant Bodies",
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
    return _delta_intensity_color(float(value), peer_values)


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
        return "#d7b5ff"
    return "#6fa8dc"


_COLOR_CODE_TERMS: dict[str, str] = {
    **{str(name): str(color) for name, color in SIGN_COLORS.items()},
    **{str(name): str(color) for name, color in PLANET_COLORS.items()},
    **{str(name): str(color) for name, color in ELEMENT_COLORS.items()},
    **{str(name).title(): str(color) for name, color in MODE_COLORS.items()},
    **{str(name): str(color) for name, (_planet, color) in NAKSHATRA_PLANET_COLOR.items()},
    **{f"House {house}": str(color) for house, color in HOUSE_COLORS.items()},
}

_COLOR_CODE_PATTERN = re.compile(
    r"(?<![\w-])("
    + "|".join(re.escape(term) for term in sorted(_COLOR_CODE_TERMS, key=len, reverse=True))
    + r")(?![\w-])",
    re.IGNORECASE,
)


def _color_code_text(text: str) -> str:
    """Escape text and color known astrological body/category names within it."""
    escaped_text = escape(str(text))

    def replace(match: re.Match[str]) -> str:
        matched = match.group(0)
        color = _COLOR_CODE_TERMS.get(matched)
        if color is None:
            color = next(
                (
                    candidate_color
                    for candidate_name, candidate_color in _COLOR_CODE_TERMS.items()
                    if candidate_name.lower() == matched.lower()
                ),
                "#6fa8dc",
            )
        return f"<span style='color:{escape(color, quote=True)};'>{matched}</span>"

    return _COLOR_CODE_PATTERN.sub(replace, escaped_text)


def _header_html(label: str) -> str:
    return f"<div style='color:{CHART_DATA_HIGHLIGHT_COLOR}; font-weight:700; margin-top:8px;'>{escape(label)}</div>"


def _list_html(items: list[str]) -> str:
    return "<ul style='margin-top:2px; margin-bottom:6px;'>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def _factor_link(group_key: str, key: str) -> str:
    kind = _NUMERIC_GROUP_LINK_KINDS.get(group_key, "")
    value = str(key).removeprefix("House ").strip() if kind == "house" else str(key)
    return f"distinguishing-factor:{kind}:{quote(value)}" if kind else ""


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
        return f"<span style='color:{escape(color, quote=True)};'>{safe_gate}</span>"
    return (
        f"<a href='{href}' style='color:{escape(color, quote=True)}; text-decoration: none;'>"
        f"{safe_gate}</a>"
    )


def format_time_sensitivity_result_html(result: TimeSensitivityResult) -> str:
    """Return compact rich text for the Chart View Time Sensitivity panel."""
    overall = result.overall
    baseline_label = f"{result.baseline_time} ({overall.get('baseline_source', 'baseline')})"
    html_lines: list[str] = [
        f"<div>Overall stability: {overall.get('stability_percent', 0):.2f}%</div>",
        f"<div>Max possible change from {escape(baseline_label)}: {overall.get('max_total_change_from_baseline_percent', 0):.2f}%</div>",
        "<div>Most sensitive: " + _color_code_text(", ".join(overall.get("most_sensitive", []) or ["n/a"])) + "</div>",
        "<div>Least sensitive: " + _color_code_text(", ".join(overall.get("least_sensitive", []) or ["n/a"])) + "</div>",
        f"<div>Samples: {result.sample_count} hypothetical standard charts + {result.sample_count} Human Design charts</div>",
        _header_html("Highly Stable:"),
    ]
    html_lines.append(_list_html([_color_code_text(item) for item in (result.stable or ["No all-day stable highlights found."])]))
    html_lines.append(_header_html("Variable:"))
    html_lines.append(_list_html([_color_code_text(item) for item in (result.variable or ["No categorical variability found."])]))

    for group_key, ranges in result.numeric_ranges.items():
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
                + f"<span style='color:{min_color};'>{escape(f'{minimum:.2f}')}</span>"
                + escape("–")
                + f"<span style='color:{max_color};'>{escape(f'{maximum:.2f}')}</span>"
                + escape(f"   peak {', '.join(payload.get('peak_times', [])[:3]) or 'n/a'}   vs {result.baseline_time}: ")
                + f"<span style='color:{delta_color};'>"
                + escape(f"{float(payload.get('max_decrease_percent', 0.0)):+.2f}% to {float(payload.get('max_increase_percent', 0.0)):+.2f}%")
                + "</span>"
                + escape(f"{suffix}")
                + "</span>"
            )
        html_lines.append(_list_html(group_items))

    hd = result.human_design
    html_lines.append(_header_html("Human Design"))
    hd_items = []
    for key in ("gates", "lines", "channels"):
        summary = hd.get(key, {})
        always = ", ".join(_gate_anchor(item) for item in summary.get("always", [])[:20]) or "none"
        sometimes = ", ".join(_gate_anchor(item) for item in summary.get("sometimes", [])[:20]) or "none"
        hd_items.append(f"{escape(key.title())} always present: {always}")
        hd_items.append(f"{escape(key.title())} sometimes present: {sometimes}")
    hd_items.append(escape("Type distribution: " + ", ".join(f"{k} ({v})" for k, v in hd.get("type_distribution", {}).items())))
    hd_items.append(escape("Profile distribution: " + ", ".join(f"{k} ({v})" for k, v in hd.get("profile_distribution", {}).items())))
    html_lines.append(_list_html(hd_items))

    if result.warnings:
        html_lines.append(_header_html("Warnings:"))
        html_lines.append(_list_html([escape(warning) for warning in result.warnings]))
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

        self.output = QTextBrowser()
        self.output.setReadOnly(True)
        self.output.setOpenExternalLinks(False)
        self.output.setOpenLinks(False)
        self.output.anchorClicked.connect(self._open_chart_info_link)
        self.output.setMinimumHeight(360)
        self.output.setPlainText("Click Compute Range to scan 49 sampled times: every 30 minutes plus 23:59.")
        layout.addWidget(self.output, 1)

        self._chart_canvases: dict[str, FigureCanvas] = {}
        self._charts_layout = QVBoxLayout()
        self._charts_layout.setContentsMargins(0, 0, 0, 0)
        self._charts_layout.setSpacing(8)
        layout.addLayout(self._charts_layout)

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
            self._clear_likelihood_charts()
            return
        saved = load_time_sensitivity_result_for_chart(chart, self._current_config())
        if saved is not None:
            self._last_result = saved
            self.output.setHtml(format_time_sensitivity_result_html(saved))
            self._render_likelihood_charts(saved)
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
        self._clear_likelihood_charts()

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
            self._render_likelihood_charts(self._last_result)
            self.compute_module.setVisible(False)
        except Exception as exc:
            self._last_result = None
            self.output.setPlainText(f"Unable to compute Time/Rectification Sensitivity:\n{exc}")
            self._clear_likelihood_charts()
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

    def _clear_likelihood_charts(self) -> None:
        for canvas in self._chart_canvases.values():
            canvas.setParent(None)
            canvas.deleteLater()
        self._chart_canvases = {}

    def _render_likelihood_charts(self, result: TimeSensitivityResult) -> None:
        self._clear_likelihood_charts()
        for group_key in ("dominant_planet_weights", "dominant_sign_weights"):
            if not _likelihood_rows(result, group_key):
                continue
            figure = Figure(figsize=(5.5, 2.8))
            ax = figure.add_subplot(111)
            _draw_likelihood_chart(ax, result, group_key)
            canvas = FigureCanvas(figure)
            canvas.setMinimumHeight(250)
            canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            canvas.setToolTip("Click to open a larger Time Sensitivity likelihood popout.")
            canvas.mpl_connect(
                "button_press_event",
                lambda _event, key=group_key: self._show_likelihood_popout(key),
            )
            self._charts_layout.addWidget(canvas)
            canvas.draw_idle()
            self._chart_canvases[group_key] = canvas

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
            "<b>Opacity+ stack meaning:</b> the solid portion is the percentage of sampled charts "
            "where that factor is dominant; the translucent cap is the remaining uncertainty across "
            f"{int(self._last_result.sample_count)} sampled charts."
        )
        info.setMaximumHeight(96)
        layout.addWidget(info)
        canvas.draw_idle()
        register = getattr(self._owner, "_register_popout_shortcuts", None)
        if callable(register):
            register(dialog)
        dialog.show()
