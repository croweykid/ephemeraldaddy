from ephemeraldaddy.gui.dbv_search_panel import weight_is_at_least_triple_next_highest


def test_specific_factor_matches_when_three_times_next_highest():
    weights = {"Virgo": 30.0, "Aries": 10.0, "Pisces": 9.5}

    assert weight_is_at_least_triple_next_highest(weights, "Virgo")


def test_specific_factor_fails_when_below_three_times_next_highest():
    weights = {"Virgo": 29.9, "Aries": 10.0, "Pisces": 1.0}

    assert not weight_is_at_least_triple_next_highest(weights, "Virgo")


def test_any_matches_any_isolated_factor_without_showing_all_charts():
    isolated_weights = {"Mars": 33.0, "Sun": 11.0, "Moon": 6.0}
    non_isolated_weights = {"Mars": 20.0, "Sun": 11.0, "Moon": 6.0}

    assert weight_is_at_least_triple_next_highest(isolated_weights, "Any")
    assert not weight_is_at_least_triple_next_highest(non_isolated_weights, "Any")
