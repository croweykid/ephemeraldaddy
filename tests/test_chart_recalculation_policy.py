from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace

from ephemeraldaddy.core.chart_recalculation_policy import ChartRecalculationPolicy


def _chart(**overrides):
    values = {
        "dt": datetime(2000, 1, 2, 3, 4),
        "birth_place": "London, UK",
        "lat": 51.5074,
        "lon": -0.1278,
        "birthtime_unknown": False,
        "retcon_time_used": False,
        "retcon_hour": None,
        "retcon_minute": None,
        "rectification_range_used": False,
        "rectification_range_start_minute": None,
        "rectification_range_end_minute": None,
        "use_birth_time_data": True,
        "chart_type": "personal",
        "source": "personal",
        "is_placeholder": False,
        "name": "Ada",
        "alias": "",
        "sentiments": [],
        "relationship_types": [],
        "tags": [],
        "gender": None,
        "alignment_score": None,
        "positive_sentiment_intensity": None,
        "negative_sentiment_intensity": None,
        "familiarity": None,
        "matched_expectations": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_new_chart_requires_full_refresh_classification():
    assert ChartRecalculationPolicy.changed_fields(None, _chart()) is None


def test_descriptive_change_does_not_become_birth_data_change():
    previous = _chart()
    current = deepcopy(previous)
    current.alias = "Countess of Lovelace"

    assert ChartRecalculationPolicy.changed_fields(previous, current) == {"alias"}


def test_birth_place_override_and_house_availability_are_authoritative():
    previous = _chart()
    current = deepcopy(previous)

    assert ChartRecalculationPolicy.changed_fields(
        previous, current, birth_place="Paris, France"
    ) == {"birth_data"}

    current.birthtime_unknown = True
    current.use_birth_time_data = False
    assert ChartRecalculationPolicy.changed_fields(previous, current) == {"birth_data"}


def test_rectified_time_state_is_authoritative_even_when_birth_time_is_unknown():
    previous = _chart(birthtime_unknown=True, use_birth_time_data=False)
    current = deepcopy(previous)
    current.retcon_time_used = True
    current.retcon_hour = 12
    current.retcon_minute = 30
    current.use_birth_time_data = True

    assert ChartRecalculationPolicy.changed_fields(previous, current) == {"birth_data"}


def test_chart_type_change_reports_membership_and_type_impacts():
    previous = _chart()
    current = deepcopy(previous)
    current.chart_type = "hypothetical"

    assert ChartRecalculationPolicy.changed_fields(previous, current) == {
        "aggregation_scope",
        "chart_type",
    }


def test_tag_identity_preserves_order_but_ignores_case_and_duplicates():
    previous = _chart(tags=["Friend", "Writer"])
    equivalent = deepcopy(previous)
    equivalent.tags = [" friend ", "WRITER", "writer"]
    reordered = deepcopy(previous)
    reordered.tags = ["Writer", "Friend"]

    assert ChartRecalculationPolicy.changed_fields(previous, equivalent) == set()
    assert ChartRecalculationPolicy.changed_fields(previous, reordered) == {"tags"}
