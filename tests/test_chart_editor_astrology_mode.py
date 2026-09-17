from types import SimpleNamespace

from ephemeraldaddy.core.sidereal import NakshatraPosition, ZodiacContext
from ephemeraldaddy.gui.features.chart_editor import astrology_mode


def test_sidereal_display_chart_is_a_copy_with_shared_uid(monkeypatch):
    chart = SimpleNamespace(
        chart_uid="PARENT01",
        positions={"Sun": 10.0},
        retrogrades={},
        houses=[1.0],
        housesPo=[2.0],
        aspects=[],
        is_placeholder=False,
    )
    sidereal = SimpleNamespace(
        positions={"Sun": 346.0},
        retrogrades={"Mercury": True},
        house_cusps=None,
        aspects=(),
        nakshatras={"Sun": NakshatraPosition(25, "Uttara Bhadrapada", 4, 12.0)},
        zodiac="sidereal",
        division="D1",
        ayanamsha="lahiri",
        source_recalculation_token="token",
    )
    monkeypatch.setattr(
        astrology_mode, "get_or_calculate_sidereal_chart_data", lambda _chart: sidereal
    )

    display = astrology_mode.chart_for_astrology_context(
        chart, ZodiacContext("sidereal", "lahiri")
    )

    assert display is not chart
    assert display.chart_uid == chart.chart_uid
    assert display.positions == {"Sun": 346.0}
    assert chart.positions == {"Sun": 10.0}
    assert display.houses == []
    assert display.nakshatras["Sun"].name == "Uttara Bhadrapada"
    assert display._tropical_source_chart is chart


def test_switching_sidereal_display_back_to_tropical_restores_original_coordinates(monkeypatch):
    chart = SimpleNamespace(
        chart_uid="PARENT01",
        positions={"Sun": 10.0},
        retrogrades={},
        houses=[1.0],
        housesPo=[2.0],
        aspects=[],
        is_placeholder=False,
    )
    sidereal = SimpleNamespace(
        positions={"Sun": 346.0},
        retrogrades={},
        house_cusps=None,
        aspects=(),
        nakshatras={"Sun": NakshatraPosition(25, "Uttara Bhadrapada", 4, 12.0)},
        zodiac="sidereal",
        division="D1",
        ayanamsha="lahiri",
        source_recalculation_token="token",
    )
    monkeypatch.setattr(
        astrology_mode, "get_or_calculate_sidereal_chart_data", lambda _chart: sidereal
    )

    display = astrology_mode.chart_for_astrology_context(
        chart, ZodiacContext("sidereal", "lahiri")
    )
    restored = astrology_mode.chart_for_astrology_context(
        display, ZodiacContext("tropical")
    )

    assert restored is chart
    assert restored.positions == {"Sun": 10.0}
    assert restored.houses == [1.0]
    assert restored.zodiac == "tropical"
    assert restored.division == "D1"


class Button:
    def __init__(self):
        self.visible = self.enabled = True

    def setVisible(self, value):
        self.visible = value

    def setEnabled(self, value):
        self.enabled = value


def test_sidereal_editor_hides_predictions_and_routes_away_from_active_prediction_tab():
    switches = []
    owner = SimpleNamespace(
        predictions_panel_button=Button(),
        _chart_right_panel_state=SimpleNamespace(active_tab="predictions"),
        _set_chart_right_panel=lambda key, **kwargs: switches.append((key, kwargs)),
        setWindowTitle=lambda title: setattr(owner, "title", title),
    )

    astrology_mode.apply_chart_editor_mode(
        owner, ZodiacContext("sidereal", "lahiri"), "PARENT01"
    )

    assert not owner.predictions_panel_button.visible
    assert not owner.predictions_panel_button.enabled
    assert switches == [("analytics", {"schedule_render": False})]
    assert "Sidereal (Lahiri)" in owner.title
