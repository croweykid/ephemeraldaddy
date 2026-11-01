"""Regression coverage for user-selected Lilith dominance mode."""

import sys
from types import ModuleType, SimpleNamespace

import pytest

style = sys.modules.get("ephemeraldaddy.gui.style")
if style is None:
    style = ModuleType("ephemeraldaddy.gui.style")
    sys.modules["ephemeraldaddy.gui.style"] = style
style.CHART_DATA_HIGHLIGHT_COLOR = "#ffffff"

from ephemeraldaddy.analysis import body_dynamics_reworked
from ephemeraldaddy.core.lilith_mode import (
    LILITH_MODES,
    filter_lilith_aspects,
    filtered_chart_export_payload,
    visible_lilith_positions,
)
from ephemeraldaddy.gui.features.charts import metrics


def example_chart():
    return SimpleNamespace(
        birthtime_unknown=False,
        houses=[float(i * 30) for i in range(12)],
        positions={
            "Mean Lilith": 15.0,
            "Osculating Lilith": 45.0,
            "Natural Lilith": 75.0,
            "Sun": 165.0,
        },
        aspects=[
            {"p1": "Mean Lilith", "p2": "Sun", "type": "trine", "delta": 0.0},
            {"p1": "Osculating Lilith", "p2": "Sun", "type": "trine", "delta": 0.0},
            {"p1": "Natural Lilith", "p2": "Sun", "type": "trine", "delta": 0.0},
            {"p1": "Mean Lilith", "p2": "Osculating Lilith", "type": "conjunction", "delta": 0.0},
        ],
    )


@pytest.mark.parametrize("mode", LILITH_MODES)
def test_sign_body_house_dominance_uses_only_selected_lilith(monkeypatch, mode):
    monkeypatch.setattr(metrics, "load_lilith_mode", lambda: mode)
    monkeypatch.setattr(body_dynamics_reworked, "load_lilith_mode", lambda: mode)
    whole = example_chart()
    selected = example_chart()
    selected.positions = visible_lilith_positions(selected.positions, mode)
    selected.aspects = filter_lilith_aspects(selected.aspects, mode)

    assert metrics.calculate_dominant_sign_weights(whole) == pytest.approx(
        metrics.calculate_dominant_sign_weights(selected)
    )
    assert metrics.calculate_dominant_planet_weights(whole) == pytest.approx(
        metrics.calculate_dominant_planet_weights(selected)
    )
    assert metrics.calculate_dominant_house_weights(whole) == pytest.approx(
        metrics.calculate_dominant_house_weights(selected)
    )
    body_weights = metrics.calculate_dominant_planet_weights(whole)
    assert mode in body_weights
    assert all(name == mode or name not in body_weights for name in LILITH_MODES)


def test_recursive_json_export_filter_keeps_metadata_and_source_unchanged():
    payload = {
        "positions": {"Mean Lilith": 12.0, "Osculating Lilith": 42.0, "Natural Lilith": 72.0},
        "aspects": [
            {"p1": "Moon", "p2": "Mean Lilith", "type": "conjunction"},
            {"p1": "Moon", "p2": "Osculating Lilith", "type": "square"},
        ],
        "metadata": None,
    }
    filtered = filtered_chart_export_payload(payload, "Osculating Lilith")
    assert filtered["positions"] == {"Osculating Lilith": 42.0}
    assert len(filtered["aspects"]) == 1
    assert filtered["metadata"] is None
    assert payload["positions"]["Mean Lilith"] == 12.0
