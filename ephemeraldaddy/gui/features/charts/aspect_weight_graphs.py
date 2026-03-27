from __future__ import annotations

from collections import Counter, OrderedDict
from typing import Any, Callable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
)

from ephemeraldaddy.core.interpretations import ASPECT_COLORS, ASPECT_FRICTION, ASPECT_TYPES


def normalize_aspect_type(raw_aspect: Any) -> str:
    return str(raw_aspect or "").strip().lower().replace("-", "_").replace(" ", "_")


def extract_aspect_weight(aspect_entry: Any) -> float:
    raw_weight = getattr(aspect_entry, "weight", None)
    if raw_weight is None and isinstance(aspect_entry, dict):
        raw_weight = aspect_entry.get("weight")
    try:
        weight = float(raw_weight)
    except (TypeError, ValueError):
        weight = 0.0
    return max(0.0, weight)


def collect_aspect_type_counts(
    aspect_entries: list[Any],
    *,
    weighted: bool = False,
    weighted_score_for_entry: Callable[[Any], float] | None = None,
) -> OrderedDict[str, float]:
    counts: Counter[str] = Counter()

    for entry in aspect_entries:
        aspect_value = getattr(entry, "aspect", None)
        if aspect_value is None:
            aspect_value = getattr(entry, "type", None)
        if aspect_value is None and isinstance(entry, dict):
            aspect_value = entry.get("aspect") or entry.get("type")
        aspect_key = normalize_aspect_type(aspect_value)
        if not aspect_key:
            continue
        if weighted:
            if weighted_score_for_entry is not None:
                weight = max(0.0, float(weighted_score_for_entry(entry) or 0.0))
            else:
                weight = extract_aspect_weight(entry)
            if weight <= 0:
                continue
            counts[aspect_key] += weight
        else:
            counts[aspect_key] += 1.0

    ordered_keys = [key for key in ASPECT_COLORS.keys() if counts.get(key, 0) > 0]
    for key in sorted(counts.keys()):
        if key not in ordered_keys and counts[key] > 0:
            ordered_keys.append(key)
    return OrderedDict((key, counts[key]) for key in ordered_keys)


def collect_aspect_category_totals(
    aspect_counts: OrderedDict[str, float],
    *,
    categories: dict[str, dict[str, Any]],
) -> OrderedDict[str, float]:
    category_totals: OrderedDict[str, float] = OrderedDict()
    for category_name, category_meta in categories.items():
        category_aspects = {normalize_aspect_type(name) for name in category_meta.get("aspects", set())}
        total = sum(aspect_counts.get(aspect_name, 0) for aspect_name in category_aspects)
        if total > 0:
            category_totals[category_name] = total
    return category_totals


def draw_popout_aspect_distribution_chart(
    analytics_ax: Any,
    *,
    mode: str,
    aspect_counts: OrderedDict[str, float],
    weighted_aspect_counts: OrderedDict[str, float],
    type_totals: OrderedDict[str, float],
    weighted_type_totals: OrderedDict[str, float],
    friction_totals: OrderedDict[str, float],
    weighted_friction_totals: OrderedDict[str, float],
    chart_theme_colors: dict[str, str],
) -> None:
    analytics_ax.clear()
    analytics_ax.set_facecolor(chart_theme_colors["background"])

    if mode == "aspect_types_weighted":
        active_counts = weighted_type_totals
        labels = [label.title() for label in active_counts.keys()]
        colors = [ASPECT_TYPES.get(key, {}).get("color", chart_theme_colors["accent"]) for key in active_counts.keys()]
    elif mode == "aspect_types":
        active_counts = type_totals
        labels = [label.title() for label in active_counts.keys()]
        colors = [ASPECT_TYPES.get(key, {}).get("color", chart_theme_colors["accent"]) for key in active_counts.keys()]
    elif mode == "aspect_friction_weighted":
        active_counts = weighted_friction_totals
        labels = [label.title() for label in active_counts.keys()]
        colors = [ASPECT_FRICTION.get(key, {}).get("color", chart_theme_colors["accent"]) for key in active_counts.keys()]
    elif mode == "aspect_friction":
        active_counts = friction_totals
        labels = [label.title() for label in active_counts.keys()]
        colors = [ASPECT_FRICTION.get(key, {}).get("color", chart_theme_colors["accent"]) for key in active_counts.keys()]
    elif mode == "aspects":
        active_counts = aspect_counts
        labels = [key.replace("_", " ").title() for key in active_counts.keys()]
        colors = [ASPECT_COLORS.get(key, chart_theme_colors["accent"]) for key in active_counts.keys()]
    else:
        active_counts = weighted_aspect_counts
        labels = [key.replace("_", " ").title() for key in active_counts.keys()]
        colors = [ASPECT_COLORS.get(key, chart_theme_colors["accent"]) for key in active_counts.keys()]

    values = list(active_counts.values())
    if values:
        total = sum(values)
        min_labeled_pct = 6
        formatted_labels = [
            label if total > 0 and ((value / total) * 100.0) >= min_labeled_pct else ""
            for label, value in zip(labels, values)
        ]
        analytics_ax.pie(
            values,
            labels=formatted_labels,
            colors=colors,
            startangle=90,
            counterclock=False,
            wedgeprops={"linewidth": 0.8, "edgecolor": chart_theme_colors["background"]},
            textprops={"color": chart_theme_colors["text"], "fontsize": 7},
            autopct=lambda pct: f"{pct:.0f}%" if pct >= min_labeled_pct else "",
            pctdistance=0.7,
            labeldistance=1.08,
            radius=0.5,
        )
        analytics_ax.axis("equal")
        analytics_ax.set_xlim(-1.0, 1.0)
        analytics_ax.set_ylim(-1.0, 1.0)
    else:
        analytics_ax.text(
            0.5,
            0.5,
            "No relevant aspects",
            color=chart_theme_colors["muted_text"],
            ha="center",
            va="center",
            transform=analytics_ax.transAxes,
            fontsize=8,
        )
        analytics_ax.set_xticks([])
        analytics_ax.set_yticks([])

    for spine in analytics_ax.spines.values():
        spine.set_color(chart_theme_colors["spine"])
    analytics_ax.set_xticks([])
    analytics_ax.set_yticks([])


def build_popout_left_panel(
    layout: QHBoxLayout,
    *,
    chart_info_placeholder: str,
    aspect_entries: list[Any],
    export_file_stem: str,
    weighted_score_for_entry: Callable[[Any], float] | None,
    aspect_subheader: str | None,
    parent: Any,
    chart_summary_highlighter_cls: type,
    export_aspect_distribution_csv_dialog: Callable[..., None],
    get_share_icon_path: Callable[[], str | None],
    chart_data_info_label_style: str,
    database_analytics_dropdown_style: str,
    chart_theme_colors: dict[str, str],
    show_aspect_distribution: bool = True,
    awareness_stream_entries: list[dict[str, Any]] | None = None,
) -> QPlainTextEdit:
    left_panel_layout = QVBoxLayout()

    analytics_header_layout = QHBoxLayout()
    analytics_header_layout.setContentsMargins(0, 0, 0, 0)
    analytics_header_layout.setSpacing(6)
    showing_awareness_streams = bool(awareness_stream_entries)
    analytics_label = QLabel("Awareness Streams" if showing_awareness_streams else "Aspect Distribution")
    analytics_label.setStyleSheet(chart_data_info_label_style)
    analytics_header_layout.addWidget(analytics_label)

    analytics_view_dropdown = QComboBox()
    analytics_view_dropdown.setStyleSheet(database_analytics_dropdown_style)
    analytics_view_dropdown.addItem("ASPECTS (WEIGHTED)", "aspects_weighted")
    analytics_view_dropdown.addItem("ASPECT TYPES (WEIGHTED)", "aspect_types_weighted")
    analytics_view_dropdown.addItem("ASPECT FRICTION (WEIGHTED)", "aspect_friction_weighted")
    analytics_view_dropdown.addItem("ASPECTS (PREVALENCE)", "aspects")
    analytics_view_dropdown.addItem("ASPECT TYPES (PREVALENCE)", "aspect_types")
    analytics_view_dropdown.addItem("ASPECT FRICTION (PREVALENCE)", "aspect_friction")
    analytics_header_layout.addWidget(analytics_view_dropdown, 0, Qt.AlignLeft)

    analytics_header_layout.addStretch(1)

    analytics_export_button = QToolButton()
    share_icon_path = get_share_icon_path()
    if share_icon_path:
        analytics_export_button.setIcon(QIcon(share_icon_path))
        analytics_export_button.setIconSize(QSize(14, 14))
    else:
        analytics_export_button.setText("↗")
    analytics_export_button.setAutoRaise(True)
    analytics_export_button.setCursor(Qt.PointingHandCursor)
    analytics_export_button.setToolTip("Export aspect distribution as CSV")
    analytics_header_layout.addWidget(analytics_export_button, 0, Qt.AlignRight)
    left_panel_layout.addLayout(analytics_header_layout)

    show_legacy_aspect_controls = show_aspect_distribution and not showing_awareness_streams
    analytics_label.setVisible(show_aspect_distribution or showing_awareness_streams)
    analytics_view_dropdown.setVisible(show_legacy_aspect_controls)
    analytics_export_button.setVisible(show_legacy_aspect_controls)

    if aspect_subheader:
        aspect_subheader_label = QLabel(aspect_subheader)
        aspect_subheader_label.setWordWrap(True)
        aspect_subheader_label.setStyleSheet(f"color: {chart_theme_colors['text']};")
        aspect_subheader_label.setVisible(show_aspect_distribution or showing_awareness_streams)
        left_panel_layout.addWidget(aspect_subheader_label)

    analytics_figure = Figure(figsize=(4.2, 3.4))
    analytics_canvas = FigureCanvas(analytics_figure)
    analytics_ax = analytics_figure.add_subplot(111)
    analytics_figure.patch.set_facecolor(chart_theme_colors["background"])
    analytics_ax.set_facecolor(chart_theme_colors["background"])

    aspect_counts = collect_aspect_type_counts(aspect_entries)
    weighted_aspect_counts = collect_aspect_type_counts(
        aspect_entries,
        weighted=True,
        weighted_score_for_entry=weighted_score_for_entry,
    )
    type_totals = collect_aspect_category_totals(aspect_counts, categories=ASPECT_TYPES)
    weighted_type_totals = collect_aspect_category_totals(weighted_aspect_counts, categories=ASPECT_TYPES)
    friction_totals = collect_aspect_category_totals(aspect_counts, categories=ASPECT_FRICTION)
    weighted_friction_totals = collect_aspect_category_totals(weighted_aspect_counts, categories=ASPECT_FRICTION)

    def _export_selected_aspect_distribution(_checked: bool = False) -> None:
        selected_mode = analytics_view_dropdown.currentData()
        if selected_mode == "aspect_types_weighted":
            selected_counts = weighted_type_totals
            export_stem = f"{export_file_stem}_aspect_types_weighted"
        elif selected_mode == "aspect_types":
            selected_counts = type_totals
            export_stem = f"{export_file_stem}_aspect_types_prevalence"
        elif selected_mode == "aspect_friction_weighted":
            selected_counts = weighted_friction_totals
            export_stem = f"{export_file_stem}_aspect_friction_weighted"
        elif selected_mode == "aspect_friction":
            selected_counts = friction_totals
            export_stem = f"{export_file_stem}_aspect_friction_prevalence"
        elif selected_mode == "aspects":
            selected_counts = aspect_counts
            export_stem = f"{export_file_stem}_aspects_prevalence"
        else:
            selected_counts = weighted_aspect_counts
            export_stem = f"{export_file_stem}_aspects_weighted"

        export_aspect_distribution_csv_dialog(
            parent,
            selected_counts,
            default_file_stem=export_stem,
        )

    analytics_export_button.clicked.connect(_export_selected_aspect_distribution)

    def _render_analytics_chart() -> None:
        if showing_awareness_streams:
            analytics_ax.clear()
            analytics_ax.set_facecolor(chart_theme_colors["background"])
            color_by_completion = {
                0: "#777777",
                1: "#a94343",
                2: "#b4942d",
                3: "#7e9f3a",
                4: "#2f8f86",
            }
            entries = awareness_stream_entries or []
            if entries:
                y_positions = list(range(len(entries)))
                analytics_ax.set_xlim(0, 4)
                analytics_ax.set_ylim(-0.5, len(entries) - 0.5)
                analytics_ax.invert_yaxis()
                for row_index, entry in enumerate(entries):
                    gates = [int(gate) for gate in entry.get("gates", []) if isinstance(gate, int)]
                    present_gates = set(int(gate) for gate in entry.get("present_gates", []))
                    completion_count = len([gate for gate in gates if gate in present_gates])
                    segment_color = color_by_completion.get(completion_count, color_by_completion[0])
                    for segment_index, gate in enumerate(gates[:4]):
                        gate_present = gate in present_gates
                        face_color = segment_color if gate_present else "#4f4f4f"
                        label_color = "#ffffff" if gate_present else "#b8b8b8"
                        bar_container = analytics_ax.barh(
                            row_index,
                            1.0,
                            left=segment_index,
                            color=face_color,
                            edgecolor=chart_theme_colors["spine"],
                            height=0.62,
                            linewidth=0.8,
                        )
                        gate_gid = f"awareness_gate:{gate}"
                        for patch in getattr(bar_container, "patches", []):
                            patch.set_gid(gate_gid)
                            patch.set_picker(True)
                        gate_text_artist = analytics_ax.text(
                            segment_index + 0.5,
                            row_index,
                            str(gate),
                            ha="center",
                            va="center",
                            color=label_color,
                            fontsize=7,
                            fontweight="bold",
                        )
                        gate_text_artist.set_gid(gate_gid)
                        gate_text_artist.set_picker(True)
                y_tick_labels = [str(entry.get("name", "Unknown")) for entry in entries]
                analytics_ax.set_yticks(y_positions)
                analytics_ax.set_yticklabels(y_tick_labels, color=chart_theme_colors["text"], fontsize=7)
            else:
                analytics_ax.text(
                    0.5,
                    0.5,
                    "No awareness stream data",
                    color=chart_theme_colors["muted_text"],
                    ha="center",
                    va="center",
                    transform=analytics_ax.transAxes,
                    fontsize=8,
                )
                analytics_ax.set_yticks([])
            analytics_ax.set_xticks([])
            for spine in analytics_ax.spines.values():
                spine.set_color(chart_theme_colors["spine"])
            analytics_figure.subplots_adjust(left=0.30, bottom=0.03, right=0.98, top=0.98)
            analytics_canvas.draw_idle()
            return

        selected_mode = str(analytics_view_dropdown.currentData() or "aspects_weighted")
        draw_popout_aspect_distribution_chart(
            analytics_ax,
            mode=selected_mode,
            aspect_counts=aspect_counts,
            weighted_aspect_counts=weighted_aspect_counts,
            type_totals=type_totals,
            weighted_type_totals=weighted_type_totals,
            friction_totals=friction_totals,
            weighted_friction_totals=weighted_friction_totals,
            chart_theme_colors=chart_theme_colors,
        )
        analytics_figure.subplots_adjust(left=0.08, bottom=0.08, right=0.95, top=0.95)
        analytics_canvas.draw_idle()

    analytics_view_dropdown.currentIndexChanged.connect(lambda _index: _render_analytics_chart())
    _render_analytics_chart()
    analytics_canvas.setMinimumHeight(220)
    analytics_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    analytics_canvas.setVisible(show_aspect_distribution or showing_awareness_streams)
    left_panel_layout.addWidget(analytics_canvas, 2)

    chart_info_label = QLabel("Chart Info!")
    chart_info_label.setStyleSheet(chart_data_info_label_style)
    chart_info_output = QPlainTextEdit()
    chart_info_output.setReadOnly(True)
    chart_info_output.setPlaceholderText(chart_info_placeholder)
    chart_info_output.setMinimumWidth(250)
    chart_info_output._summary_highlighter = chart_summary_highlighter_cls(chart_info_output.document())
    left_panel_layout.addWidget(chart_info_label)
    left_panel_layout.addWidget(chart_info_output, 1)

    def _show_awareness_gate_info(gate: int) -> None:
        show_gate_info = getattr(parent, "_show_human_design_gate_line_info", None)
        if not callable(show_gate_info):
            chart_info_output.setPlainText(f"Gate {gate}")
            return
        original_chart_info_output = getattr(parent, "chart_info_output", None)
        try:
            parent.chart_info_output = chart_info_output
            show_gate_info(int(gate), None)
        finally:
            parent.chart_info_output = original_chart_info_output

    def _on_awareness_pick(event: Any) -> None:
        if not showing_awareness_streams:
            return
        artist = getattr(event, "artist", None)
        artist_gid = artist.get_gid() if artist is not None else None
        if not isinstance(artist_gid, str) or not artist_gid.startswith("awareness_gate:"):
            return
        gate_text = artist_gid.split(":", 1)[1]
        try:
            gate = int(gate_text)
        except (TypeError, ValueError):
            return
        _show_awareness_gate_info(gate)

    analytics_canvas.mpl_connect("pick_event", _on_awareness_pick)

    layout.addLayout(left_panel_layout, 1)
    return chart_info_output
