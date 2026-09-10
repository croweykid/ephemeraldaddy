from __future__ import annotations

import pytest

from ephemeraldaddy.analysis import theme_evidence as evidence


def test_theme_evidence_reuses_one_scorer_context_and_emits_positive_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        evidence,
        "THEMES",
        {
            "sample": {
                "signs": ["Aries", "Cancer"],
                "gates": [1, 2],
            }
        },
    )
    monkeypatch.setattr(evidence, "WEIGHTED_THEME_PROPERTIES", ("signs", "gates"))
    monkeypatch.setattr(evidence, "theme_item_weight", lambda *_args: 1.0)

    context = {"marker": object()}
    calls = []

    def activation_context(_chart):
        calls.append("context")
        return context

    def activation_for_item(property_name, item, received_context):
        assert received_context is context
        values = {
            ("signs", "Aries"): 0.8,
            ("signs", "Cancer"): 0.0,
            ("gates", 1): 1.0,
            ("gates", 2): 0.0,
        }
        return values[(property_name, item)]

    monkeypatch.setattr(evidence.prominence, "_activation_context", activation_context)
    monkeypatch.setattr(evidence.prominence, "_activation_for_item", activation_for_item)

    result = evidence.calculate_theme_factor_evidence(object(), ["sample"])

    assert calls == ["context"]
    assert [(row.property_name, row.item, row.activation) for row in result["sample"]] == [
        ("signs", "Aries", pytest.approx(0.8)),
        ("gates", 1, pytest.approx(1.0)),
    ]


def test_theme_evidence_omits_unavailable_and_nonpositive_weight_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        evidence,
        "THEMES",
        {"sample": {"houses": [1], "bodies": ["Sun", "Saturn"]}},
    )
    monkeypatch.setattr(evidence, "WEIGHTED_THEME_PROPERTIES", ("houses", "bodies"))
    monkeypatch.setattr(
        evidence,
        "theme_item_weight",
        lambda _theme, _property, item: -1.0 if item == "Saturn" else 1.0,
    )
    monkeypatch.setattr(evidence.prominence, "_activation_context", lambda _chart: {})

    def activation_for_item(property_name, item, _context):
        if property_name == "houses":
            return None
        return 1.0

    monkeypatch.setattr(evidence.prominence, "_activation_for_item", activation_for_item)

    result = evidence.calculate_theme_factor_evidence(object(), ["sample"])

    assert [(row.property_name, row.item) for row in result["sample"]] == [("bodies", "Sun")]


def test_theme_evidence_rejects_unknown_theme_keys():
    with pytest.raises(KeyError, match="Unknown Theme"):
        evidence.calculate_theme_factor_evidence(object(), ["not-a-theme"])
