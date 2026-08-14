from types import SimpleNamespace

from ephemeraldaddy.gui.features.charts.duplicate_detection import (
    build_duplicate_save_warning,
    find_possible_duplicate_charts,
)


def _row(local_row_id: int, name: str, *, month=1, day=2, year=2000):
    row = [None] * 20
    row[0] = local_row_id
    row[1] = name
    row[2] = None
    row[15] = 0
    row[17] = month
    row[18] = day
    row[19] = year
    return tuple(row)


def test_duplicate_result_is_keyed_entirely_by_uid():
    rows = [_row(10, "Alice"), _row(20, "Alice")]

    result = find_possible_duplicate_charts(
        rows,
        chart_uids_by_local_row={10: "UID-ALICE-A", 20: "UID-ALICE-B"},
    )

    assert result.duplicate_uids == {"UID-ALICE-A", "UID-ALICE-B"}
    assert set(result.related_names) == result.duplicate_uids
    assert set(result.likelihood_by_chart_uid) == result.duplicate_uids
    assert set(result.duplicate_sort_key_by_chart_uid) == result.duplicate_uids
    assert set(result.duplicate_group_by_chart_uid) == result.duplicate_uids


def test_uid_exclusion_prevents_duplicate_pair_linking():
    rows = [_row(10, "Alice"), _row(20, "Alice")]

    result = find_possible_duplicate_charts(
        rows,
        chart_uids_by_local_row={10: "UID-ALICE-A", 20: "UID-ALICE-B"},
        excluded_pairs={("UID-ALICE-A", "UID-ALICE-B")},
    )

    assert result.duplicate_uids == {"UID-ALICE-A", "UID-ALICE-B"}
    assert result.related_names == {}


def test_rows_without_persisted_uid_are_not_duplicate_candidates():
    rows = [_row(10, "Alice"), _row(20, "Alice")]

    result = find_possible_duplicate_charts(
        rows,
        chart_uids_by_local_row={10: "UID-ALICE-A"},
    )

    assert result.duplicate_uids == set()


def test_duplicate_save_warning_displays_uid_not_local_row_id():
    chart = SimpleNamespace(
        name="Alice",
        alias="",
        birth_month=1,
        birth_day=2,
        birth_year=2000,
        is_placeholder=False,
    )

    warning = build_duplicate_save_warning(
        chart,
        [_row(10, "Alice")],
        {10: "UID-ALICE-A"},
    )

    assert warning is not None
    assert "UID UID-ALICE-A: Alice" in warning.message
    assert "#10" not in warning.message
