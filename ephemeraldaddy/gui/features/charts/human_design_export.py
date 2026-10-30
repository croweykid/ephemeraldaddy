"""Complete Human Design popout text export from the chart's clickable targets.

The popout supplies the same renderer used by its Chart Info panel, so this
module stays independent of Qt, the optional supplement format, and the
reference-text implementation. This prevents exports from drifting out of sync
with interactive explanations.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any


DetailRenderer = Callable[[dict[str, object]], str]


def build_human_design_popout_export_text(
    summary_text: str,
    position_info_map: Mapping[int, object],
    *,
    render_detail: DetailRenderer,
    chart_name: str = "",
    bodygraph_gates: Iterable[int] = (),
    center_names: Iterable[str] = (),
) -> str:
    """Export the summary plus Chart Info for every Human Design target.

    The position map contains the exact targets exposed as clickable text,
    including uncertain-time variants and each independently linked cross.
    The bodygraph and analytics are separate interactive surfaces and must be
    supplied explicitly. Repeated links share a single exported explanation.
    """
    properties: dict[tuple[str, str], dict[str, object]] = {}
    channels: dict[tuple[int, int], dict[str, object]] = {}
    gate_lines: dict[tuple[int, int], dict[str, object]] = {}
    gates: dict[int, dict[str, object]] = {}
    centers: dict[str, dict[str, object]] = {}
    lines: dict[int, dict[str, object]] = {}
    colors: dict[int, dict[str, object]] = {}
    tones: dict[int, dict[str, object]] = {}
    bases: dict[int, dict[str, object]] = {}

    for row in sorted(position_info_map):
        raw_entries = position_info_map[row]
        entries = raw_entries if isinstance(raw_entries, (list, tuple)) else [raw_entries]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            kind = entry.get("kind")
            if kind == "hd_property":
                key = (str(entry.get("property_key", "")), str(entry.get("property_value", "")))
                properties.setdefault(key, entry)
            elif kind == "hd_channel":
                a, b = sorted((int(entry["gate_a"]), int(entry["gate_b"])))
                channels.setdefault((a, b), entry)
            elif kind == "hd_gate_line":
                gate = int(entry["gate"])
                if entry.get("line") is None:
                    gates.setdefault(gate, {"kind": kind, "gate": gate, "line": None})
                else:
                    line = int(entry["line"])
                    gate_lines.setdefault((gate, line), {"kind": kind, "gate": gate, "line": line})
            elif kind == "hd_color":
                value = int(entry["color"])
                colors.setdefault(value, {"kind": kind, "color": value})
            elif kind == "hd_tone":
                value = int(entry["tone"])
                tones.setdefault(value, {"kind": kind, "tone": value})
            elif kind == "hd_base":
                value = int(entry["base"])
                bases.setdefault(value, {"kind": kind, "base": value})
            elif kind == "hd_line":
                value = int(entry["line"])
                lines.setdefault(value, {"kind": kind, "line": value})

    # The bodygraph has individually clickable gate segments even when those
    # gates are not activated in the current chart.
    for gate in bodygraph_gates:
        number = int(gate)
        gates.setdefault(number, {"kind": "hd_gate_line", "gate": number, "line": None})
    for center in center_names:
        name = str(center).strip()
        if name:
            centers.setdefault(name, {"kind": "hd_center", "center": name})

    # Each of the six line/color/tone bars is a clickable analytics target,
    # including bars whose current count is zero. Bases are clicked in the
    # positions table, not in the analytics panel.
    for number in range(1, 7):
        lines.setdefault(number, {"kind": "hd_line", "line": number})
        colors.setdefault(number, {"kind": "hd_color", "color": number})
        tones.setdefault(number, {"kind": "hd_tone", "tone": number})

    name = str(chart_name or "").strip() or "Unnamed"
    parts = [
        f"Human Design Chart Export: {name}",
        "=" * (27 + len(name)),
        "",
        "CHART DATA",
        "----------",
        str(summary_text or "").strip() or "No chart data available.",
    ]

    def add_section(title: str, entries: Iterable[dict[str, object]]) -> None:
        rendered: list[str] = []
        for entry in entries:
            # Rendering is delegated to the actual Chart Info handlers,
            # including their installed Advanced Supplement plugin content.
            detail = str(render_detail(entry) or "").strip()
            if detail:
                rendered.append(detail)
        if rendered:
            parts.extend(["", title, "-" * len(title), "\n\n".join(rendered)])

    add_section("CHART INFO — PROPERTIES AND INCARNATION CROSSES", properties.values())
    add_section("CHART INFO — DEFINED CHANNELS", (channels[key] for key in sorted(channels)))
    add_section(
        "CHART INFO — DISPLAYED GATE/LINE COMBINATIONS",
        (gate_lines[key] for key in sorted(gate_lines)),
    )
    add_section("CHART INFO — BODYGRAPH GATES", (gates[key] for key in sorted(gates)))
    add_section("CHART INFO — CENTERS", centers.values())
    add_section("CHART INFO — LINE ARCHETYPES", (lines[key] for key in sorted(lines)))
    add_section("CHART INFO — COLORS", (colors[key] for key in sorted(colors)))
    add_section("CHART INFO — TONES", (tones[key] for key in sorted(tones)))
    add_section("CHART INFO — BASES", (bases[key] for key in sorted(bases)))
    return "\n".join(parts).rstrip() + "\n"
