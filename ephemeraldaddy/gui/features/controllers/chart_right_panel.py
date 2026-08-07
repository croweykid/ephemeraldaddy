"""Compatibility imports for the migrated Chart Editor right-panel controller.

Delete this façade after external callers import ``chart_editor.right_panel_controller``.
"""

from ephemeraldaddy.gui.features.chart_editor.right_panel_controller import (
    ChartEditorRightPanelController,
    ChartRightPanelController,
    RightPanelSection,
)

__all__ = [
    "ChartEditorRightPanelController",
    "ChartRightPanelController",
    "RightPanelSection",
]
