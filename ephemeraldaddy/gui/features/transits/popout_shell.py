"""Shared GUI scaffolding for Global and Personal Transit popouts.

Data calculation remains owned by each transit mode.  This module owns only the
window geometry: a tabbed auxiliary panel on the left and a large tabbed content
area on the right.  Both Global Transit and Personal Transit should build into
this same shell so future layout changes do not fork again.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QHBoxLayout,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True, slots=True)
class TransitPopoutHosts:
    """Layouts that callers populate with mode-specific controls and content."""

    chart_drawing_layout: QVBoxLayout
    aspects_layout: QHBoxLayout
    controls_layout: QVBoxLayout
    table_view_layout: QVBoxLayout
    theme_view_layout: QVBoxLayout
    left_tabs: QTabWidget
    main_tabs: QTabWidget



def _page_with_layout(
    parent: QWidget,
    *,
    horizontal: bool = False,
) -> tuple[QWidget, QVBoxLayout | QHBoxLayout]:
    page = QWidget(parent)
    layout = QHBoxLayout(page) if horizontal else QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    return page, layout



def build_transit_popout_shell(
    parent: QWidget,
    *,
    left_stretch: int = 1,
    main_stretch: int = 3,
) -> TransitPopoutHosts:
    """Install the shared two-column Transit popout layout on ``parent``.

    Left side:
      - Chart Drawing
      - Aspects (default)

    Main side:
      - controls header
      - west-tabbed Table View / Theme View content area
    """
    root = QHBoxLayout(parent)
    root.setContentsMargins(12, 12, 12, 12)
    root.setSpacing(10)

    left_tabs = QTabWidget(parent)
    left_tabs.setDocumentMode(True)
    left_tabs.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    chart_page, chart_layout = _page_with_layout(left_tabs)
    aspects_page, aspects_layout = _page_with_layout(left_tabs, horizontal=True)
    left_tabs.addTab(chart_page, "Chart Drawing")
    left_tabs.addTab(aspects_page, "Aspects")
    # Aspect analytics are currently more useful than the legacy wheel as the
    # first thing users see; Chart Drawing remains one click away.
    left_tabs.setCurrentWidget(aspects_page)
    root.addWidget(left_tabs, max(1, int(left_stretch)))

    main_host = QWidget(parent)
    main_layout = QVBoxLayout(main_host)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(8)

    controls_page, controls_layout = _page_with_layout(main_host)
    controls_page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
    main_layout.addWidget(controls_page, 0)

    main_tabs = QTabWidget(main_host)
    main_tabs.setDocumentMode(True)
    main_tabs.setTabPosition(QTabWidget.TabPosition.West)
    main_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    table_page, table_layout = _page_with_layout(main_tabs)
    theme_page, theme_layout = _page_with_layout(main_tabs)
    main_tabs.addTab(table_page, "Table View")
    main_tabs.addTab(theme_page, "Theme View")
    main_tabs.setCurrentWidget(table_page)
    main_layout.addWidget(main_tabs, 1)

    root.addWidget(main_host, max(1, int(main_stretch)))

    return TransitPopoutHosts(
        chart_drawing_layout=chart_layout,
        aspects_layout=aspects_layout,
        controls_layout=controls_layout,
        table_view_layout=table_layout,
        theme_view_layout=theme_layout,
        left_tabs=left_tabs,
        main_tabs=main_tabs,
    )
