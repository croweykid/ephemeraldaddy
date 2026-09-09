from __future__ import annotations

import datetime
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt

from ephemeraldaddy.gui.features.transits import personal_timeline_sorting as sorting


UTC = datetime.timezone.utc
BIRTH = datetime.datetime(2000, 1, 1, tzinfo=UTC)


class _Header:
    def __init__(self) -> None:
        self.indicator_shown = False
        self.indicator: tuple[int, object] | None = None

    def setSortIndicatorShown(self, shown: bool) -> None:  # noqa: N802 - Qt API shape
        self.indicator_shown = bool(shown)

    def setSortIndicator(self, column: int, order: object) -> None:  # noqa: N802
        self.indicator = (int(column), order)


class _Tree:
    def __init__(self) -> None:
        self._header = _Header()

    def header(self) -> _Header:
        return self._header


def _window(
    name: str,
    *,
    start_day: int,
    duration_days: int,
    scope: str,
    relevant_bodies: tuple[str, ...],
) -> SimpleNamespace:
    start = BIRTH + datetime.timedelta(days=start_day)
    end = start + datetime.timedelta(days=duration_days)
    transit = SimpleNamespace(label=name)
    metadata = SimpleNamespace(
        cycle_scope=scope,
        relevant_bodies=relevant_bodies,
    )
    return SimpleNamespace(
        transit=transit,
        start=start,
        end=end,
        midpoint=start + ((end - start) / 2),
        duration_days=float(duration_days),
        metadata=metadata,
    )


def _core() -> SimpleNamespace:
    return SimpleNamespace(
        metadata_for_window=lambda window, _relevance: window.metadata,
    )


def _widget(windows: list[SimpleNamespace]) -> SimpleNamespace:
    widget = SimpleNamespace(
        chart=SimpleNamespace(dt=BIRTH),
        _body_relevance=None,
        _personal_timeline_sort_column=None,
        _personal_timeline_sort_order=Qt.AscendingOrder,
        _visible_windows=windows,
        tree=_Tree(),
        rendered=[],
    )
    widget._populate = lambda rows: setattr(
        widget,
        "rendered",
        sorting._sorted_timeline_windows(_core(), widget, rows),
    )
    return widget


@pytest.fixture
def windows() -> list[SimpleNamespace]:
    return [
        _window(
            "Saturn square natal Sun",
            start_day=800,
            duration_days=90,
            scope="individualized",
            relevant_bodies=("Saturn",),
        ),
        _window(
            "Jupiter trine natal Moon",
            start_day=120,
            duration_days=12,
            scope="individualized",
            relevant_bodies=(),
        ),
        _window(
            "Pluto conjunct natal Pluto",
            start_day=1500,
            duration_days=420,
            scope="cohort/generational cycle",
            relevant_bodies=("Pluto",),
        ),
    ]


@pytest.mark.parametrize("column", range(sorting.PERSONAL_TIMELINE_SORTABLE_COLUMNS))
def test_every_visible_column_has_a_typed_sort_key(
    windows: list[SimpleNamespace],
    column: int,
) -> None:
    widget = _widget(windows)
    widget._personal_timeline_sort_column = column

    result = sorting._sorted_timeline_windows(_core(), widget, windows)

    assert sorted(id(item) for item in result) == sorted(id(item) for item in windows)


def test_age_sort_is_numeric_not_display_text(windows: list[SimpleNamespace]) -> None:
    widget = _widget(windows)
    widget._personal_timeline_sort_column = 0

    result = sorting._sorted_timeline_windows(_core(), widget, windows)

    assert [item.transit.label for item in result] == [
        "Jupiter trine natal Moon",
        "Saturn square natal Sun",
        "Pluto conjunct natal Pluto",
    ]


def test_duration_sort_is_numeric_and_reversible(windows: list[SimpleNamespace]) -> None:
    widget = _widget(windows)
    widget._personal_timeline_sort_column = 6

    ascending = sorting._sorted_timeline_windows(_core(), widget, windows)
    widget._personal_timeline_sort_order = Qt.DescendingOrder
    descending = sorting._sorted_timeline_windows(_core(), widget, windows)

    assert [item.duration_days for item in ascending] == [12.0, 90.0, 420.0]
    assert [item.duration_days for item in descending] == [420.0, 90.0, 12.0]


def test_repeated_header_click_toggles_sort_direction(windows: list[SimpleNamespace]) -> None:
    widget = _widget(windows)

    sorting._header_clicked(_core(), widget, 6)

    assert widget._personal_timeline_sort_column == 6
    assert widget._personal_timeline_sort_order == Qt.AscendingOrder
    assert [item.duration_days for item in widget.rendered] == [12.0, 90.0, 420.0]
    assert widget.tree.header().indicator_shown is True
    assert widget.tree.header().indicator == (6, Qt.AscendingOrder)

    sorting._header_clicked(_core(), widget, 6)

    assert widget._personal_timeline_sort_order == Qt.DescendingOrder
    assert [item.duration_days for item in widget.rendered] == [420.0, 90.0, 12.0]
    assert widget.tree.header().indicator == (6, Qt.DescendingOrder)


def test_new_header_resets_to_ascending(windows: list[SimpleNamespace]) -> None:
    widget = _widget(windows)
    sorting._header_clicked(_core(), widget, 6)
    sorting._header_clicked(_core(), widget, 6)

    sorting._header_clicked(_core(), widget, 4)

    assert widget._personal_timeline_sort_column == 4
    assert widget._personal_timeline_sort_order == Qt.AscendingOrder
    assert [item.start for item in widget.rendered] == sorted(item.start for item in windows)
