from ephemeraldaddy.gui.features.charts.sign_dominance_ranking import (
    complete_sign_weight_map,
    least_house_priority,
    resolve_complete_sign_weights,
)


ZODIAC_NAMES = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)


def _weights(**overrides: float) -> dict[str, float]:
    values = {sign: 1.0 for sign in ZODIAC_NAMES}
    values.update(overrides)
    return values


def test_empty_persisted_weights_recalculate_instead_of_becoming_zero():
    calls = 0

    def recalculate():
        nonlocal calls
        calls += 1
        return _weights(Aries=42.0)

    weights, recalculated = resolve_complete_sign_weights(
        {},
        {},
        ZODIAC_NAMES,
        recalculate,
    )

    assert recalculated is True
    assert calls == 1
    assert weights is not None
    assert weights["Aries"] == 42.0


def test_partial_weight_map_is_not_accepted_as_a_zero_for_missing_signs():
    partial = _weights(Aries=9.0)
    partial.pop("Pisces")

    assert complete_sign_weight_map(partial, ZODIAC_NAMES) is None

    weights, recalculated = resolve_complete_sign_weights(
        partial,
        None,
        ZODIAC_NAMES,
        lambda: _weights(Aries=7.5),
    )

    assert recalculated is True
    assert weights is not None
    assert weights["Aries"] == 7.5


def test_all_zero_weight_map_is_invalid_and_must_be_recalculated():
    all_zero = {sign: 0.0 for sign in ZODIAC_NAMES}
    assert complete_sign_weight_map(all_zero, ZODIAC_NAMES) is None


def test_least_mode_prioritizes_known_houses_before_unknown_house_fallbacks():
    known_rows = [
        {"name": f"Known {index:02d}", "value": index / 1000.0, "uses_houses": True}
        for index in range(1, 21)
    ]
    unknown_row = {"name": "Unknown", "value": 0.0, "uses_houses": False}

    ranked = sorted(
        [unknown_row, *known_rows],
        key=lambda row: (
            least_house_priority(least=True, uses_houses=row["uses_houses"]),
            row["value"],
            row["name"].casefold(),
        ),
    )

    assert unknown_row not in ranked[:20]
    assert ranked[-1] is unknown_row


def test_unknown_house_chart_is_used_when_known_house_candidates_run_out():
    known_rows = [
        {"name": "Known A", "value": 0.02, "uses_houses": True},
        {"name": "Known B", "value": 0.03, "uses_houses": True},
    ]
    unknown_rows = [
        {"name": "Unknown A", "value": 0.0, "uses_houses": False},
        {"name": "Unknown B", "value": 0.01, "uses_houses": False},
    ]

    ranked = sorted(
        [*unknown_rows, *known_rows],
        key=lambda row: (
            least_house_priority(least=True, uses_houses=row["uses_houses"]),
            row["value"],
            row["name"].casefold(),
        ),
    )

    assert ranked[:2] == known_rows
    assert ranked[2:] == unknown_rows


def test_house_priority_is_neutral_for_most_dominant_mode():
    assert least_house_priority(least=False, uses_houses=True) == 0
    assert least_house_priority(least=False, uses_houses=False) == 0
