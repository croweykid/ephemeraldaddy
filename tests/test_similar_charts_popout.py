import sys
import types
from types import SimpleNamespace


def _install_pyside_stubs():
    pyside = types.ModuleType("PySide6")
    qt_core = types.ModuleType("PySide6.QtCore")
    qt_gui = types.ModuleType("PySide6.QtGui")
    qt_widgets = types.ModuleType("PySide6.QtWidgets")

    class _Qt:
        WindowModal = 1
        Horizontal = 2
        Vertical = 3
        AlignTop = 4
        AlignLeft = 5
        Widget = 6
        RichText = 7
        TextBrowserInteraction = 8
        TextSelectableByMouse = 9
        PointingHandCursor = 10
        DownArrow = 11
        RightArrow = 12

    class _QEventLoop:
        AllEvents = 1

    class _Widget:
        def __init__(self, *_args, **_kwargs):
            pass

    qt_core.QEventLoop = _QEventLoop
    qt_core.QSize = _Widget
    qt_core.Qt = _Qt
    qt_gui.QIcon = _Widget
    for name in (
        "QApplication",
        "QComboBox",
        "QDialog",
        "QFrame",
        "QHBoxLayout",
        "QLabel",
        "QProgressDialog",
        "QPushButton",
        "QScrollArea",
        "QSplitter",
        "QToolButton",
        "QVBoxLayout",
        "QWidget",
    ):
        setattr(qt_widgets, name, _Widget)

    sys.modules.setdefault("PySide6", pyside)
    sys.modules.setdefault("PySide6.QtCore", qt_core)
    sys.modules.setdefault("PySide6.QtGui", qt_gui)
    sys.modules.setdefault("PySide6.QtWidgets", qt_widgets)


def _install_style_stub():
    style = types.ModuleType("ephemeraldaddy.gui.style")
    style.CHART_DATA_DIVIDER = "---------"
    style.CHART_DATA_HIGHLIGHT_COLOR = "#ffffff"
    style.DEFAULT_DROPDOWN_STYLE = ""

    def format_chart_header(*_args, **_kwargs):
        return ""

    style.format_chart_header = format_chart_header
    sys.modules.setdefault("ephemeraldaddy.gui.style", style)


_install_pyside_stubs()
_install_style_stub()

from ephemeraldaddy.gui.features.charts.similar_charts_popout import (  # noqa: E402
    _human_design_gate_difference_lines,
)


def test_human_design_gate_differences_use_chart_labels():
    subject = SimpleNamespace(name="Alice", human_design_gates=[1, "2", "bad"])
    compared = SimpleNamespace(name="Boris", human_design_gates=[2, 3])

    assert _human_design_gate_difference_lines(subject, compared) == [
        "Only in Alice's chart: Gate 1",
        "Only in Boris' chart: Gate 3",
    ]
