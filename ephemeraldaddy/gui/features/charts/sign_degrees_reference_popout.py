from __future__ import annotations

import math
from dataclasses import dataclass

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Wedge

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QSplitter, QTextBrowser, QVBoxLayout

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
from ephemeraldaddy.gui.style import CHART_DATA_HIGHLIGHT_COLOR

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
    return merged_segments



def _segment_for_degree(segments: list[Segment], degree: float) -> Segment | None:
    for segment in segments:
        if segment.start <= degree < segment.end:
            return segment
    return None


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

    info_output = QTextBrowser(dialog)
    info_output.setOpenExternalLinks(False)
    info_output.setReadOnly(True)
    info_output.setHtml("<b>Click a segment in any ring to see details.</b>")

    splitter.addWidget(canvas)
    splitter.addWidget(info_output)
    splitter.setSizes([700, 280])
    status_text = ax.text(
        -0.14,
        -0.08,
        "Degree selected: —",
        transform=ax.transAxes,
        color="#f7f7f7",
        fontsize=9.2,
        ha="left",
        va="bottom",
        bbox={"facecolor": "#111111cc", "edgecolor": "#3a3a3a", "boxstyle": "round,pad=0.3"},
        zorder=99,
    )

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
        draw_start, draw_end = nak.start, nak.end
        while draw_start >= 360.0:
            draw_start -= 360.0
            draw_end -= 360.0
        if draw_end > 360.0:
            parts = [(draw_start, 360.0), (0.0, draw_end - 360.0)]
        else:
            parts = [(draw_start, draw_end)]
        for p_start, p_end in parts:
            theta1 = 90.0 - p_end
            theta2 = 90.0 - p_start
            inner_radius, outer_radius = ring_map["nakshatra"]
            nak_color = NAKSHATRA_PLANET_COLOR.get(nak.label, ("Unknown", "#66ccff"))[1]
            ax.add_patch(Wedge((0, 0), outer_radius, theta1, theta2, width=outer_radius-inner_radius, facecolor=nak_color, alpha=0.30, edgecolor="#1e1e1e", linewidth=0.7))
            mid = math.radians(90.0 - ((p_start + p_end) / 2.0))
            rr = (inner_radius + outer_radius) / 2.0
            nak_label = abbreviate_nakshatra_label(nak.label)
            oval_x_scale = 1.0
            oval_y_scale = 1.15
            ax.text(
                (rr * oval_x_scale) * math.cos(mid),
                (rr * oval_y_scale) * math.sin(mid),
                nak_label,
                color="#f7f7f7",
                fontsize=6.6,
                ha="center",
                va="center",
            )

    for gate in gate_segments:
        theta1 = 90.0 - gate.end
        theta2 = 90.0 - gate.start
        inner_radius, outer_radius = ring_map["gate"]
        gate_number = int(gate.label[1:])
        gate_color = GATE_COLORS.get(gate_number, "#666666")
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

        status_text.set_text(
            f"Degree selected: {absolute_degree:.4f}°\n"
            f"Sign: {sign_name} ({sign_local_degree:.4f}° of sign)\n"
            f"Decan: d{decan_data['decan']} ({decan_data['elemental_subsign']}/{decan_data['subsign_ruler']})\n"
            f"Nakshatra: {nak_name}\n"
            f"Gate: {gate_match.label if gate_match else 'Unknown'}"
        )
        info_output.setHtml(
            f"<h3 style='margin:0; color:#f7f7f7;'>{absolute_degree:.4f}°</h3>"
            f"<h3 style='margin:10px 0 6px 0; color:{sign_color};'>{sign_name}</h3>"
            "<ul style='margin:0; padding-left:18px;'>"
            f"<li><span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Talents</span>"
            "<ul style='margin:0; padding-left:18px;'>"
            + "".join(f"<li>{item}</li>" for item in sign_profile.get("talents", []))
            + "</ul></li>"
            f"<li><span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Challenges</span>"
            "<ul style='margin:0; padding-left:18px;'>"
            + "".join(f"<li>{item}</li>" for item in sign_profile.get("challenges", []))
            + "</ul></li>"
            f"<li><span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Fears</span>"
            "<ul style='margin:0; padding-left:18px;'>"
            + "".join(f"<li>{item}</li>" for item in sign_profile.get("greatest_fears", []))
            + "</ul></li>"
            f"<li><span style='font-weight:700;color:{CHART_DATA_HIGHLIGHT_COLOR};'>Motivations</span>"
            "<ul style='margin:0; padding-left:18px;'>"
            + "".join(f"<li>{item}</li>" for item in sign_profile.get("motivations", []))
            + "</ul></li>"
            "</ul>"
            f"<h3 style='margin:10px 0 6px 0; color:{decan_ruler_color};'>Decan {decan_data['decan']}</h3>"
            f"<p style='margin-top:0;'>{decan_data.get('description', 'No decan description available.')}</p>"
            f"<h3 style='margin:10px 0 6px 0; color:{NAKSHATRA_PLANET_COLOR.get(nak_name, ('', '#e0e0e0'))[1]};'>{nak_name}</h3>"
            f"<p style='margin-top:0;'>{nak_shakti}</p>"
            f"<h3 style='margin:10px 0 6px 0; color:{GATE_COLORS.get(gate_number, '#e0e0e0') if gate_number else '#e0e0e0'};'>{f'Gate {gate_number}: {gate_name}' if gate_number else 'Unknown Gate'}</h3>"
            f"<p style='margin:0 0 4px 0;'><i>{gate_theme if gate_theme else 'No gate theme available.'}</i></p>"
            f"<p style='margin-top:0;'>{gate_meaning}</p>"
        )
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
