from pathlib import Path

import pytest

from ephemeraldaddy.core.chart_data_fields import (
    ASTRO_DATA,
    ASTRO_DATA_CATEGORY,
    CHART_INFO_STATUS,
    CHART_INFO_STATUS_CATEGORY,
    NONASTRAL_DATA,
    NONASTRAL_DATA_CATEGORY,
    chart_data_category,
    require_nonastral_data_fields,
)
from ephemeraldaddy.core.trait_invalidation import (
    trait_definition_invalidation,
    trait_invalidation_for_chart_change,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROPERTY_MANAGER_SOURCE = (
    REPO_ROOT / "ephemeraldaddy/gui/property_manager.py"
).read_text(encoding="utf-8")


def test_chart_data_categories_are_disjoint():
    assert not ASTRO_DATA & NONASTRAL_DATA
    assert not ASTRO_DATA & CHART_INFO_STATUS
    assert not NONASTRAL_DATA & CHART_INFO_STATUS


def test_tags_and_subjective_metadata_are_nonastral():
    assert chart_data_category("tags") == NONASTRAL_DATA_CATEGORY
    assert chart_data_category("comments") == NONASTRAL_DATA_CATEGORY
    assert chart_data_category("biography") == NONASTRAL_DATA_CATEGORY
    assert chart_data_category("sentiments") == NONASTRAL_DATA_CATEGORY


def test_chart_result_eligibility_is_chart_info_status():
    assert chart_data_category("is_placeholder") == CHART_INFO_STATUS_CATEGORY
    assert chart_data_category("is_hypothetical") == CHART_INFO_STATUS_CATEGORY
    assert chart_data_category("is_hidden") == CHART_INFO_STATUS_CATEGORY
    assert chart_data_category("chart_type") == CHART_INFO_STATUS_CATEGORY


def test_astro_inputs_remain_astro_data():
    assert chart_data_category("datetime_iso") == ASTRO_DATA_CATEGORY
    assert chart_data_category("birth_place") == ASTRO_DATA_CATEGORY
    assert chart_data_category("lat") == ASTRO_DATA_CATEGORY


def test_legacy_narrow_persistence_accepts_metadata_and_status_but_not_astro():
    require_nonastral_data_fields({"tags", "comments", "is_placeholder"})
    with pytest.raises(ValueError):
        require_nonastral_data_fields({"tags", "datetime_iso"})


def test_nonastral_change_has_zero_trait_consequences():
    invalidation = trait_invalidation_for_chart_change(
        NONASTRAL_DATA_CATEGORY,
        {"abc", "def"},
    )
    assert not invalidation.has_trait_work
    assert not invalidation.score_chart_uids
    assert not invalidation.reposition_chart_uids
    assert not invalidation.membership_chart_uids
    assert not invalidation.refresh_trait_ui


def test_astro_change_recalculates_and_repositions_only_changed_charts():
    invalidation = trait_invalidation_for_chart_change(
        ASTRO_DATA_CATEGORY,
        {"abc", "Def"},
    )
    assert invalidation.score_chart_uids == frozenset({"ABC", "DEF"})
    assert invalidation.reposition_chart_uids == frozenset({"ABC", "DEF"})
    assert not invalidation.membership_chart_uids
    assert invalidation.refresh_trait_ui


def test_chart_info_status_changes_membership_without_rescoring():
    invalidation = trait_invalidation_for_chart_change(
        CHART_INFO_STATUS_CATEGORY,
        {"abc"},
    )
    assert invalidation.membership_chart_uids == frozenset({"ABC"})
    assert not invalidation.score_chart_uids
    assert not invalidation.reposition_chart_uids
    assert invalidation.refresh_trait_ui


def test_trait_definition_event_targets_only_named_trait():
    invalidation = trait_definition_invalidation(
        "Agreeableness",
        change_type="definition_changed",
    )
    assert invalidation.trait_names == frozenset({"Agreeableness"})
    assert not invalidation.score_chart_uids
    assert invalidation.refresh_trait_ui


@pytest.mark.parametrize("change_type", ["renamed", "archived", "unarchived", "deleted"])
def test_trait_presentation_events_do_not_request_chart_rescoring(change_type):
    invalidation = trait_definition_invalidation("Agreeableness", change_type=change_type)
    assert invalidation.trait_names == frozenset({"Agreeableness"})
    assert not invalidation.score_chart_uids
    assert not invalidation.reposition_chart_uids


def test_property_manager_nonastral_reload_blocks_rankings_and_generic_analysis():
    refresh_method = PROPERTY_MANAGER_SOURCE.split(
        "def _refresh_host_after_nonastral_change", 1
    )[1].split("def refresh_after_close", 1)[0]
    assert 'host._refresh_visible_rankings_sections = lambda: None' in refresh_method
    assert "refresh_metrics=False" in refresh_method
    assert "force_full_analysis_refresh=False" in refresh_method
    assert 'host._rankings_data_dirty = previous_dirty' in refresh_method


def test_property_manager_noop_close_does_not_reload_database():
    refresh_method = PROPERTY_MANAGER_SOURCE.split("def refresh_after_close", 1)[1].split(
        "def load_usage", 1
    )[0]
    assert "if not needs_refresh:" in refresh_method
    assert "return" in refresh_method
    assert "self._refresh_host_after_nonastral_change()" in refresh_method
