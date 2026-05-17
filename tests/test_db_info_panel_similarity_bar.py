import sys
import types


def _install_pyside_stubs():
    pyside = sys.modules.setdefault("PySide6", types.ModuleType("PySide6"))
    qt_core = sys.modules.setdefault(
        "PySide6.QtCore", types.ModuleType("PySide6.QtCore")
    )
    qt_gui = sys.modules.setdefault("PySide6.QtGui", types.ModuleType("PySide6.QtGui"))
    qt_widgets = sys.modules.setdefault(
        "PySide6.QtWidgets", types.ModuleType("PySide6.QtWidgets")
    )

    class _Qt:
        AlignRight = 1
        AlignVCenter = 2
        AlignLeft = 4
        RichText = 8
        TextBrowserInteraction = 16
        PointingHandCursor = 32

    class _Widget:
        def __init__(self, *_args, **_kwargs):
            self.updated = False

        def update(self):
            self.updated = True

    class _QProgressBar(_Widget):
        pass

    qt_core.Qt = getattr(qt_core, "Qt", _Qt)
    qt_core.QSize = getattr(qt_core, "QSize", _Widget)
    qt_gui.QColor = getattr(qt_gui, "QColor", _Widget)
    qt_gui.QPainter = getattr(qt_gui, "QPainter", _Widget)
    qt_gui.QPen = getattr(qt_gui, "QPen", _Widget)
    qt_gui.QIcon = getattr(qt_gui, "QIcon", _Widget)
    qt_widgets.QProgressBar = getattr(qt_widgets, "QProgressBar", _QProgressBar)
    for name in (
        "QHBoxLayout",
        "QLabel",
        "QListWidget",
        "QListWidgetItem",
        "QSizePolicy",
        "QTextEdit",
        "QToolButton",
        "QVBoxLayout",
        "QWidget",
    ):
        if not hasattr(qt_widgets, name):
            setattr(qt_widgets, name, _Widget)

    pyside.QtCore = qt_core
    pyside.QtGui = qt_gui
    pyside.QtWidgets = qt_widgets


_install_pyside_stubs()
style = sys.modules.setdefault(
    "ephemeraldaddy.gui.style", types.ModuleType("ephemeraldaddy.gui.style")
)
style.DATABASE_VIEW_PANEL_HEADER_STYLE = ""

from ephemeraldaddy.gui.features.charts.db_info_panel import (  # noqa: E402
    SimilarityPercentBar,
)


def test_similarity_percent_bar_accepts_norm_delta_overlay():
    bar = SimilarityPercentBar()

    bar.set_norm_delta_overlay(
        selection_percent=20,
        db_norm_percent=70,
        delta_rgb=(255, 45, 45),
    )

    assert bar._norm_delta_overlay == (20.0, 70.0, (255, 45, 45))
    assert bar.updated is True


def test_similarity_percent_bar_clears_invalid_norm_delta_overlay():
    bar = SimilarityPercentBar()

    bar.set_norm_delta_overlay(
        selection_percent=float("nan"),
        db_norm_percent=70,
        delta_rgb=(255, 45, 45),
    )

    assert bar._norm_delta_overlay is None
    assert bar.updated is True


def test_similarity_percent_bar_centers_database_norm_for_selection_delta():
    center = SimilarityPercentBar._centered_percent_x(
        content_left=0,
        content_width=100,
        percent_value=70,
        db_norm_percent=70,
        axis_span_percent=20,
    )
    right_of_center = SimilarityPercentBar._centered_percent_x(
        content_left=0,
        content_width=100,
        percent_value=80,
        db_norm_percent=70,
        axis_span_percent=20,
    )
    left_of_center = SimilarityPercentBar._centered_percent_x(
        content_left=0,
        content_width=100,
        percent_value=60,
        db_norm_percent=70,
        axis_span_percent=20,
    )

    assert center == 50
    assert right_of_center > center
    assert left_of_center < center


def test_standard_error_guides_are_hidden_for_tiny_samples():
    from ephemeraldaddy.gui.features.charts.db_info_panel import (
        _standard_error_guide_percents,
    )

    assert _standard_error_guide_percents(
        db_percent_value=50,
        total_count=2,
        show_standard_deviation_guides=True,
    ) == []
    assert _standard_error_guide_percents(
        db_percent_value=50,
        total_count=5,
        show_standard_deviation_guides=True,
    )
