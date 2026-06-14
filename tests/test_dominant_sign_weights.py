import sys
from types import ModuleType, SimpleNamespace

style_stub = sys.modules.get("ephemeraldaddy.gui.style")
if style_stub is None:
    style_stub = ModuleType("ephemeraldaddy.gui.style")
    sys.modules["ephemeraldaddy.gui.style"] = style_stub
style_stub.CHART_DATA_HIGHLIGHT_COLOR = "#ffffff"

from ephemeraldaddy.gui.features.charts.metrics import (
    calculate_dominant_house_weights,
    calculate_dominant_sign_weights,
)


def test_dominant_sign_weights_do_not_boost_absent_natural_house_signs():
    chart = SimpleNamespace(
        birthtime_unknown=False,
        houses=[150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0],
        positions={"Moon": 5.0},
        aspects=[],
    )

    house_weights = calculate_dominant_house_weights(chart)
    sign_weights = calculate_dominant_sign_weights(chart)

    assert house_weights[8] > 0.0
    assert sign_weights["Scorpio"] == 0.0


def test_dominant_sign_weights_do_not_treat_h4_or_h7_as_cancer_or_libra():
    chart = SimpleNamespace(
        birthtime_unknown=False,
        houses=[0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0],
        positions={"Sun": 95.0, "Moon": 185.0},
        aspects=[],
    )

    house_weights = calculate_dominant_house_weights(chart)
    sign_weights = calculate_dominant_sign_weights(chart)

    assert house_weights[4] > 0.0
    assert house_weights[7] > 0.0
    assert sign_weights["Cancer"] > 0.0
    assert sign_weights["Libra"] > 0.0

    # Move the bodies just out of the natural signs while keeping them in H4/H7.
    chart.positions = {"Sun": 125.0, "Moon": 215.0}
    house_weights = calculate_dominant_house_weights(chart)
    sign_weights = calculate_dominant_sign_weights(chart)

    assert house_weights[4] > 0.0
    assert house_weights[7] > 0.0
    assert sign_weights["Cancer"] == 0.0
    assert sign_weights["Libra"] == 0.0
