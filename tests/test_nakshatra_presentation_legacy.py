import sys
from types import ModuleType


style_stub = sys.modules.get("ephemeraldaddy.gui.style")
if style_stub is None:
    style_stub = ModuleType("ephemeraldaddy.gui.style")
    sys.modules["ephemeraldaddy.gui.style"] = style_stub
style_stub.CHART_DATA_HIGHLIGHT_COLOR = "#ffffff"

from ephemeraldaddy.gui.features.charts.presentation import get_nakshatra
from ephemeraldaddy.core.interpretations import NAKSHATRA_RANGES, ZODIAC_NAMES


def test_context_free_tropical_lookup_retains_reference_range_semantics():
    assert get_nakshatra(24.0) == "Ashwini"
    assert get_nakshatra(37.2) == "Bharani"

    for name, start_sign, start_deg, start_min, *_end in NAKSHATRA_RANGES:
        start = (
            ZODIAC_NAMES.index(start_sign) * 30.0
            + start_deg
            + start_min / 60.0
        )
        assert get_nakshatra(start + 0.001) == name
