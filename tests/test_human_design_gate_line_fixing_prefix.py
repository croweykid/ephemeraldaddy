"""Human Design gate-line fixings appear on the gate-line tokens themselves."""

from types import SimpleNamespace

from ephemeraldaddy.analysis.human_design import (
    _build_hd_positions_lines,
    _hd_activation_body_display_label,
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
        activation = next(a for a in activations if a.body == body)
        body_label = _hd_activation_body_display_label(activation)
        row_index = next(i for i, line in enumerate(rows) if line.startswith(body_label + " "))
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


def test_body_dignities_and_hd_gate_line_fixings_are_independent():
    """The example's zodiac markers and gate-line markers must coexist."""
    from ephemeraldaddy.analysis.human_design import (
        _hd_activation_body_dignity_prefix,
        _hd_activation_body_display_label,
    )

    samples = [
        # side, body, longitude, gate, line, body prefix, line prefix
        ("personality", "Earth", 47.787, 2, 5, "👑", "↓"),
        ("personality", "Jupiter", 258.007, 26, 2, "👑", ""),
        ("personality", "Pluto", 239.995, 14, 6, "👑", ""),
        ("design", "Sun", 139.787, 4, 1, "👑", ""),
        ("design", "Mercury", 155.277, 59, 6, "↑", "↓"),
        ("design", "Jupiter", 245.692, 34, 6, "👑", "↓"),
        ("design", "Pluto", 237.822, 14, 4, "👑", ""),
        ("design", "Mars", 193.729, 48, 5, "", "↑"),
        ("design", "Venus", 137.580, 7, 5, "", "↑"),
    ]
    activations = [
        HDActivation(
            body=body,
            side=side,
            longitude=longitude,
            gate=gate,
            line=line,
            color=4,
            tone=1,
            base=2,
            style="black" if side == "personality" else "red",
        )
        for side, body, longitude, gate, line, body_prefix, line_prefix in samples
    ]
    result = SimpleNamespace(
        personality_activations=tuple(a for a in activations if a.side == "personality"),
        design_activations=tuple(a for a in activations if a.side == "design"),
    )
    rows, info_map = _build_hd_positions_lines(result)

    for activation, sample in zip(activations, samples):
        side, body, longitude, gate, line, body_prefix, line_prefix = sample
        alias = "P." if side == "personality" else "D."
        expected_body = f"{alias} {body_prefix}{body}"
        expected_line = f"{line_prefix}{gate}.{line}"
        assert _hd_activation_body_dignity_prefix(activation) == body_prefix
        assert _hd_activation_body_display_label(activation) == expected_body
        row_idx = next(i for i, rendered in enumerate(rows) if rendered.startswith(expected_body + " "))
        rendered = rows[row_idx]
        assert expected_line in rendered
        assert rendered.count(expected_body) == 1
        gate_entries = [
            item for item in info_map[row_idx]
            if item["kind"] == "hd_gate_line" and "icon_index" not in item
        ]
        assert len(gate_entries) == 1
        entry = gate_entries[0]
        assert rendered[entry["span_start"]:entry["span_end"]] == f"{gate}.{line}"


def test_body_column_padding_accounts_for_crown_emoji_width():
    from ephemeraldaddy.analysis.human_design import (
        _hd_display_cell_width,
        _hd_pad_display_column,
    )

    names = ["P. 👑Earth", "D. 👑Jupiter", "D. ↑Mercury", "P. Saturn"]
    width = max(_hd_display_cell_width(name) for name in names)
    padded = [_hd_pad_display_column(name, width) for name in names]
    assert len({_hd_display_cell_width(value) for value in padded}) == 1
    assert _hd_display_cell_width("P. 👑Earth") == len("P. 👑Earth") + 1
