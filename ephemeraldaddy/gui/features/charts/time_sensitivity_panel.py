"""Chart View right-panel UI for Time/Rectification Sensitivity."""

from __future__ import annotations

from html import escape
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
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


def _group_title(group_key: str) -> str:
    return group_key.replace("dominant_", "Dominant ").replace("_weights", "").replace("_", " ").title()


def format_time_sensitivity_result_html(result: TimeSensitivityResult) -> str:
    """Return compact rich text for the Chart View Time Sensitivity panel."""
    overall = result.overall
    baseline_label = f"{result.baseline_time} ({overall.get('baseline_source', 'baseline')})"
    lines: list[str] = [
        f"Overall stability: {overall.get('stability_percent', 0):.2f}%",
        f"Max possible change from {baseline_label}: {overall.get('max_total_change_from_baseline_percent', 0):.2f}%",
        "Most sensitive: " + ", ".join(overall.get("most_sensitive", []) or ["n/a"]),
        "Least sensitive: " + ", ".join(overall.get("least_sensitive", []) or ["n/a"]),
        f"Samples: {result.sample_count} hypothetical standard charts + {result.sample_count} Human Design charts",
        "",
        "Highly stable:",
    ]
    lines.extend(f"  {item}" for item in (result.stable or ["No all-day stable highlights found."]))
    lines.extend(["", "Variable:"])
    lines.extend(f"  {item}" for item in (result.variable or ["No categorical variability found."]))

    for group_key, ranges in result.numeric_ranges.items():
        meaningful = [
            (key, payload)
            for key, payload in ranges.items()
            if float(payload.get("delta", 0.0)) > 0.0 or float(payload.get("baseline", 0.0)) > 0.0
        ]
        meaningful.sort(key=lambda item: float(item[1].get("percent_delta", 0.0)), reverse=True)
        lines.extend(["", _group_title(group_key)])
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
            lines.append(
                f"{key:<22} {float(payload.get('min', 0.0)):.2f}–{float(payload.get('max', 0.0)):.2f}   "
                f"peak {', '.join(payload.get('peak_times', [])[:3]) or 'n/a'}   "
                f"vs {result.baseline_time}: {float(payload.get('max_decrease_percent', 0.0)):+.2f}% to "
                f"{float(payload.get('max_increase_percent', 0.0)):+.2f}%{suffix}  [hover: {tooltip}]"
            )

    hd = result.human_design
    lines.extend(["", "Human Design"])
    for key in ("gates", "lines", "channels"):
        summary = hd.get(key, {})
        always = ", ".join(summary.get("always", [])[:20]) or "none"
        sometimes = ", ".join(summary.get("sometimes", [])[:20]) or "none"
        lines.append(f"{key.title()} always present: {always}")
        lines.append(f"{key.title()} sometimes present: {sometimes}")
    lines.append("Type distribution: " + ", ".join(f"{k} ({v})" for k, v in hd.get("type_distribution", {}).items()))
    lines.append("Profile distribution: " + ", ".join(f"{k} ({v})" for k, v in hd.get("profile_distribution", {}).items()))

    if result.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"  {warning}" for warning in result.warnings)
    html_lines: list[str] = []
    for line in lines:
        marker = "  [hover: "
        if marker in line and line.endswith("]"):
            visible, tooltip = line.split(marker, 1)
            tooltip = tooltip[:-1]
            html_lines.append(
                "<span style='text-decoration: underline dotted;' title='"
                + escape(tooltip, quote=True)
                + "'>"
                + escape(visible)
                + "</span>"
            )
        else:
            html_lines.append(escape(line))
    return "<pre style='white-space: pre-wrap; font-family: monospace;'>" + "\n".join(html_lines) + "</pre>"


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

        refinement_row = QHBoxLayout()
        self.boundary_refinement_checkbox = QCheckBox("boundary refinement")
        self.boundary_refinement_checkbox.setEnabled(False)
        self.boundary_refinement_checkbox.setToolTip("examines thresholds of change; takes longer but more accurate")
        refinement_info = QLabel("ⓘ")
        refinement_info.setToolTip("examines thresholds of change; takes longer but more accurate")
        refinement_row.addWidget(self.boundary_refinement_checkbox)
        refinement_row.addWidget(refinement_info)
        refinement_row.addStretch(1)
        layout.addLayout(refinement_row)

        controls = QHBoxLayout()
        self.interval_combo = QComboBox()
        self.interval_combo.addItem("30 min intervals", 30)
        self.compute_button = QPushButton("Compute Range")
        self.compute_button.clicked.connect(self.compute_range)
        controls.addWidget(self.interval_combo)
        controls.addWidget(self.compute_button)
        layout.addLayout(controls)

        self.save_button = QPushButton("Save range")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_range)
        layout.addWidget(self.save_button)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(360)
        self.output.setPlainText("Click Compute Range to scan 49 sampled times: every 30 minutes plus 23:59.")
        layout.addWidget(self.output, 1)

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
        self.save_button.setEnabled(False)
        if chart is None:
            self.output.setPlainText("No active chart is loaded.")
            return
        saved = load_time_sensitivity_result_for_chart(chart, self._current_config())
        if saved is not None:
            self._last_result = saved
            self.output.setHtml(format_time_sensitivity_result_html(saved))
            self.save_button.setEnabled(True)
            return
        if date_key:
            self.output.setPlainText(
                f"No saved Time/Rectification Sensitivity range for {date_key}. "
                "Click Compute Range to scan 49 sampled times: every 30 minutes plus 23:59."
            )
        else:
            self.output.setPlainText("No usable birth date found for Time/Rectification Sensitivity storage.")

    def compute_range(self) -> None:
        chart = self._current_chart()
        if chart is None:
            self.output.setPlainText("No active chart is loaded.")
            return
        self.compute_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.output.setPlainText("Computing Time/Rectification Sensitivity…")
        try:
            config = self._current_config()
            self._last_result = compute_time_sensitivity(chart, config)
            self._chart_date_key = birth_date_key_for_chart(chart)
            self.output.setHtml(format_time_sensitivity_result_html(self._last_result))
            self.save_button.setEnabled(True)
        except Exception as exc:
            self._last_result = None
            self.output.setPlainText(f"Unable to compute Time/Rectification Sensitivity:\n{exc}")
        finally:
            self.compute_button.setEnabled(True)

    def save_range(self) -> None:
        if self._last_result is None:
            return
        try:
            save_time_sensitivity_result(self._last_result)
        except Exception as exc:
            QMessageBox.warning(self, "Time Sensitivity", f"Unable to save range:\n{exc}")
            return
        QMessageBox.information(self, "Time Sensitivity", "Time/Rectification Sensitivity range saved.")
