"""Human Design gate-line fixings appear on the gate-line tokens themselves."""

from types import SimpleNamespace

from ephemeraldaddy.analysis.human_design import (
    _build_hd_positions_lines,
    _hd_gate_line_fixing_prefix,
    _render_clickable_gate_line_summary,
    hd_line_fixing_for_activation,
)
from ephemeraldaddy.core.human_design_system import HDActivation


def _activation(body: str, gate: int, line: int) -> HDActivation:
    return HDActivation(
        body=body,
        side="personality",
        longitude=12.5,
        gate=gate,
        line=line,
        color=3,
        tone=2,
        base=1,
        style="black",
    )


def test_fixing_prefixes_are_symmetric_and_other_lines_unmarked():
    exalted = _activation("Moon", 1, 1)
    detriment = _activation("Uranus", 1, 1)
    neutral = _activation("Sun", 1, 1)
    assert hd_line_fixing_for_activation(exalted) == "exaltation"
    assert hd_line_fixing_for_activation(detriment) == "detriment"
    assert hd_line_fixing_for_activation(neutral) is None
    assert _hd_gate_line_fixing_prefix("exaltation") == "↑"
    assert _hd_gate_line_fixing_prefix("detriment") == "↓"
    assert _hd_gate_line_fixing_prefix(None) == ""


def test_positions_gate_line_prefixes_and_click_spans():
    activations = (
        _activation("Moon", 1, 1),
        _activation("Uranus", 1, 1),
        _activation("Sun", 1, 1),
    )
    result = SimpleNamespace(personality_activations=activations, design_activations=())
    rows, info_map = _build_hd_positions_lines(result)

    for body, expected in (("Moon", "↑1.1"), ("Uranus", "↓1.1"), ("Sun", "1.1")):
        row_index = next(i for i, line in enumerate(rows) if f"P. {body}" in line)
        row = rows[row_index]
        assert expected in row
        if body == "Uranus":
            assert "P. ↓Uranus" not in row
            assert "P. ↓ Uranus" not in row
        gate_entries = [
            e for e in info_map[row_index]
            if e["kind"] == "hd_gate_line" and "icon_index" not in e
        ]
        assert len(gate_entries) == 1
        entry = gate_entries[0]
        assert row[entry["span_start"]:entry["span_end"]] == "1.1"
        assert (entry["gate"], entry["line"]) == (1, 1)
        color_entries = [e for e in info_map[row_index] if e["kind"] == "hd_color"]
        assert color_entries
        assert row[color_entries[0]["span_start"]:color_entries[0]["span_end"]] == "3"


def test_gates_and_lines_summary_prefixes_detriment_and_preserves_click_targets():
    activations = (
        _activation("Moon", 1, 1),  # exalted
        _activation("Mars", 1, 2),  # detriment
        _activation("Sun", 1, 3),  # no fixing
    )
    assert hd_line_fixing_for_activation(activations[1]) == "detriment"
    rows, info_map = _render_clickable_gate_line_summary(
        {(1, 1), (1, 2), (1, 3)},
        activations,
    )
    assert rows == ["↑1.1, ↓1.2, 1.3"]
    entries = info_map[0]
    assert [(e["gate"], e["line"]) for e in entries] == [(1, 1), (1, 2), (1, 3)]
    for entry in entries:
        actual = rows[0][entry["span_start"]:entry["span_end"]]
        assert actual == f'{entry["gate"]}.{entry["line"]}'
