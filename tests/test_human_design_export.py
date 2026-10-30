"""Human Design popout export must include each clickable Chart Info explanation."""

from pathlib import Path

from ephemeraldaddy.gui.features.charts.human_design_export import (
    build_human_design_popout_export_text,
)


def test_popout_export_collects_clickable_references_and_advanced_plugin_text():
    calls = []

    def render(entry):
        calls.append(dict(entry))
        if entry["kind"] == "hd_gate_line":
            label = f"Gate {entry['gate']}"
            if entry.get("line") is not None:
                label += f".{entry['line']}"
            return f"{label}\nAdvanced plugin supplement:\n• Gate summary: supplemented"
        return f"Details for {entry['kind']}: {entry}"

    text = build_human_design_popout_export_text(
        "PROFILE: 1/3\nACTIVE GATES: 1",
        {
            1: [
                {"kind": "hd_property", "property_key": "incarnation_cross", "property_value": "Cross A"},
                {"kind": "hd_property", "property_key": "incarnation_cross", "property_value": "Cross B"},
                {"kind": "hd_channel", "gate_a": 8, "gate_b": 1, "center": "G"},
                {"kind": "hd_gate_line", "gate": 1, "line": 3},
                {"kind": "hd_gate_line", "gate": 1, "line": 3},  # second clickable representation
            ],
            2: [
                {"kind": "hd_gate_line", "gate": 1, "line": None},
                {"kind": "hd_color", "color": 2},
                {"kind": "hd_tone", "tone": 5},
                {"kind": "hd_base", "base": 3},
            ],
        },
        render_detail=render,
        chart_name="Test Chart",
        bodygraph_gates=(1, 2),
        center_names=("Head", "G"),
    )

    assert text.startswith("Human Design Chart Export: Test Chart")
    assert "PROFILE: 1/3" in text
    assert "CHART INFO — PROPERTIES AND INCARNATION CROSSES" in text
    assert "CHART INFO — DEFINED CHANNELS" in text
    assert "CHART INFO — DISPLAYED GATE/LINE COMBINATIONS" in text
    assert "CHART INFO — BODYGRAPH GATES" in text
    assert "CHART INFO — CENTERS" in text
    assert "CHART INFO — BASES" in text
    assert "Advanced plugin supplement:" in text
    assert "Gate summary: supplemented" in text

    assert len([entry for entry in calls if entry["kind"] == "hd_property"]) == 2
    assert len([entry for entry in calls if entry["kind"] == "hd_channel"]) == 1
    assert len([entry for entry in calls if entry["kind"] == "hd_gate_line" and entry.get("line") == 3]) == 1
    assert {entry["gate"] for entry in calls if entry["kind"] == "hd_gate_line" and entry.get("line") is None} == {1, 2}
    assert {entry["center"] for entry in calls if entry["kind"] == "hd_center"} == {"Head", "G"}
    assert {entry["line"] for entry in calls if entry["kind"] == "hd_line"} == set(range(1, 7))
    assert {entry["color"] for entry in calls if entry["kind"] == "hd_color"} == set(range(1, 7))
    assert {entry["tone"] for entry in calls if entry["kind"] == "hd_tone"} == set(range(1, 7))
    assert {entry["base"] for entry in calls if entry["kind"] == "hd_base"} == {3}


def test_popout_export_keeps_unequal_unknown_time_gate_line_targets():
    targets = []

    def render(entry):
        targets.append((entry["gate"], entry["line"]))
        return f"{entry['gate']}.{entry['line']} from Chart Info"

    text = build_human_design_popout_export_text(
        "UNCERTAIN TIME VARIANTS",
        {3: [{"kind": "hd_gate_line", "gate": 2, "line": 1},
             {"kind": "hd_gate_line", "gate": 2, "line": 2}]},
        render_detail=render,
    )
    assert targets == [(2, 1), (2, 2)]
    assert "2.1 from Chart Info" in text and "2.2 from Chart Info" in text


def test_popout_export_button_uses_complete_details_provider():
    source = (
        Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/app.py"
    ).read_text(encoding="utf-8")
    start = source.index("    def on_get_human_design_info(")
    end = source.index("\n    def ", start + 1)
    method = source[start:end]
    assert "export_text_provider=_build_complete_hd_export" in method
    assert "build_human_design_popout_export_text(" in method
    assert "self._run_with_chart_info_output(scratch_output, _render)" in method
    assert "self._show_human_design_gate_line_info(" in method
    assert "self._show_human_design_property_info(" in method
    assert "self._show_human_design_channel_info(" in method
