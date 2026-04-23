from __future__ import annotations

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ephemeraldaddy.analysis.human_design import build_human_design_result
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.gui.features.charts.human_design_plot import draw_human_design_chart
from ephemeraldaddy.gui.style import CHART_DATA_MONOSPACE_FONT_FAMILY, CHART_DATA_POPOUT_HEADER_STYLE

SYNASTRY_PRIMARY_COLOR = "#ff9f1c"
SYNASTRY_SECONDARY_COLOR = "#4ea5ff"


def create_human_design_synastry_dialog(
    parent: QWidget,
    chart_a: Chart,
    chart_b: Chart,
    *,
    chart_theme_colors: dict[str, str],
) -> QDialog:
    """Create a Human Design synastry popout dialog for two saved charts."""
    dialog = QDialog(parent)
    dialog.setAttribute(Qt.WA_DeleteOnClose)
    dialog.setWindowTitle(f"🪷 Human Design Synastry: {chart_a.name} + {chart_b.name}")
    dialog.setMinimumSize(600, 600)

    layout = QHBoxLayout(dialog)
    layout.setContentsMargins(12, 12, 12, 12)

    right_layout = QVBoxLayout()
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(0)
    layout.addLayout(right_layout, 1)

    hd_a = build_human_design_result(chart_a)
    hd_b = build_human_design_result(chart_b)

    chart_a_gate_set = {activation.gate for activation in hd_a.personality_activations}
    chart_a_gate_set.update({activation.gate for activation in hd_a.design_activations})
    chart_b_gate_set = {activation.gate for activation in hd_b.personality_activations}
    chart_b_gate_set.update({activation.gate for activation in hd_b.design_activations})

    header_label = QLabel(
        "\n".join(
            [
                "🪷 Human Design Synastry",
                f"Orange: {chart_a.name}",
                f"Blue:    {chart_b.name}",
                "Shared gates are drawn as striped segments.",
            ]
        )
    )
    header_label.setStyleSheet(f"{CHART_DATA_POPOUT_HEADER_STYLE} background: transparent;")
    header_font = header_label.font()
    header_font.setFamily(CHART_DATA_MONOSPACE_FONT_FAMILY)
    header_font.setBold(True)
    if header_font.pointSizeF() > 0:
        header_font.setPointSizeF(max(1.0, header_font.pointSizeF() * 0.65))
    header_label.setFont(header_font)

    figure = Figure(figsize=(8.2, 10.9))
    canvas = FigureCanvas(figure)
    draw_human_design_chart(
        figure,
        hd_a,
        chart_theme_colors=chart_theme_colors,
        personality_gate_set_override=chart_a_gate_set,
        design_gate_set_override=chart_b_gate_set,
        personality_active_color=SYNASTRY_PRIMARY_COLOR,
        design_active_color=SYNASTRY_SECONDARY_COLOR,
    )

    chart_container = QWidget()
    chart_container_layout = QVBoxLayout(chart_container)
    chart_container_layout.setContentsMargins(0, 0, 0, 0)
    chart_container_layout.addWidget(header_label, 0, Qt.AlignTop | Qt.AlignLeft)
    chart_container_layout.addWidget(canvas, 1)

    right_layout.addWidget(chart_container, 1)
    dialog.resize(1180, 1060)
    return dialog
