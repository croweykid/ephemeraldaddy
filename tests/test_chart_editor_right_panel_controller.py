import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from PySide6.QtWidgets import QApplication, QPushButton, QScrollArea, QStackedWidget

from ephemeraldaddy.gui.features.chart_editor.right_panel_controller import (
    ChartEditorRightPanelController,
)


def test_tab_activation_uses_only_explicit_widgets_and_operations():
    app = QApplication.instance() or QApplication([])
    stack = QStackedWidget()
    panels = {"analytics": QScrollArea(), "predictions": QScrollArea()}
    buttons = {"analytics": QPushButton(), "predictions": QPushButton()}
    for panel in panels.values():
        stack.addWidget(panel)
    for button in buttons.values():
        button.setCheckable(True)
    calls = []
    controller = ChartEditorRightPanelController(
        stack=stack,
        panels=panels,
        buttons=buttons,
        resolve_panel_key=lambda key: key,
        set_active_tab=lambda key, scroll: calls.append(("active", key, scroll)),
        request_visible_canvas_layouts=lambda: calls.append(("layout",)),
        schedule_render=lambda key: calls.append(("render", key)),
        on_analytics_activated=lambda: calls.append(("analytics",)),
        scroll_panel_to_top=lambda scroll: calls.append(("top", scroll)),
    )

    controller.set_active_panel("predictions")
    app.processEvents()

    assert stack.currentWidget() is panels["predictions"]
    assert buttons["predictions"].isChecked()
    assert calls == [
        ("active", "predictions", panels["predictions"]),
        ("layout",),
        ("render", "predictions"),
    ]
