from ephemeraldaddy.gui.features.charts.search_text import (
    database_search_text_is_active,
    database_search_text_matches,
)


def test_database_search_text_preserves_trailing_spaces():
    assert database_search_text_matches("Al ", "Al Smith")
    assert not database_search_text_matches("Al ", "Calvin Smith")
    assert not database_search_text_matches("Al ", "Al")


def test_database_search_text_preserves_leading_and_repeated_spaces():
    assert database_search_text_matches("  Al", "The Great  Al")
    assert not database_search_text_matches("  Al", "The Great Al")
    assert database_search_text_matches("Al  Smith", "Al  Smith")
    assert not database_search_text_matches("Al  Smith", "Al Smith")


def test_database_search_text_treats_space_only_queries_as_active():
    assert database_search_text_is_active(" ")
    assert database_search_text_matches(" ", "Al Smith")
    assert not database_search_text_matches(" ", "Madonna")


def test_database_search_text_still_matches_case_insensitively():
    assert database_search_text_matches("al ", "AL SMITH")
