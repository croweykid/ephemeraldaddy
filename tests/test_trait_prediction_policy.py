from __future__ import annotations

from types import SimpleNamespace

from ephemeraldaddy.gui.features.charts.trait_prediction_policy import (
    filter_ascribed_prediction_metadata,
    gender_evidence_points,
    likelihood_from_evidence,
)
from ephemeraldaddy.gui.settings.core import (
    SETTINGS_KEY_PREDICTIONS_EXCLUDE_ASCRIBED_TRAIT_CHARTS,
    SETTINGS_KEY_PREDICTIONS_USE_TRAIT_GENDER_DISTRIBUTION,
    load_predictions_exclude_ascribed_trait_charts,
    load_predictions_use_trait_gender_distribution,
)


class _Settings:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def value(self, key, default=None):
        return self.values.get(key, default)


def _significant_gender_profile() -> dict:
    return {
        "genderDistribution": {
            "percentages": {"Female": 80.0, "Male": 20.0},
            "databasePercentages": {"Female": 50.0, "Male": 50.0},
            "statisticallySignificant": True,
            "significance": {
                "Female": {"significant": True},
                "Male": {"significant": False},
            },
            "significantCategories": ["Female"],
        }
    }


def test_gender_evidence_uses_only_significant_matching_category() -> None:
    profile = _significant_gender_profile()

    assert gender_evidence_points(profile, " female ") == 30.0
    assert gender_evidence_points(profile, "Male") is None
    assert gender_evidence_points(profile, None) is None


def test_gender_evidence_requires_distribution_level_significance() -> None:
    profile = _significant_gender_profile()
    profile["genderDistribution"]["statisticallySignificant"] = False

    assert gender_evidence_points(profile, "Female") is None


def test_gender_evidence_participates_in_both_score_and_possible_evidence() -> None:
    # Base score: 10 / 20 => 75%.  Gender adds +30 signed points and +30
    # possible points: 40 / 50 => 90%.
    assert likelihood_from_evidence(10.0, 20.0) == 75.0
    assert likelihood_from_evidence(10.0, 20.0, gender_delta=30.0) == 90.0
    assert likelihood_from_evidence(0.0, 20.0, gender_delta=-20.0) == 25.0


def test_ascribed_exclusion_is_trait_specific_uid_only_and_non_destructive() -> None:
    chart = SimpleNamespace(chart_uid=" abc-123 ", name="Mutable Name")
    traits = [
        {"name": "Ascribed", "profile": {"chartUIDs": ["ABC-123"]}},
        {"name": "Predicted", "profile": {"chartUIDs": ["OTHER-999"]}},
        {"name": "Legacy", "profile": {}},
    ]
    metadata = {
        "likelihoods": {"Ascribed": 90.0, "Predicted": 80.0, "Legacy": 70.0},
        "database_averages": {"Ascribed": 50.0, "Predicted": 50.0, "Legacy": 50.0},
        "deviations": {"Ascribed": 40.0, "Predicted": 30.0, "Legacy": 20.0},
        "above": {"Ascribed", "Predicted", "Legacy"},
        "below": set(),
    }

    filtered = filter_ascribed_prediction_metadata(chart, traits, metadata, enabled=True)

    assert filtered["likelihoods"] == {"Predicted": 80.0, "Legacy": 70.0}
    assert filtered["above"] == {"Predicted", "Legacy"}
    assert filtered["excluded_ascribed_traits"] == ["Ascribed"]
    assert "Ascribed" in metadata["likelihoods"]


def test_ascribed_exclusion_never_falls_back_to_name() -> None:
    chart = SimpleNamespace(chart_uid="", name="Ascribed")
    traits = [{"name": "Ascribed", "profile": {"chartUIDs": ["ABC-123"]}}]
    metadata = {
        "likelihoods": {"Ascribed": 90.0},
        "database_averages": {"Ascribed": 50.0},
        "deviations": {"Ascribed": 40.0},
        "above": {"Ascribed"},
        "below": set(),
    }

    assert filter_ascribed_prediction_metadata(chart, traits, metadata, enabled=True)["likelihoods"] == {
        "Ascribed": 90.0
    }


def test_prediction_policy_settings_default_off_and_parse_boolean_values() -> None:
    settings = _Settings()
    assert load_predictions_exclude_ascribed_trait_charts(settings) is False
    assert load_predictions_use_trait_gender_distribution(settings) is False

    settings = _Settings(
        {
            SETTINGS_KEY_PREDICTIONS_EXCLUDE_ASCRIBED_TRAIT_CHARTS: "true",
            SETTINGS_KEY_PREDICTIONS_USE_TRAIT_GENDER_DISTRIBUTION: 1,
        }
    )
    assert load_predictions_exclude_ascribed_trait_charts(settings) is True
    assert load_predictions_use_trait_gender_distribution(settings) is True
