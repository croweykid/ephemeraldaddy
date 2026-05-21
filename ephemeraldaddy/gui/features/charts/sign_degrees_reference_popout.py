from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.offsetbox import AnnotationBbox, HPacker, TextArea
from matplotlib.patches import Wedge

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QScrollArea, QSplitter, QTextBrowser, QToolButton, QVBoxLayout, QWidget

from ephemeraldaddy.analysis.human_design_reference import HD_GATES_BY_SIGN
from ephemeraldaddy.analysis.human_design_reference import GATE_COLORS, GATE_REFERENCE
from ephemeraldaddy.core.decans import ZODIAC_DECANS
from ephemeraldaddy.core.interpretations import (
    NAKSHATRA_PLANET_COLOR,
    NAKSHATRA_DESCRIPTIONS,
    NAKSHATRA_RANGES,
    PLANET_COLORS,
    SIGN_KEYWORDS_CANONICAL,
    SIGN_COLORS,
    ZODIAC_SIGNS,
)

from ephemeraldaddy.gui.features.charts.presentation import abbreviate_nakshatra_label
from ephemeraldaddy.gui.features.charts.exporters import get_text_export_path
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR, configure_collapsible_header_toggle, configure_share_export_icon_button

SIGN_ORDER = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


@dataclass(frozen=True)
class Segment:
    ring: str
    start: float
    end: float
    label: str


def _normalize_degree(value: float) -> float:
    wrapped = value % 360.0
    if wrapped < 0:
        wrapped += 360.0
    return wrapped


def _sign_index(name: str) -> int:
    return SIGN_ORDER.index(name)


def _absolute_deg(sign: str, degree: int, minute: int) -> float:
    return (_sign_index(sign) * 30.0) + degree + (minute / 60.0)


def _parse_dms_degree(text: str) -> float:
    cleaned = text.replace('"', "")
    deg_part, minute_part, sec_part = cleaned.split("°")[0], cleaned.split("°")[1].split("'")[0], cleaned.split("'")[1]
    return float(deg_part) + (float(minute_part) / 60.0) + (float(sec_part) / 3600.0)


def _build_gate_segments() -> list[Segment]:
    segments: list[Segment] = []
    for sign_name in SIGN_ORDER:
        entries = HD_GATES_BY_SIGN.get(sign_name, [])
        sign_base = _sign_index(sign_name) * 30.0
        for entry in entries:
            start_txt, end_txt = entry["degree_range"].split("–")
            start = sign_base + _parse_dms_degree(start_txt)
            end = sign_base + _parse_dms_degree(end_txt)
            if end <= start:
                end = sign_base + 30.0
            segments.append(Segment("gate", start, end, f"G{entry['gate']}"))

    segments.sort(key=lambda seg: seg.start)
    merged_segments: list[Segment] = []
    epsilon = 1e-6
    for segment in segments:
        if not merged_segments:
            merged_segments.append(segment)
            continue
        previous = merged_segments[-1]
        if previous.label == segment.label and abs(previous.end - segment.start) < epsilon:
            merged_segments[-1] = Segment(previous.ring, previous.start, segment.end, previous.label)
            continue
        merged_segments.append(segment)

    if len(merged_segments) > 1:
        first = merged_segments[0]
        last = merged_segments[-1]
        if (
            first.label == last.label
            and abs(last.end - 360.0) < epsilon
            and abs(first.start - 0.0) < epsilon
        ):
            merged_segments[0] = Segment(first.ring, last.start, first.end + 360.0, first.label)
            merged_segments.pop()

    if len(merged_segments) > 1:
        first = merged_segments[0]
        last = merged_segments[-1]
        if (
            first.label == last.label
            and abs(last.end - 360.0) < epsilon
            and abs(first.start - 0.0) < epsilon
        ):
            merged_segments[0] = Segment(first.ring, last.start, first.end + 360.0, first.label)
            merged_segments.pop()
    return merged_segments



def _segment_for_degree(segments: list[Segment], degree: float) -> Segment | None:
    for segment in segments:
        if segment.start <= degree < segment.end:
            return segment
    return None


def _split_segment_for_drawing(start: float, end: float) -> tuple[list[tuple[float, float]], float]:
    draw_start, draw_end = start, end
    while draw_start >= 360.0:
        draw_start -= 360.0
        draw_end -= 360.0
    while draw_start < 0.0:
        draw_start += 360.0
        draw_end += 360.0
    if draw_end > 360.0:
        return [(draw_start, 360.0), (0.0, draw_end - 360.0)], ((draw_start + draw_end) / 2.0) % 360.0
    return [(draw_start, draw_end)], (draw_start + draw_end) / 2.0


def show_sign_degrees_reference_popout(parent, register_popout_shortcuts=None) -> QDialog:
    dialog = QDialog(parent)
    dialog.setWindowTitle("Sign Degrees Reference Circle")
    dialog.resize(980, 860)
    dialog.setAttribute(Qt.WA_DeleteOnClose, True)

    layout = QVBoxLayout(dialog)
    splitter = QSplitter(Qt.Horizontal, dialog)
    layout.addWidget(splitter)

    figure = Figure(figsize=(8, 8), facecolor="#111111")
    canvas = FigureCanvas(figure)
    ax = figure.add_subplot(111)
    ax.set_facecolor("#111111")
    ax.set_aspect("equal")
    ax.axis("off")

    right_panel = QWidget(dialog)
    right_layout = QVBoxLayout(right_panel)
    right_layout.setContentsMargins(8, 8, 8, 8)
    right_layout.setSpacing(8)
    header_row = QHBoxLayout()
    degree_header = QLabel("—")
    degree_header.setAlignment(Qt.AlignCenter)
    degree_header.setStyleSheet("font-size: 16px; font-weight: 700; color: #f7f7f7;")
    export_button = QToolButton(right_panel)
    configure_share_export_icon_button(
        export_button,
        share_icon_path=str((Path(__file__).resolve().parents[3] / "graphics" / "share_icon2.png")) if (Path(__file__).resolve().parents[3] / "graphics" / "share_icon2.png").exists() else None,
        tooltip="Export sign degree analysis as TXT/MD",
    )
    header_row.addWidget(degree_header, 1)
    header_row.addWidget(export_button, 0, Qt.AlignRight)
    right_layout.addLayout(header_row)

    scroll = QScrollArea(right_panel)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.NoFrame)
    scroll_host = QWidget(scroll)
    scroll_layout = QVBoxLayout(scroll_host)
    scroll_layout.setContentsMargins(0, 0, 0, 0)
    scroll_layout.setSpacing(6)
    scroll.setWidget(scroll_host)
    right_layout.addWidget(scroll, 1)

    section_contents: dict[str, QTextBrowser] = {}
    section_toggles: dict[str, QToolButton] = {}
    section_bodies: dict[str, QWidget] = {}
    section_order = ("Sign", "Decan", "Nakshatra", "Gate")
    for section_name in section_order:
        section = QWidget(scroll_host)
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(3)
        toggle = QToolButton(section)
        configure_collapsible_header_toggle(
            toggle,
            title=section_name,
            expanded=True,
            style_sheet=(
                "QToolButton { border: none; color: #d4b06a; font-weight: 700; padding: 4px 2px; background: transparent; text-align: left; }"
                "QToolButton:hover { color: #f0cb7b; }"
            ),
        )
        section_layout.addWidget(toggle)
        body = QWidget(section)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(10, 0, 0, 0)
        body_layout.setSpacing(0)
        text = QTextBrowser(body)
        text.setOpenExternalLinks(False)
        text.setReadOnly(True)
        text.setFrameStyle(QTextBrowser.NoFrame)
        text.setStyleSheet("background: transparent;")
        body_layout.addWidget(text)
        section_layout.addWidget(body)
        toggle.toggled.connect(lambda checked, body_widget=body, btn=toggle: (body_widget.setVisible(checked), btn.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)))
        scroll_layout.addWidget(section)
        section_contents[section_name] = text
        section_toggles[section_name] = toggle
        section_bodies[section_name] = body
    scroll_layout.addStretch(1)

    splitter.addWidget(canvas)
    splitter.addWidget(right_panel)
    splitter.setSizes([700, 280])
    status_box = ax.text(
        -0.14,
        -0.08,
        "",
        transform=ax.transAxes,
        color=(0, 0, 0, 0),
        fontsize=9.2,
        ha="left",
        va="bottom",
        bbox={"facecolor": "#111111cc", "edgecolor": "#3a3a3a", "boxstyle": "round,pad=0.3"},
        zorder=98,
    )
    status_line_texts = []

    def _set_status_line_items(items: list[tuple[str, str, str]]) -> None:
        nonlocal status_line_texts
        for old_artist in status_line_texts:
            old_artist.remove()
        status_line_texts = []
        base_x = -0.132
        base_y = -0.068
        line_step = 0.034
        for idx, (header, value, value_color) in enumerate(items):
            y = base_y + ((len(items) - 1 - idx) * line_step)
            header_area = TextArea(
                header,
                textprops={
                    "color": CHART_DATA_HIGHLIGHT_COLOR,
                    "fontsize": 9.2,
                    "fontweight": "bold",
                },
            )
            value_area = TextArea(
                value,
                textprops={
                    "color": value_color,
                    "fontsize": 9.2,
                },
            )
            line_box = HPacker(children=[header_area, value_area], align="baseline", pad=0, sep=0)
            line_artist = AnnotationBbox(
                line_box,
                (base_x, y),
                xycoords=ax.transAxes,
                box_alignment=(0.0, 0.0),
                frameon=False,
                pad=0.0,
                zorder=99,
            )
            ax.add_artist(line_artist)
            status_line_texts.append(line_artist)

    _set_status_line_items([("Degree selected: ", "—", "#f7f7f7")])

    ring_map = {
        "sign": (0.00, 0.25),
        "decan": (0.25, 0.50),
        "nakshatra": (0.50, 0.75),
        "gate": (0.75, 1.00),
    }

    nak_segments: list[Segment] = []
    for nakshatra, start_sign, start_deg, start_min, end_sign, end_deg, end_min in NAKSHATRA_RANGES:
        start = _absolute_deg(start_sign, start_deg, start_min)
        end = _absolute_deg(end_sign, end_deg, end_min)
        if end <= start:
            end += 360.0
        nak_segments.append(Segment("nakshatra", start, end, nakshatra))

    gate_segments = _build_gate_segments()

    for i, sign_name in enumerate(SIGN_ORDER):
        start = i * 30.0
        end = start + 30.0
        sign_color = SIGN_COLORS[sign_name]
        theta1 = 90.0 - end
        theta2 = 90.0 - start

        inner_radius, outer_radius = ring_map["sign"]
        ax.add_patch(Wedge((0, 0), outer_radius, theta1, theta2, width=outer_radius-inner_radius, facecolor=sign_color, edgecolor="#1e1e1e", linewidth=1.1))
        glyph = ZODIAC_SIGNS[i]
        mid = math.radians(90.0 - (start + 15.0))
        r = inner_radius + ((outer_radius - inner_radius) * 0.64)
        ax.text(r * math.cos(mid), r * math.sin(mid), glyph, color="black", fontsize=14, ha="center", va="center", fontweight="bold")

        for decan in ZODIAC_DECANS[sign_name]:
            d_start = start + float(decan["degree_start"])
            d_end = start + float(decan["degree_end"])
            dtheta1 = 90.0 - d_end
            dtheta2 = 90.0 - d_start
            color = PLANET_COLORS.get(str(decan["subsign_ruler"]), "#aaaaaa")
            inner_radius, outer_radius = ring_map["decan"]
            ax.add_patch(Wedge((0, 0), outer_radius, dtheta1, dtheta2, width=outer_radius-inner_radius, facecolor=color, alpha=0.45, edgecolor="#1e1e1e", linewidth=0.8))
            dmid = math.radians(90.0 - ((d_start + d_end) / 2.0))
            dr = (inner_radius + outer_radius) / 2.0
            ax.text(dr * math.cos(dmid), dr * math.sin(dmid), f"d{decan['decan']}", color="#f0f0f0", fontsize=8, ha="center", va="center")

    for nak in nak_segments:
        theta1 = 90.0 - nak.end
        theta2 = 90.0 - nak.start
        inner_radius, outer_radius = ring_map["nakshatra"]
        nak_color = NAKSHATRA_PLANET_COLOR.get(nak.label, ("Unknown", "#66ccff"))[1]
        ax.add_patch(Wedge((0, 0), outer_radius, theta1, theta2, width=outer_radius-inner_radius, facecolor=nak_color, alpha=0.30, edgecolor="#1e1e1e", linewidth=0.7))
        mid = math.radians(90.0 - ((nak.start + nak.end) / 2.0))
        rr = (inner_radius + outer_radius) / 2.0
        nak_label = abbreviate_nakshatra_label(nak.label)
        oval_x_scale = 1.0
        oval_y_scale = 1.05
        x = (rr * oval_x_scale) * math.cos(mid)
        y = (rr * oval_y_scale) * math.sin(mid)
        is_vertical_axis_label = abs(math.cos(mid)) < 0.10
        ax.text(
            x,
            y,
            nak_label,
            color="#f7f7f7",
            fontsize=6.6,
            ha="center",
            va="center",
            rotation=-30 if is_vertical_axis_label else 0,
            rotation_mode="anchor",
        )

    for gate in gate_segments:
        inner_radius, outer_radius = ring_map["gate"]
        gate_number = int(gate.label[1:])
        gate_color = GATE_COLORS.get(gate_number, "#666666")
        theta1 = 90.0 - gate.end
        theta2 = 90.0 - gate.start
        ax.add_patch(Wedge((0, 0), outer_radius, theta1, theta2, width=outer_radius-inner_radius, facecolor=gate_color, alpha=0.38, edgecolor="#1e1e1e", linewidth=0.6))
        mid = math.radians(90.0 - ((gate.start + gate.end) / 2.0))
        rr = (inner_radius + outer_radius) / 2.0
        oval_x_scale = 1.0
        oval_y_scale = 1.0
        ax.text(
            (rr * oval_x_scale) * math.cos(mid),
            (rr * oval_y_scale) * math.sin(mid),
            gate.label,
            color="#ffffff",
            fontsize=6.2,
            ha="center",
            va="center",
        )

    def _on_click(event) -> None:
        if event.inaxes != ax or event.xdata is None or event.ydata is None:
            return
        x, y = float(event.xdata), float(event.ydata)
        radius = math.hypot(x, y)
        if radius <= 0.0 or radius > 1.0:
            return

        theta = (90.0 - math.degrees(math.atan2(y, x))) % 360.0
        absolute_degree = _normalize_degree(theta)
        sign_index = int(absolute_degree // 30.0)
        sign_name = SIGN_ORDER[sign_index]
        sign_local_degree = absolute_degree - (sign_index * 30.0)
        decan_index = min(2, int(sign_local_degree // 10.0))
        decan_data = ZODIAC_DECANS[sign_name][decan_index]

        nak_match = _segment_for_degree(nak_segments, absolute_degree)
        if nak_match is None:
            nak_match = _segment_for_degree(nak_segments, absolute_degree + 360.0)
        gate_match = _segment_for_degree(gate_segments, absolute_degree)

        gate_number = int(gate_match.label[1:]) if gate_match else None
        gate_reference = GATE_REFERENCE.get(gate_number, {})
        gate_name = str(gate_reference.get("name", "")).strip() or "Unknown"
        gate_theme = str(gate_reference.get("theme", "")).strip()
        gate_meaning = str(gate_reference.get("meaning", "")).strip() or "No gate reference available."
        sign_profile = SIGN_KEYWORDS_CANONICAL.get(sign_name.lower(), {})
        sign_color = SIGN_COLORS.get(sign_name, "#f7f7f7")
        nak_name = nak_match.label if nak_match else "Unknown"
        nak_shakti = NAKSHATRA_DESCRIPTIONS.get(nak_name, {}).get("shakti", "No shakti reference available.")
        decan_ruler_color = PLANET_COLORS.get(str(decan_data["subsign_ruler"]), "#f7f7f7")

        status_box.set_text("")
        _set_status_line_items(
            [
                ("Degree selected: ", f"{absolute_degree:.4f}°", "#f7f7f7"),
                ("Sign: ", f"{sign_name} ({sign_local_degree:.4f}° of sign)", sign_color),
                ("Decan: ", f"d{decan_data['decan']} ({decan_data['elemental_subsign']}/{decan_data['subsign_ruler']})", decan_ruler_color),
                ("Nakshatra: ", nak_name, NAKSHATRA_PLANET_COLOR.get(nak_name, ("", "#e0e0e0"))[1]),
                ("Gate: ", gate_match.label if gate_match else "Unknown", GATE_COLORS.get(gate_number, "#e0e0e0") if gate_number else "#e0e0e0"),
            ]
        )
        degree_header.setText(f"{absolute_degree:.4f}°")
        section_contents["Sign"].setHtml(
            f"<h3 style='margin:0 0 6px 0; color:{sign_color};'>{sign_name}</h3>"
            f"<div style='margin:0;'><span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Talents</span>"
            "<ul style='margin:0; padding-left:12px;'>"
            + "".join(f"<li>{item}</li>" for item in sign_profile.get("talents", []))
            + "</ul></div>"
            f"<div style='margin:4px 0 0 0;'><span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Challenges</span>"
            "<ul style='margin:0; padding-left:12px;'>"
            + "".join(f"<li>{item}</li>" for item in sign_profile.get("challenges", []))
            + "</ul></div>"
            f"<div style='margin:4px 0 0 0;'><span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Fears</span>"
            "<ul style='margin:0; padding-left:12px;'>"
            + "".join(f"<li>{item}</li>" for item in sign_profile.get("greatest_fears", []))
            + "</ul></div>"
            f"<div style='margin:4px 0 0 0;'><span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Motivations</span>"
            "<ul style='margin:0; padding-left:12px;'>"
            + "".join(f"<li>{item}</li>" for item in sign_profile.get("motivations", []))
            + "</ul></div>"
        )
        section_contents["Decan"].setHtml(
            f"<h3 style='margin:0 0 6px 0; color:{decan_ruler_color};'>Decan {decan_data['decan']}</h3>"
            f"<p style='margin-top:0;'>{decan_data.get('description', 'No decan description available.')}</p>"
        )
        section_contents["Nakshatra"].setHtml(
            f"<h3 style='margin:0 0 6px 0; color:{NAKSHATRA_PLANET_COLOR.get(nak_name, ('', '#e0e0e0'))[1]};'>{nak_name}</h3>"
            f"<p style='margin-top:0;'>{nak_shakti}</p>"
        )
        section_contents["Gate"].setHtml(
            f"<h3 style='margin:0 0 6px 0; color:{GATE_COLORS.get(gate_number, '#e0e0e0') if gate_number else '#e0e0e0'};'>{f'Gate {gate_number}: {gate_name}' if gate_number else 'Unknown Gate'}</h3>"
            f"<p style='margin:0 0 4px 0; color:{GATE_COLORS.get(gate_number, '#e0e0e0') if gate_number else '#e0e0e0'};'><i>{gate_theme if gate_theme else 'No gate theme available.'}</i></p>"
            f"<p style='margin-top:0;'>{gate_meaning}</p>"
        )
        def _export_analysis() -> None:
            rounded_degree = int(round(absolute_degree))
            default_stem = f"ephemeraldaddy_{rounded_degree}degree_analysis"
            settings = QSettings("Ephemeraldaddy", "Ephemeraldaddy")
            export_path = get_text_export_path(
                dialog,
                settings,
                dialog_title="Export degree analysis as TXT/MD",
                default_stem=default_stem,
                preference_key="sign_degree_analysis_export_extension",
            )
            if not export_path:
                return
            export_md = export_path.lower().endswith(".md")
            lines = [
                f"Degree: {absolute_degree:.4f}°",
                "",
                "## Sign",
                f"{sign_name}",
                "",
                "Talents:",
            ]
            for item in sign_profile.get("talents", []):
                lines.append(f"- {item}")
            lines.append("")
            lines.append("Challenges:")
            for item in sign_profile.get("challenges", []):
                lines.append(f"- {item}")
            lines.append("")
            lines.append("Fears:")
            for item in sign_profile.get("greatest_fears", []):
                lines.append(f"- {item}")
            lines.append("")
            lines.append("Motivations:")
            for item in sign_profile.get("motivations", []):
                lines.append(f"- {item}")
            lines.extend(["", "## Decan", f"Decan {decan_data['decan']}", str(decan_data.get("description", "")), "", "## Nakshatra", nak_name, nak_shakti, "", "## Gate", f"Gate {gate_number}: {gate_name}" if gate_number else "Unknown Gate", gate_theme if gate_theme else "No gate theme available.", gate_meaning])
            content = "\n".join(lines)
            if not export_md:
                content = content.replace("## ", "")
            Path(export_path).write_text(content, encoding="utf-8")
        try:
            export_button.clicked.disconnect()
        except Exception:
            pass
        export_button.clicked.connect(_export_analysis)
        canvas.draw_idle()

    canvas.mpl_connect("button_press_event", _on_click)
    ax.set_xlim(-1.12, 1.12)
    ax.set_ylim(-1.12, 1.12)
    canvas.draw_idle()

    if callable(register_popout_shortcuts):
        register_popout_shortcuts(dialog)

    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog
