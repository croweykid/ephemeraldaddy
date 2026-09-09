"""Clickable row sorting for the Personal Timeline table."""

from __future__ import annotations

import datetime
from types import ModuleType
from typing import Any, Iterable

from PySide6.QtCore import Qt


PERSONAL_TIMELINE_SORTABLE_COLUMNS = 7


def _stable_tiebreaker(window: Any) -> tuple[datetime.datetime, datetime.datetime, str]:
    return (
        window.start,
        window.end,
        str(window.transit.label).casefold(),
    )


def _timeline_sort_key(core: ModuleType, widget: Any, window: Any, column: int) -> tuple[object, ...]:
    """Return a typed sort key matching the meaning of each visible column."""
    metadata = core.metadata_for_window(window, getattr(widget, "_body_relevance", None))

    if column == 0:  # Age
        birth = getattr(widget.chart, "dt", None)
        if isinstance(birth, datetime.datetime):
            primary: object = (window.midpoint - birth).total_seconds()
        else:
            primary = float("inf")
    elif column == 1:  # Transit
        primary = str(window.transit.label).casefold()
    elif column == 2:  # Scope
        primary = str(metadata.cycle_scope).casefold()
    elif column == 3:  # Chart relevance
        relevance_text = ", ".join(metadata.relevant_bodies) if metadata.relevant_bodies else ""
        primary = relevance_text.casefold()
    elif column == 4:  # Start
        primary = window.start
    elif column == 5:  # End
        primary = window.end
    elif column == 6:  # Duration
        primary = float(window.duration_days)
    else:
        primary = window.start

    return (primary, *_stable_tiebreaker(window))


def _sorted_timeline_windows(
    core: ModuleType,
    widget: Any,
    windows: Iterable[Any],
) -> list[Any]:
    items = list(windows)
    column = getattr(widget, "_personal_timeline_sort_column", None)
    if not isinstance(column, int) or not 0 <= column < PERSONAL_TIMELINE_SORTABLE_COLUMNS:
        return items

    order = getattr(widget, "_personal_timeline_sort_order", Qt.AscendingOrder)
    return sorted(
        items,
        key=lambda window: _timeline_sort_key(core, widget, window, column),
        reverse=order == Qt.DescendingOrder,
    )


def _header_clicked(core: ModuleType, widget: Any, column: int) -> None:
    if not 0 <= int(column) < PERSONAL_TIMELINE_SORTABLE_COLUMNS:
        return

    previous_column = getattr(widget, "_personal_timeline_sort_column", None)
    previous_order = getattr(widget, "_personal_timeline_sort_order", Qt.AscendingOrder)
    if previous_column == column:
        order = (
            Qt.DescendingOrder
            if previous_order == Qt.AscendingOrder
            else Qt.AscendingOrder
        )
    else:
        order = Qt.AscendingOrder

    widget._personal_timeline_sort_column = int(column)
    widget._personal_timeline_sort_order = order

    header = widget.tree.header()
    header.setSortIndicatorShown(True)
    header.setSortIndicator(int(column), order)
    widget._populate(widget._visible_windows)


def install_personal_timeline_sorting(core: ModuleType) -> None:
    """Make each Personal Timeline column header toggle ascending/descending sort."""
    widget_type = core.PersonalTimelineWindowWidget
    if bool(getattr(widget_type, "_ephemeraldaddy_sorting_installed", False)):
        return

    original_init = widget_type.__init__
    original_populate = widget_type._populate

    def _init_with_sorting(self: Any, *args: object, **kwargs: object) -> None:
        original_init(self, *args, **kwargs)
        self._personal_timeline_sort_column = None
        self._personal_timeline_sort_order = Qt.AscendingOrder
        header = self.tree.header()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(False)
        header.sectionClicked.connect(
            lambda column: _header_clicked(core, self, int(column))
        )

    def _populate_with_sorting(self: Any, windows: Iterable[Any]) -> None:
        original_populate(self, _sorted_timeline_windows(core, self, windows))

    widget_type.__init__ = _init_with_sorting
    widget_type._populate = _populate_with_sorting
    widget_type._ephemeraldaddy_sorting_installed = True
