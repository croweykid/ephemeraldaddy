from ephemeraldaddy.gui.dbv_search_panel import weight_is_at_least_triple_next_highest


def test_isolated_factor_threshold_is_loosened_by_fifteen_percent():
    weights = {"Sun": 25.5, "Moon": 10.0, "Mars": 4.0}

    assert weight_is_at_least_triple_next_highest(weights, "Sun")


def test_isolated_factor_threshold_still_rejects_non_isolated_weights():
    weights = {"Sun": 25.4, "Moon": 10.0, "Mars": 4.0}

    assert not weight_is_at_least_triple_next_highest(weights, "Sun")


def test_isolated_factor_any_uses_loosened_threshold():
    weights = {"Sun": 10.0, "Moon": 25.5, "Mars": 4.0}

    assert weight_is_at_least_triple_next_highest(weights, "Any")
