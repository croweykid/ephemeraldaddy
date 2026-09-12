"""Shared GUI scaffolding for global and personal Transit popouts."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QSplitter,
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
    chart_info_layout: QVBoxLayout
    left_stack: QStackedWidget
    main_stack: QStackedWidget


def _toolbar_tabs(
    labels: tuple[str, ...],
    stack: QStackedWidget,
    *,
    default_index: int,
) -> QHBoxLayout:
    """Build a compact panel-top row of buttons for a stacked view."""
    layout = QHBoxLayout()
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
    return layout


def _page() -> tuple[QWidget, QVBoxLayout]:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    return widget, layout


def build_transit_popout_scaffold(root_layout: QHBoxLayout) -> TransitPopoutScaffold:
    """Create the common two-panel Transit layout.

    The resizeable left panel owns Chart Drawing / Aspects controls in a top
    toolbar row, with the selected content directly below and Chart Info beneath
    that.  The larger main panel uses the same toolbar-over-content pattern for
    Table View / Theme View.  The initial horizontal split is approximately
    30% left panel and 70% main panel.
    """
    chart_page, chart_layout = _page()
    aspects_page, aspects_layout = _page()
    left_stack = QStackedWidget()
    left_stack.addWidget(chart_page)
    left_stack.addWidget(aspects_page)
    left_stack.setCurrentIndex(0)
    left_stack.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)

    chart_info, chart_info_layout = _page()
    chart_info.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)

    left_splitter = QSplitter(Qt.Vertical)
    left_splitter.setChildrenCollapsible(False)
    left_splitter.addWidget(left_stack)
    left_splitter.addWidget(chart_info)
    left_splitter.setStretchFactor(0, 3)
    left_splitter.setStretchFactor(1, 2)
    left_splitter.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)

    left_panel = QWidget()
    left_panel_layout = QVBoxLayout(left_panel)
    left_panel_layout.setContentsMargins(0, 0, 0, 0)
    left_panel_layout.setSpacing(6)
    left_panel_layout.addLayout(
        _toolbar_tabs(("Chart Drawing", "Aspects"), left_stack, default_index=0)
    )
    left_panel_layout.addWidget(left_splitter, 1)
    left_panel.setMinimumWidth(0)
    left_panel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)

    table_page, table_layout = _page()
    theme_page, theme_layout = _page()
    main_stack = QStackedWidget()
    main_stack.addWidget(table_page)
    main_stack.addWidget(theme_page)
    main_stack.setCurrentIndex(0)

    main_panel = QWidget()
    main_panel_layout = QVBoxLayout(main_panel)
    main_panel_layout.setContentsMargins(0, 0, 0, 0)
    main_panel_layout.setSpacing(6)
    main_panel_layout.addLayout(
        _toolbar_tabs(("Table View", "Theme View"), main_stack, default_index=0)
    )
    main_panel_layout.addWidget(main_stack, 1)
    main_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    main_splitter = QSplitter(Qt.Horizontal)
    main_splitter.setChildrenCollapsible(False)
    main_splitter.addWidget(left_panel)
    main_splitter.addWidget(main_panel)
    main_splitter.setStretchFactor(0, 3)
    main_splitter.setStretchFactor(1, 7)
    main_splitter.setSizes([360, 840])
    root_layout.addWidget(main_splitter, 1)

    return TransitPopoutScaffold(
        chart_drawing_layout=chart_layout,
        aspects_layout=aspects_layout,
        table_layout=table_layout,
        theme_layout=theme_layout,
        chart_info_layout=chart_info_layout,
        left_stack=left_stack,
        main_stack=main_stack,
    )
