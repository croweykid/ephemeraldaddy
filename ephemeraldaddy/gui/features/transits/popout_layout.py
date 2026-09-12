"""Shared GUI scaffolding for global and personal Transit popouts."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True, slots=True)
class TransitPopoutScaffold:
    """The named insertion points shared by both Transit windows."""

    chart_drawing_layout: QVBoxLayout
    aspects_layout: QVBoxLayout
    table_layout: QVBoxLayout
    theme_layout: QVBoxLayout
    left_stack: QStackedWidget
    detail_stack: QStackedWidget


def _vertical_tabs(
    labels: tuple[str, ...],
    stack: QStackedWidget,
    *,
    default_index: int,
) -> QWidget:
    rail = QWidget()
    layout = QVBoxLayout(rail)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    buttons: list[QPushButton] = []

    def select(index: int) -> None:
        stack.setCurrentIndex(index)
        for button_index, button in enumerate(buttons):
            button.setChecked(button_index == index)

    for index, label in enumerate(labels):
        button = QPushButton(label)
        button.setCheckable(True)
        button.setToolTip(f"Show {label.lower()}")
        button.clicked.connect(lambda _checked=False, index=index: select(index))
        layout.addWidget(button)
        buttons.append(button)
    layout.addStretch(1)
    select(default_index)
    return rail


def _page() -> tuple[QWidget, QVBoxLayout]:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    return widget, layout


def build_transit_popout_scaffold(root_layout: QHBoxLayout) -> TransitPopoutScaffold:
    """Create the common two-column Transit layout.

    The compact left panel defaults to Aspects and contains the chart drawing as
    an alternate page.  The larger detail panel defaults to Table View, with a
    Theme View alongside it.  Both use left-side buttons, matching Database
    View's panel-switching convention rather than top-mounted document tabs.
    """
    chart_page, chart_layout = _page()
    aspects_page, aspects_layout = _page()
    left_stack = QStackedWidget()
    left_stack.addWidget(chart_page)
    left_stack.addWidget(aspects_page)
    left_stack.setCurrentIndex(1)

    left = QWidget()
    left_layout = QHBoxLayout(left)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.addWidget(
        _vertical_tabs(("Chart Drawing", "Aspects"), left_stack, default_index=1)
    )
    left_layout.addWidget(left_stack, 1)
    left.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
    root_layout.addWidget(left, 2)

    table_page, table_layout = _page()
    theme_page, theme_layout = _page()
    detail_stack = QStackedWidget()
    detail_stack.addWidget(table_page)
    detail_stack.addWidget(theme_page)

    detail = QWidget()
    detail_layout = QHBoxLayout(detail)
    detail_layout.setContentsMargins(0, 0, 0, 0)
    detail_layout.addWidget(
        _vertical_tabs(("Table View", "Theme View"), detail_stack, default_index=0),
        0,
        Qt.AlignTop,
    )
    detail_layout.addWidget(detail_stack, 1)
    root_layout.addWidget(detail, 5)

    return TransitPopoutScaffold(
        chart_drawing_layout=chart_layout,
        aspects_layout=aspects_layout,
        table_layout=table_layout,
        theme_layout=theme_layout,
        left_stack=left_stack,
        detail_stack=detail_stack,
    )
