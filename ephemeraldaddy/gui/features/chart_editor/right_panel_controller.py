"""Explicit navigation boundary for the Chart Editor right-hand panel."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QAbstractButton, QScrollArea, QStackedWidget


class ChartEditorRightPanelController:
    """Activate Chart Editor panels without retaining the editor window.

    The legacy right-panel workflow still coordinates rendering and availability.
    This controller owns the migrated tab-navigation slice and receives every Qt
    widget and operation that slice needs explicitly.
    """

    def __init__(
        self,
        *,
        stack: QStackedWidget,
        panels: Mapping[str, QScrollArea],
        buttons: Mapping[str, QAbstractButton],
        resolve_panel_key: Callable[[str], str],
        set_active_tab: Callable[[str, QScrollArea], None],
        request_visible_canvas_layouts: Callable[[], None],
        schedule_render: Callable[[str], None],
        on_analytics_activated: Callable[[], None],
        scroll_panel_to_top: Callable[[QScrollArea], None],
    ) -> None:
        self._stack = stack
        self._panels = dict(panels)
        self._buttons = dict(buttons)
        self._resolve_panel_key = resolve_panel_key
        self._set_active_tab = set_active_tab
        self._request_visible_canvas_layouts = request_visible_canvas_layouts
        self._schedule_render = schedule_render
        self._on_analytics_activated = on_analytics_activated
        self._scroll_panel_to_top = scroll_panel_to_top

    def set_active_panel(
        self,
        panel_key: str,
        *,
        schedule_render: bool = True,
    ) -> None:
        """Activate a panel and reassert visible viewport-bound canvas sizing."""
        panel_key = self._resolve_panel_key(panel_key)
        active_scroll = self._panels.get(panel_key)
        if active_scroll is None:
            return

        self._stack.setCurrentWidget(active_scroll)
        self._set_active_tab(panel_key, active_scroll)
        for tab_key, button in self._buttons.items():
            button.setChecked(panel_key == tab_key)

        # Descendant layouts may settle after QStackedWidget exposes the page.
        QTimer.singleShot(0, self._request_visible_canvas_layouts)
        if panel_key == "analytics":
            self._on_analytics_activated()
        if panel_key in {"subjective_notes", "abc"}:
            self._scroll_panel_to_top(active_scroll)
        if not schedule_render:
            return
        if panel_key == "predictions":
            QTimer.singleShot(0, lambda: self._schedule_render(panel_key))
        else:
            self._schedule_render(panel_key)
