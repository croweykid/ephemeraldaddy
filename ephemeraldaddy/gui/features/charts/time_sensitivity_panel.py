"""Chart View right-panel UI for Time/Rectification Sensitivity."""

from __future__ import annotations

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
    compute_time_sensitivity,
    save_time_sensitivity_result,
)


def _group_title(group_key: str) -> str:
    return group_key.replace("dominant_", "Dominant ").replace("_weights", "").replace("_", " ").title()


def format_time_sensitivity_result_text(result: TimeSensitivityResult) -> str:
    """Return compact text for the Chart View Time Sensitivity panel."""
    overall = result.overall
    lines: list[str] = [
        f"Overall stability: {overall.get('stability_percent', 0):.2f}%",
        f"Max total change from noon: {overall.get('max_total_change_from_baseline_percent', 0):.2f}%",
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
            lines.append(
                f"{key:<22} {float(payload.get('min', 0.0)):.2f}–{float(payload.get('max', 0.0)):.2f}   "
                f"Δ {float(payload.get('delta', 0.0)):.2f}   {float(payload.get('percent_delta', 0.0)):+.2f}% from noon{suffix}"
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
    return "\n".join(lines)


class TimeSensitivityPanel(QWidget):
    """Right-panel widget that computes sampled Time/Rectification Sensitivity."""

    def __init__(self, owner: object) -> None:
        super().__init__()
        self._owner = owner
        self._last_result: TimeSensitivityResult | None = None
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

    def compute_range(self) -> None:
        chart = self._current_chart()
        if chart is None:
            self.output.setPlainText("No active chart is loaded.")
            return
        self.compute_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.output.setPlainText("Computing Time/Rectification Sensitivity…")
        try:
            config = TimeSensitivityConfig(
                interval_minutes=int(self.interval_combo.currentData() or 30),
                include_day_end=True,
                baseline_time="12:00",
                boundary_refinement=False,
            )
            self._last_result = compute_time_sensitivity(chart, config)
            self.output.setPlainText(format_time_sensitivity_result_text(self._last_result))
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
