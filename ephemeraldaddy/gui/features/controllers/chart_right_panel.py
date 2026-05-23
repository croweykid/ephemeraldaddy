"""Controller wrapper for Chart View's right-hand panel behaviors."""

from __future__ import annotations

from ephemeraldaddy.gui.features.charts.cv_right_panel_stack import (
    schedule_chart_render_for_active_right_panel,
    set_chart_right_panel,
    set_chart_right_panel_container_visible,
    sync_chart_right_panel_placeholder_state,
)


class ChartRightPanelController:
    """Adapter over right-panel helpers for incremental controller migration."""

    def __init__(self, owner: object) -> None:
        self._owner = owner

    def set_container_visible(self, visible: bool) -> None:
        """Show/hide Chart View's full right-side container."""
        set_chart_right_panel_container_visible(self._owner, visible)

    def set_active_panel(self, panel_key: str) -> None:
        """Activate one of the right-panel tabs."""
        set_chart_right_panel(self._owner, panel_key)

    def schedule_render_for_active_panel(self) -> None:
        """Queue tab-specific chart rendering after tab state changes."""
        schedule_chart_render_for_active_right_panel(self._owner)

    def sync_placeholder_state(self, chart: object | None) -> None:
        """Sync tab availability based on placeholder/saved chart status."""
        sync_chart_right_panel_placeholder_state(self._owner, chart)
