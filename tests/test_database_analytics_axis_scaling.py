import sys
import types

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


class _Dummy:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return _Dummy()

    def __getattr__(self, _name):
        return _Dummy()

    def __or__(self, _other):
        return self

    def __ror__(self, _other):
        return self


backend_qtagg = types.ModuleType("matplotlib.backends.backend_qtagg")
backend_qtagg.FigureCanvasQTAgg = FigureCanvasAgg
sys.modules.setdefault("matplotlib.backends.backend_qtagg", backend_qtagg)

qtcore = types.ModuleType("PySide6.QtCore")
qtcore.__getattr__ = lambda _name: _Dummy
qtcore.Qt = _Dummy()
qtcore.QTimer = type("QTimer", (), {"singleShot": staticmethod(lambda *_args, **_kwargs: None)})
qtwidgets = types.ModuleType("PySide6.QtWidgets")
qtwidgets.__getattr__ = lambda _name: _Dummy
for name in ("QFileDialog", "QLabel", "QLayout", "QMessageBox", "QSizePolicy"):
    setattr(qtwidgets, name, _Dummy)
qtgui = types.ModuleType("PySide6.QtGui")
qtgui.__getattr__ = lambda _name: _Dummy
pyside6 = types.ModuleType("PySide6")
pyside6.QtCore = qtcore
pyside6.QtWidgets = qtwidgets
pyside6.QtGui = qtgui
sys.modules.setdefault("PySide6", pyside6)
sys.modules.setdefault("PySide6.QtCore", qtcore)
sys.modules.setdefault("PySide6.QtWidgets", qtwidgets)
sys.modules.setdefault("PySide6.QtGui", qtgui)

from ephemeraldaddy.gui.features.charts.database_analytics import DatabaseAnalyticsChartsMixin


def test_percent_difference_axis_scales_symmetrically_to_visible_dataset():
    figure = Figure()
    ax = figure.add_subplot(111)

    axis_limit = DatabaseAnalyticsChartsMixin._configure_symmetric_percent_difference_axis(
        ax,
        [0.04, -0.01, 0.015],
    )

    assert axis_limit == 0.05
    assert ax.get_xlim() == (-0.05, 0.05)
    assert [tick.get_text() for tick in ax.get_xticklabels()] == ["-5%", "-2%", "0%", "2%", "5%"]


def test_percent_difference_axis_caps_full_range_when_data_needs_it():
    figure = Figure()
    ax = figure.add_subplot(111)

    axis_limit = DatabaseAnalyticsChartsMixin._configure_symmetric_percent_difference_axis(
        ax,
        [0.92, -0.8],
    )

    assert axis_limit == 1.0
    assert ax.get_xlim() == (-1.0, 1.0)
