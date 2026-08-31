from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from ephemeraldaddy.gui import style
from ephemeraldaddy.gui.features.charts import trait_predictions
from ephemeraldaddy.gui.features.predictions import trait_factor_explanations as explanations


def test_trait_info_renders_compact_missing_section_with_semantic_tokens(monkeypatch):
    monkeypatch.setattr(explanations, "chart_uses_houses", lambda _chart: False)
    monkeypatch.setattr(
        trait_predictions,
        "matched_weighted_criteria",
        lambda _chart, _profile: {
            "positive": ["Pluto in Cancer", "Gate 49"],
            "negative": [],
        },
    )
    trait = {
        "name": "Published novelist",
        "description": "Based on the charts of published novelists.",
        "samples": 98,
        "profile": {
            "gates": {49: 5, 29: 4, 55: 3},
            "positions": {
                "Pluto in Cancer": 6,
                "Pluto in Taurus": 8,
                "Mars in Libra": 5,
                "Mars in Taurus": 4,
                "Mars in Virgo": 3,
            },
            "aspects": {"Jupiter trine Pallas": 2},
        },
    }

    result = trait_predictions._trait_info_html(trait, SimpleNamespace(name="Uncle Frank"))

    assert "Supporting:</div>" in result
    assert "Pluto in Cancer</li>" in result
    assert "Gate 49</li>" in result
    assert "Missing:</div>" in result
    assert "Missing Gates " in result and "29" in result and "55" in result
    assert style.chart_info_token_color_map()["Gate 29"] in result
    assert style.chart_info_token_color_map()["Gate 55"] in result
    assert "Mars not in Libra, Taurus or Virgo</li>" in result
    assert "Jupiter trine Pallas</li>" in result
    assert "Pluto in Taurus" not in result

    colorized = style.colorize_chart_info_html(result)
    assert "Mars" in colorized and "Libra" in colorized
    assert "font-weight:700;" in colorized


def test_missing_formatter_colors_profile_house_channel_and_bazi_semantics():
    color_map = style.chart_info_token_color_map()

    profile_html = explanations.missing_factor_html("Profile 4/6")
    assert color_map["Line 4"] in profile_html
    assert color_map["Line 6"] in profile_html

    house_html = explanations.missing_factor_html("House 10 not above baseline in chart")
    assert style.CHART_DATA_HIGHLIGHT_COLOR in house_html

    channel_html = explanations.missing_factor_html("Channel 29–46")
    assert color_map["Gate 29"] in channel_html
    assert color_map["Gate 46"] in channel_html

    bazi_html = explanations.missing_factor_html("BaZi Rat")
    assert style.CHART_DATA_HIGHLIGHT_COLOR in bazi_html


def test_trait_info_omits_missing_heading_when_nothing_meaningful_remains(monkeypatch):
    monkeypatch.setattr(explanations, "chart_uses_houses", lambda _chart: False)
    monkeypatch.setattr(
        trait_predictions,
        "matched_weighted_criteria",
        lambda _chart, _profile: {
            "positive": ["Pluto in Cancer", "Gate 49"],
            "negative": [],
        },
    )
    trait = {
        "name": "Example",
        "profile": {
            "gates": {49: 5},
            "positions": {"Pluto in Cancer": 6, "Pluto in Taurus": 8},
        },
    }

    result = trait_predictions._trait_info_html(trait, SimpleNamespace(name="Test Chart"))

    assert "Missing:</div>" not in result
    assert "Pluto in Taurus" not in result
