import sys
import types

from ephemeraldaddy.gui.dbv_search_panel import snapshot_human_design_search_selections


class _ModeWidget:
    def __init__(self, mode):
        self._mode = mode
        self.read_count = 0

    def mode(self):
        self.read_count += 1
        return self._mode


class _RadioButton:
    def __init__(self, checked):
        self._checked = checked

    def isChecked(self):
        return self._checked


def test_human_design_selections_are_normalized_in_one_widget_pass(monkeypatch):
    quad_state_module = types.ModuleType("ephemeraldaddy.gui.widgets.quad_state")
    quad_state_module.QuadStateSlider = type(
        "QuadStateSlider",
        (),
        {"MODE_EMPTY": 0, "MODE_TRUE": 1, "MODE_FALSE": 2},
    )
    monkeypatch.setitem(
        sys.modules,
        "ephemeraldaddy.gui.widgets.quad_state",
        quad_state_module,
    )
    type_widgets = {
        "Generator": _ModeWidget(1),
        "Projector": _ModeWidget(2),
    }
    profile_widgets = {
        "1/3": _ModeWidget(1),
        "2/4": _ModeWidget(0),
    }
    window = type(
        "Window",
        (),
        {
            "_human_design_type_filter_checkboxes": type_widgets,
            "_human_design_profile_filter_checkboxes": profile_widgets,
            "_human_design_type_filter_and": _RadioButton(False),
            "_human_design_profile_filter_and": _RadioButton(True),
        },
    )()

    snapshot = snapshot_human_design_search_selections(window)

    assert snapshot.included_types == {"Generator"}
    assert snapshot.excluded_types == {"Projector"}
    assert snapshot.included_profiles == {"1/3"}
    assert not snapshot.require_all_types
    assert snapshot.require_all_profiles
    widgets = (*type_widgets.values(), *profile_widgets.values())
    assert all(widget.read_count == 1 for widget in widgets)


def test_human_design_search_uses_tri_state_widgets_and_logic_toggles():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/dbv_search_panel.py"
    ).read_text(encoding="utf-8")

    assert 'add_hd_tri_state_filter(' in source
    assert '"human_design_type"' in source
    assert '"human_design_profile"' in source
    assert 'and_button = QRadioButton("&&")' in source
    assert 'or_button = QRadioButton("OR")' in source
    assert "and_button.setChecked(True)" in source
