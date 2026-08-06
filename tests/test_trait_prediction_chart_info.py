from types import SimpleNamespace

from ephemeraldaddy.gui.features.charts import trait_predictions


def test_trait_info_explains_dominance_and_formats_evidence_headers(monkeypatch):
    monkeypatch.setattr(
        trait_predictions,
        "matched_weighted_criteria",
        lambda _chart, _profile: {
            "positive": ["Aries", "Sun", "Ashwini", "Gate 12", "Sun in Aries"],
            "negative": [],
        },
    )
    trait = {
        "name": "Inventive",
        "description": "Finds original solutions.",
        "samples": 42,
        "profile": {
            "signs": {"Aries": 1},
            "bodies": {"Sun": 1},
            "nakshatras": {"Ashwini": 1},
            "gates": {12: 1},
            "positions": {"Sun in Aries": 1},
        },
    }

    result = trait_predictions._trait_info_html(trait, SimpleNamespace())

    assert "based on aggregated data from 42 charts" in result
    assert f"color:{trait_predictions.CHART_DATA_HIGHLIGHT_COLOR};" in result
    assert "Matching factors in this chart:</div>" in result
    assert "font-size:12px; font-weight:700; color:#9fd6aa;'>Supporting:</div>" in result
    assert "Aries dominant</li>" in result
    assert "Sun dominant</li>" in result
    assert "Ashwini dominant</li>" in result
    assert "Gate 12</li>" in result
    assert "Gate 12 dominant" not in result
    assert "Sun in Aries</li>" in result
    assert "Sun in Aries dominant" not in result
