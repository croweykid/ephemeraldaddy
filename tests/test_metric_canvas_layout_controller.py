import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtWidgets import QApplication, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from ephemeraldaddy.gui.features.chart_editor.metric_canvas_layout import (
    MetricCanvasLayoutController,
)


def _process_events(app: QApplication) -> None:
    for _ in range(4):
        app.processEvents()


def test_hidden_canvas_waits_for_its_visible_viewport_before_accepting_width():
    app = QApplication.instance() or QApplication([])
    stack = QStackedWidget()
    stack.resize(420, 500)
    controller = MetricCanvasLayoutController(side_gutter_px=5, redraw=lambda _canvas: None)

    pages = []
    canvases = []
    for _ in range(2):
        content = QWidget()
        layout = QVBoxLayout(content)
        canvas = FigureCanvas(Figure(figsize=(8, 2.4)))
        layout.addWidget(canvas)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        stack.addWidget(scroll)
        controller.register(canvas, scroll)
        pages.append(scroll)
        canvases.append(canvas)

    stack.setCurrentWidget(pages[0])
    stack.show()
    _process_events(app)
    controller.request_visible()
    _process_events(app)

    hidden_width = canvases[1].width()
    assert hidden_width != pages[1].viewport().width() - 10

    stack.setCurrentWidget(pages[1])
    _process_events(app)
    controller.request_visible()
    _process_events(app)

    margins = canvases[1].parentWidget().layout().contentsMargins()
    expected_width = pages[1].viewport().width() - margins.left() - margins.right() - 10
    assert canvases[1].width() == expected_width


def test_canvas_resize_is_not_a_layout_input():
    source = __import__(
        "inspect"
    ).getsource(MetricCanvasLayoutController.eventFilter)
    assert "watched is scroll_area or watched is scroll_area.viewport()" in source
    assert "watched is canvas" not in source


def test_transient_missing_scroll_area_does_not_orphan_registered_canvas():
    app = QApplication.instance() or QApplication([])
    content = QWidget()
    layout = QVBoxLayout(content)
    canvas = FigureCanvas(Figure(figsize=(4, 2.4)))
    layout.addWidget(canvas)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(content)
    scroll.resize(420, 500)
    scroll.show()
    controller = MetricCanvasLayoutController(side_gutter_px=5, redraw=lambda _canvas: None)
    controller.register(canvas, scroll)
    _process_events(app)

    controller.register(canvas, None)
    scroll.resize(360, 500)
    _process_events(app)

    margins = layout.contentsMargins()
    expected_width = scroll.viewport().width() - margins.left() - margins.right() - 10
    assert canvas.width() == expected_width
