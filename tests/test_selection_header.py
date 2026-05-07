from ephemeraldaddy.gui.features.charts.collections import CustomCollection
from ephemeraldaddy.gui.features.charts.selection_header import (
    SelectionSummaryCounts,
    format_selection_summary,
)


def _counts(selected=2, search_results=5, current_collection=7, database=11):
    return SelectionSummaryCounts.from_values(
        selected=selected,
        search_results=search_results,
        current_collection=current_collection,
        database=database,
    )


def test_all_collection_unfiltered_shows_database_total():
    assert (
        format_selection_summary(
            counts=_counts(),
            active_collection_id="all",
            active_filters=False,
        )
        == "Charts Selected: 2 of 11"
    )


def test_all_collection_filtered_shows_search_results_and_database_total():
    assert (
        format_selection_summary(
            counts=_counts(),
            active_collection_id="all",
            active_filters=True,
        )
        == "Charts Selected: 2 of 5 results. 11 in database"
    )


def test_non_all_collection_unfiltered_shows_collection_name_and_database_total():
    assert (
        format_selection_summary(
            counts=_counts(),
            active_collection_id="personal",
            active_filters=False,
        )
        == "Charts Selected: 2 of 7 in Personal collection. (11 in database)"
    )


def test_non_all_collection_filtered_shows_results_collection_and_database_total():
    assert (
        format_selection_summary(
            counts=_counts(),
            active_collection_id="personal",
            active_filters=True,
        )
        == "Charts Selected: 2 of 5 results. 7 in Personal collection. (11 in database)"
    )


def test_custom_collection_name_is_used_and_counts_are_hardened():
    assert (
        format_selection_summary(
            counts=_counts(
                selected="bad",
                search_results=-4,
                current_collection="3",
                database=None,
            ),
            active_collection_id="favorites",
            active_filters=True,
            custom_collections={
                "favorites": CustomCollection(
                    collection_id="favorites",
                    name="Favorites",
                    chart_ids=frozenset({1, 2, 3}),
                )
            },
        )
        == "Charts Selected: 0 of 0 results. 3 in Favorites collection. (0 in database)"
    )
