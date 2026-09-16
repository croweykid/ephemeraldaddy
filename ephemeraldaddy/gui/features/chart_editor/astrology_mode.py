"""Chart Editor adapters for selecting an astrology coordinate context."""

from __future__ import annotations

from copy import copy

from ephemeraldaddy.core.db import get_or_calculate_sidereal_chart_data
from ephemeraldaddy.core.sidereal import ZodiacContext
from ephemeraldaddy.gui.features.chart_editor.astrology_context import ChartEditorModePolicy


def chart_for_astrology_context(chart: object, context: ZodiacContext) -> object:
    """Return a chart-like display object without mutating cached Tropical data."""

    if context.zodiac == "tropical":
        # Sidereal display objects are shallow copies of the canonical Tropical
        # chart. Never relabel a Sidereal copy as Tropical: restore the original
        # coordinate source so positions/houses/aspects cannot leak across modes.
        tropical_chart = getattr(chart, "_tropical_source_chart", chart)
        setattr(tropical_chart, "zodiac", "tropical")
        setattr(tropical_chart, "division", "D1")
        return tropical_chart

    if bool(getattr(chart, "is_placeholder", False)):
        setattr(chart, "zodiac", "tropical")
        setattr(chart, "division", "D1")
        return chart

    if getattr(chart, "zodiac", None) == "sidereal":
        return chart

    sidereal = get_or_calculate_sidereal_chart_data(chart)
    display_chart = copy(chart)
    display_chart._tropical_source_chart = chart
    display_chart.positions = dict(sidereal.positions)
    display_chart.retrogrades = dict(sidereal.retrogrades)
    display_chart.houses = list(sidereal.house_cusps or ())
    display_chart.housesPo = []
    display_chart.aspects = [dict(aspect) for aspect in sidereal.aspects]
    display_chart.zodiac = sidereal.zodiac
    display_chart.division = sidereal.division
    display_chart.ayanamsha = sidereal.ayanamsha
    display_chart.sidereal_source_recalculation_token = sidereal.source_recalculation_token
    return display_chart


def apply_chart_editor_mode(owner: object, context: ZodiacContext, chart_uid: str) -> None:
    """Apply panel availability and honest context labeling to an editor shell."""
    policy = ChartEditorModePolicy(chart_uid, context.zodiac)
    setattr(owner, "_astrology_context", context)
    predictions_button = getattr(owner, "predictions_panel_button", None)
    if predictions_button is not None:
        predictions_button.setVisible(policy.predictions_available)
        predictions_button.setEnabled(policy.predictions_available)
    state = getattr(owner, "_chart_right_panel_state", None)
    if getattr(state, "active_tab", None) == "predictions" and not policy.predictions_available:
        switch_panel = getattr(owner, "_set_chart_right_panel", None)
        if callable(switch_panel):
            switch_panel("analytics", schedule_render=False)
    title = getattr(owner, "setWindowTitle", None)
    if callable(title):
        label = "Sidereal (Lahiri) Chart Editor" if context.zodiac == "sidereal" else "Chart Editor"
        title(label)
