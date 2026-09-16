import pytest

from ephemeraldaddy.gui.features.chart_editor.astrology_context import (
    ChartEditorModePolicy,
    SHARED_PERSON_PANELS,
)


def test_tropical_d1_keeps_predictions_and_coordinate_editing():
    policy = ChartEditorModePolicy("PARENT01", "tropical")
    assert policy.predictions_available
    assert policy.derived_coordinates_editable
    assert "predictions" in policy.available_panels


@pytest.mark.parametrize("division", ["D1", "D9"])
def test_sidereal_modes_hide_predictions_but_keep_shared_person_panels(division):
    policy = ChartEditorModePolicy("PARENT01", "sidereal", division)
    assert not policy.predictions_available
    assert not policy.derived_coordinates_editable
    assert SHARED_PERSON_PANELS <= policy.available_panels
    assert policy.resolve_panel("predictions") == "analytics"


def test_tropical_divisional_context_is_rejected():
    with pytest.raises(ValueError):
        ChartEditorModePolicy("PARENT01", "tropical", "D9")
