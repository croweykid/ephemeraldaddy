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


def test_human_design_channel_payload_sorts_without_display_label_lookup():
    selection_cache = {
        "human_design_channel_totals": {"57-20": 1, "1-8": 2},
        "human_design_channel_total_count": 3,
    }
    database_cache = {
        "human_design_channel_totals": {"10-20": 4},
        "human_design_channel_total_count": 4,
    }

    labels, selection_counts, database_counts, selection_total, database_total = (
        DatabaseAnalyticsChartsMixin._human_design_mode_payload(
            "hd_channels",
            selection_cache,
            database_cache,
        )
    )

    assert labels == ["1-8", "10-20", "57-20"]
    assert selection_counts["1-8"] == 2
    assert database_counts["10-20"] == 4
    assert selection_total == 3.0
    assert database_total == 4.0


def test_database_analysis_csv_export_uses_raw_labels_without_display_label_lookup(monkeypatch, tmp_path):
    import ephemeraldaddy.gui.features.charts.database_analytics as database_analytics

    output_path = tmp_path / "human-design.csv"
    monkeypatch.setattr(
        database_analytics.QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *_args, **_kwargs: (str(output_path), "CSV Files (*.csv)")),
        raising=False,
    )
    messages = []
    monkeypatch.setattr(
        database_analytics.QMessageBox,
        "information",
        staticmethod(lambda *_args: messages.append(_args)),
        raising=False,
    )
    monkeypatch.setattr(
        database_analytics.QMessageBox,
        "critical",
        staticmethod(lambda *_args: (_ for _ in ()).throw(AssertionError(_args))),
        raising=False,
    )

    class FakeDialog(DatabaseAnalyticsChartsMixin):
        _analysis_chart_export_rows = {
            "human_design": [
                ("57-20", 0.5, 0.25, 0.25, 1, 2, 50.0),
            ]
        }
        _analysis_chart_filenames = {"human_design": "human-design"}

        def _reactivate_database_view(self):
            pass

        def _analysis_matching_chart_names(self, chart_key, label):
            return "Example Chart"

    FakeDialog()._export_database_analysis_chart_csv("human_design", "Human Design")

    assert output_path.read_text(encoding="utf-8").splitlines()[1].startswith("57-20,")
    assert messages
