"""Human Design summary helpers for Chart View popouts."""

from __future__ import annotations

from typing import Any

from ephemeraldaddy.core.chart import Chart
from ephemeraldaddy.core.hd import get_line
from ephemeraldaddy.core.interpretations import AWARENESS_STREAMS
from ephemeraldaddy.gui.features.charts.metrics import chart_uses_houses
from ephemeraldaddy.gui.features.charts.text_summary import format_chart_text
from ephemeraldaddy.gui.style import CHART_DATA_DIVIDER


def build_human_design_chart_data_output(
    chart: Chart,
    *,
    aspect_sort: str,
) -> tuple[str, dict[int, Any], dict[int, Any], dict[int, Any], int]:
    """Build Human Design-centric chart data text for popout output.

    Includes the standard Positions section, then Gates/Lines/Awareness Streams.
    Excludes Houses and Aspects from the rendered output.
    """

    chart_summary_text, position_info_map, aspect_info_map, species_info_map = format_chart_text(
        chart,
        aspect_sort=aspect_sort,
    )
    summary_lines = chart_summary_text.splitlines()
    positions_start_index = next(
        (idx for idx, line in enumerate(summary_lines) if line.strip() == "POSITIONS"),
        0,
    )
    houses_header_index = next(
        (
            idx
            for idx, line in enumerate(summary_lines[positions_start_index + 1 :], start=positions_start_index + 1)
            if line.strip() == "HOUSES"
        ),
        len(summary_lines),
    )
    position_lines = summary_lines[positions_start_index:houses_header_index]

    use_houses = chart_uses_houses(chart)
    active_longitudes = [
        lon
        for body, lon in (getattr(chart, "positions", {}) or {}).items()
        if isinstance(lon, (int, float))
        and (use_houses or body not in {"AS", "MC", "DS", "IC"})
    ]
    active_gate_set = {get_line(float(lon))[0] for lon in active_longitudes}
    active_line_set = {(gate, line) for gate, line in (get_line(float(lon)) for lon in active_longitudes)}

    gates_text = ", ".join(str(gate) for gate in sorted(active_gate_set)) or "None"
    lines_text = (
        ", ".join(f"{gate}.{line}" for gate, line in sorted(active_line_set, key=lambda item: (item[0], item[1])))
        or "None"
    )

    awareness_lines: list[str] = []
    for stream in AWARENESS_STREAMS:
        stream_name = str(stream.get("name", "")).strip().title() or "Unknown"
        stream_type = str(stream.get("type", "")).strip().title() or "Unknown"
        required_gates = [int(gate) for gate in stream.get("gates", []) if isinstance(gate, int)]
        if not required_gates:
            awareness_lines.append(f"{stream_type}: {stream_name} - 0%. Missing all gates")
            continue
        completed_count = sum(1 for gate in required_gates if gate in active_gate_set)
        completion_pct = int(round((completed_count / len(required_gates)) * 100))
        missing = [str(gate) for gate in required_gates if gate not in active_gate_set]
        if missing:
            missing_text = f"Missing {', '.join(missing)}"
        else:
            missing_text = "Complete"
        awareness_lines.append(f"{stream_type}: {stream_name} - {completion_pct}%. {missing_text}")

    rendered_lines = [
        *position_lines,
        "",
        CHART_DATA_DIVIDER,
        "GATES",
        CHART_DATA_DIVIDER,
        gates_text,
        "",
        CHART_DATA_DIVIDER,
        "LINES",
        CHART_DATA_DIVIDER,
        lines_text,
        "",
        CHART_DATA_DIVIDER,
        "AWARENESS STREAMS",
        CHART_DATA_DIVIDER,
        *awareness_lines,
    ]
    return (
        "\n".join(rendered_lines),
        position_info_map,
        aspect_info_map,
        species_info_map,
        positions_start_index,
    )

