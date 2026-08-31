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
    assert "Missing Gates 29 &amp; 55</li>" in result
    assert "Mars not in Libra, Taurus or Virgo</li>" in result
    assert "Jupiter trine Pallas</li>" in result
    assert "Pluto in Taurus" not in result

    colorized = style.colorize_chart_info_html(result)
    assert "Mars" in colorized and "Libra" in colorized and "Gate 29" in colorized
    assert "font-weight:700;" in colorized


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
