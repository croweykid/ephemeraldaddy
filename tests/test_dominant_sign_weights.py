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


def test_dominant_sign_weights_include_final_house_weight_for_natural_sign():
    chart = SimpleNamespace(
        birthtime_unknown=False,
        houses=[150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0],
        positions={"Moon": 5.0},
        aspects=[],
    )

    house_weights = calculate_dominant_house_weights(chart)
    sign_weights = calculate_dominant_sign_weights(chart)

    assert house_weights[8] > 0.0
    assert sign_weights["Scorpio"] == house_weights[8]
