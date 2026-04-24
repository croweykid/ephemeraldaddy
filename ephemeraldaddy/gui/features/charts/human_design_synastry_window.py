from __future__ import annotations

from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSplitter,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.analysis.human_design import (
    build_awareness_stream_completion,
    build_human_design_result,
    build_human_design_synastry_data_output,
)
from ephemeraldaddy.analysis.human_design_reference import HD_CENTERS
from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.gui.features.charts.chart_data_output import (
    ChartDataTableOutput,
    apply_chart_data_highlighter,
)
from ephemeraldaddy.gui.features.charts.human_design_plot import (
    BODYGRAPH_VERTICAL_OFFSET,
    CENTER_HALF_HEIGHT,
    CENTER_HALF_WIDTH,
    CENTER_POSITIONS,
    draw_human_design_chart,
)
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
    dialog.setMinimumSize(860, 780)

    layout = QHBoxLayout(dialog)
    layout.setContentsMargins(12, 12, 12, 12)

    hd_a = build_human_design_result(chart_a)
    hd_b = build_human_design_result(chart_b)

    chart_a_gate_set = {activation.gate for activation in (*hd_a.personality_activations, *hd_a.design_activations)}
    chart_b_gate_set = {activation.gate for activation in (*hd_b.personality_activations, *hd_b.design_activations)}
    aggregate_gate_set = set(chart_a_gate_set) | set(chart_b_gate_set)
    awareness_stream_entries = build_awareness_stream_completion(aggregate_gate_set)

    chart_info_output = parent._build_popout_left_panel(
        layout,
        chart_info_placeholder="Click a gate or center on the bodygraph to see details here.",
        aspect_entries=[],
        export_file_stem="human_design_synastry",
        weighted_score_for_entry=lambda _entry: 0.0,
        show_aspect_distribution=False,
        awareness_stream_entries=awareness_stream_entries,
        circuit_entries=[],
    )

    right_layout = QVBoxLayout()
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(0)
    layout.addLayout(right_layout, 3)

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

    figure = Figure(figsize=(7.9, 10.9))
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

    center_reference_by_name = {
        str(center_data.get("center", "")).strip(): center_data
        for center_data in HD_CENTERS.values()
        if str(center_data.get("center", "")).strip()
    }

    def _show_center_info(center_name: str) -> None:
        center_meta = center_reference_by_name.get(center_name, {})
        description = str(center_meta.get("description", "No center description available.")).strip()
        is_defined = center_name in hd_a.defined_centers or center_name in hd_b.defined_centers
        state_label = "Defined in Combined Chart" if is_defined else "Undefined in Combined Chart"
        state_detail_key = "defined" if is_defined else "undefined"
        state_detail = str(center_meta.get(state_detail_key, "No details available.")).strip()
        chart_info_output.setPlainText(
            "\n".join(
                [
                    center_name,
                    description,
                    "",
                    state_label,
                    state_detail,
                ]
            )
        )

    def _show_gate_info(gate: int) -> None:
        parent._run_with_chart_info_output(
            chart_info_output,
            lambda: parent._show_human_design_gate_line_info(int(gate), None),
        )

    def _on_bodygraph_click(event: Any) -> None:
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            return
        if not figure.axes or event.inaxes is not figure.axes[0]:
            return
        for line in event.inaxes.lines:
            gate_segment_id = str(getattr(line, "get_gid", lambda: "")() or "")
            if not gate_segment_id.startswith("gate-segment:"):
                continue
            contains, _info = line.contains(event)
            if not contains:
                continue
            gate_text = gate_segment_id.split(":", 1)[1]
            if gate_text.isdigit():
                _show_gate_info(int(gate_text))
                return
        click_x = float(event.xdata)
        click_y = float(event.ydata)
        for center_name, (center_x, center_y) in CENTER_POSITIONS.items():
            center_y += BODYGRAPH_VERTICAL_OFFSET
            if (
                abs(click_x - center_x) <= CENTER_HALF_WIDTH
                and abs(click_y - center_y) <= CENTER_HALF_HEIGHT
            ):
                _show_center_info(center_name)
                return

    canvas.mpl_connect("button_press_event", _on_bodygraph_click)

    hovered_gate_text: str | None = None

    def _on_bodygraph_hover(event: Any) -> None:
        nonlocal hovered_gate_text
        if event.inaxes is None or event.x is None or event.y is None:
            if hovered_gate_text is not None:
                QToolTip.hideText()
                hovered_gate_text = None
            return
        if not figure.axes or event.inaxes is not figure.axes[0]:
            if hovered_gate_text is not None:
                QToolTip.hideText()
                hovered_gate_text = None
            return
        for line in event.inaxes.lines:
            gate_segment_id = str(getattr(line, "get_gid", lambda: "")() or "")
            if not gate_segment_id.startswith("gate-segment:"):
                continue
            contains, _info = line.contains(event)
            if not contains:
                continue
            gate_text = gate_segment_id.split(":", 1)[1]
            if not gate_text:
                continue
            if hovered_gate_text == gate_text:
                return
            tooltip_text = (
                "<div style='"
                "background-color:#000000;"
                "color:#ffffff;"
                "font-size:18px;"
                "font-weight:700;"
                "padding:6px 10px;"
                "border:1px solid #ffffff;"
                "border-radius:4px;'>"
                f"Gate {gate_text}"
                "</div>"
            )
            QToolTip.showText(canvas.mapToGlobal(QPoint(int(event.x), int(event.y))), tooltip_text, canvas)
            hovered_gate_text = gate_text
            return
        if hovered_gate_text is not None:
            QToolTip.hideText()
            hovered_gate_text = None

    canvas.mpl_connect("motion_notify_event", _on_bodygraph_hover)
    canvas.draw_idle()

    chart_container = QWidget()
    chart_container_layout = QGridLayout(chart_container)
    chart_container_layout.setContentsMargins(0, 0, 0, 0)
    chart_container_layout.setSpacing(0)
    chart_container_layout.addWidget(canvas, 0, 0)
    chart_container_layout.addWidget(header_label, 0, 0, Qt.AlignLeft | Qt.AlignTop)

    right_splitter = QSplitter(Qt.Vertical)
    right_splitter.setChildrenCollapsible(False)
    right_splitter.addWidget(chart_container)

    summary_output = ChartDataTableOutput()
    summary_output.setReadOnly(True)
    output_font = summary_output.font()
    summary_output.setFont(output_font)
    summary_output.setTabStopDistance(6)
    apply_chart_data_highlighter(summary_output)
    summary_output.setMinimumHeight(220)
    right_splitter.addWidget(summary_output)
    right_splitter.setStretchFactor(0, 7)
    right_splitter.setStretchFactor(1, 3)
    right_layout.addWidget(right_splitter, 1)

    chart_data_text, position_info_map, summary_block_offset = build_human_design_synastry_data_output(hd_a, hd_b)
    summary_output.setPlainText(chart_data_text)

    popout_context_key = summary_output.viewport()
    popout_context: dict[str, object] = {
        "output_widget": summary_output,
        "chart_info_output": chart_info_output,
        "position_info_map": position_info_map,
        "aspect_info_map": {},
        "species_info_map": {},
        "summary_block_offset": summary_block_offset,
    }
    synastry_file_stem = f"ephemeraldaddy_{parent._sanitize_export_token(chart_a.name)}_{parent._sanitize_export_token(chart_b.name)}_hd_synastry"
    summary_share_button = parent._attach_popout_share_button(summary_output, synastry_file_stem)
    popout_context["share_button"] = summary_share_button
    parent._popout_summary_contexts[popout_context_key] = popout_context
    dialog.destroyed.connect(
        lambda _=None, key=popout_context_key: parent._popout_summary_contexts.pop(key, None)
    )

    dialog.resize(1320, 1080)
    return dialog
