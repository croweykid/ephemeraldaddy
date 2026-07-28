from types import SimpleNamespace

from ephemeraldaddy.core.db import SOURCE_HYPOTHETICAL, SOURCE_PERSONAL
from ephemeraldaddy.gui.features.charts.collections import (
    CustomCollection,
    DEFAULT_COLLECTION_HYPOTHETICAL,
    DEFAULT_COLLECTION_OPTIONS,
    chart_uids_in_collection,
    chart_belongs_to_collection,
    collection_filter_options,
)
from ephemeraldaddy.gui.features.charts.selection_header import (
    SelectionSummaryCounts,
    format_selection_summary,
)


def test_hypothetical_collection_is_last_default_collection():
    assert DEFAULT_COLLECTION_OPTIONS[-1] == ("Hypothetical", DEFAULT_COLLECTION_HYPOTHETICAL)


def test_hypothetical_collection_matches_hypothetical_chart_type():
    chart = SimpleNamespace(chart_type=SOURCE_HYPOTHETICAL, source=SOURCE_PERSONAL)

    assert chart_belongs_to_collection(
        DEFAULT_COLLECTION_HYPOTHETICAL,
        chart=chart,
        source=SOURCE_PERSONAL,
    )


def test_hypothetical_collection_matches_row_source_without_chart_object():
    assert chart_belongs_to_collection(
        DEFAULT_COLLECTION_HYPOTHETICAL,
        chart=None,
        source=SOURCE_HYPOTHETICAL,
    )


def test_hypothetical_collection_display_name_is_available_for_summaries():
    assert (
        format_selection_summary(
            counts=SelectionSummaryCounts.from_values(
                selected=1,
                search_results=1,
                current_collection=2,
                database=3,
            ),
            active_collection_id=DEFAULT_COLLECTION_HYPOTHETICAL,
            active_filters=False,
        )
        == "Charts Selected: 1 of 2 in Hypothetical collection. (3 in database)"
    )


def test_custom_collection_membership_prefers_chart_uids():
    collection = CustomCollection(
        collection_id="favorites",
        name="Favorites",
        chart_ids=frozenset({1}),
        chart_uids=frozenset({"STABLEUID123"}),
    )

    assert chart_belongs_to_collection(
        "favorites",
        chart=None,
        custom_collections={"favorites": collection},
        chart_uid="stableuid123",
    )
    assert chart_belongs_to_collection(
        "favorites",
        chart=None,
        custom_collections={"favorites": collection},
        chart_id=1,
    )


def test_collection_filter_options_put_all_first_and_sort_custom_names():
    custom = {
        "friends": CustomCollection("friends", "Friends", frozenset(), frozenset()),
        "celebs": CustomCollection("celebs", "Celebrities", frozenset(), frozenset()),
    }

    options = collection_filter_options(custom)

    assert options[0] == ("All collections", "all")
    assert options[-2:] == [("Celebrities", "celebs"), ("Friends", "friends")]


def test_chart_uids_in_collection_uses_stable_uid_membership():
    collection = CustomCollection(
        "friends", "Friends", frozenset({999}), frozenset({"FRIEND-UID"})
    )
    charts = {
        "FRIEND-UID": SimpleNamespace(source=SOURCE_PERSONAL),
        "OTHER-UID": SimpleNamespace(source=SOURCE_PERSONAL),
    }

    assert chart_uids_in_collection(
        "friends", charts_by_uid=charts, custom_collections={"friends": collection}
    ) == {"FRIEND-UID"}
