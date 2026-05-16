import sys
import types
from types import SimpleNamespace


def _install_pyside_stubs():
    pyside = sys.modules.setdefault("PySide6", types.ModuleType("PySide6"))
    qt_core = sys.modules.setdefault("PySide6.QtCore", types.ModuleType("PySide6.QtCore"))
    qt_gui = sys.modules.setdefault("PySide6.QtGui", types.ModuleType("PySide6.QtGui"))
    qt_widgets = sys.modules.setdefault("PySide6.QtWidgets", types.ModuleType("PySide6.QtWidgets"))

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

    qt_core.QEventLoop = getattr(qt_core, "QEventLoop", _QEventLoop)
    qt_core.QSize = getattr(qt_core, "QSize", _Widget)
    qt_core.Qt = getattr(qt_core, "Qt", _Qt)
    qt_gui.QIcon = getattr(qt_gui, "QIcon", _Widget)
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
        if not hasattr(qt_widgets, name):
            setattr(qt_widgets, name, _Widget)

    pyside.QtCore = qt_core
    pyside.QtGui = qt_gui
    pyside.QtWidgets = qt_widgets


def _install_style_stub():
    style = sys.modules.setdefault("ephemeraldaddy.gui.style", types.ModuleType("ephemeraldaddy.gui.style"))
    style.CHART_DATA_DIVIDER = getattr(style, "CHART_DATA_DIVIDER", "---------")
    style.CHART_DATA_HIGHLIGHT_COLOR = getattr(style, "CHART_DATA_HIGHLIGHT_COLOR", "#ffffff")
    style.DEFAULT_DROPDOWN_STYLE = getattr(style, "DEFAULT_DROPDOWN_STYLE", "")

    def format_chart_header(*_args, **_kwargs):
        return ""

    if not hasattr(style, "format_chart_header"):
        style.format_chart_header = format_chart_header


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


def _band_for_test(_percent):
    return "test band", "#ffffff"


def test_similar_chart_export_rows_include_z_score():
    match = SimpleNamespace(
        chart_id=7,
        chart_name="Test Chart",
        score=0.82,
        placement_score=0.8,
        aspect_score=0.7,
        distribution_score=0.6,
        dominance_score=0.5,
    )

    from ephemeraldaddy.gui.features.charts.similar_charts_popout import (  # noqa: PLC0415
        build_similar_charts_export_lines,
        build_similar_charts_export_rows_from_matches,
    )

    rows = build_similar_charts_export_rows_from_matches(
        matches=[match],
        resolve_similarity_band=_band_for_test,
        similarity_average=70.0,
        similarity_standard_deviation=6.0,
    )

    assert rows[0]["similarity_z_score"] == 2.0
    markdown = "\n".join(build_similar_charts_export_lines(subject_name="Subject", rows=rows, is_markdown=True))
    plain = "\n".join(build_similar_charts_export_lines(subject_name="Subject", rows=rows, is_markdown=False))
    assert "+2.000" in markdown
    assert "z=+2.000" in plain


def test_similar_match_blocks_include_z_score():
    match = SimpleNamespace(
        chart_id=7,
        chart_name="Test Chart",
        score=0.82,
        placement_score=0.8,
        aspect_score=0.7,
        distribution_score=0.6,
        dominance_score=0.5,
        chart_uses_houses=True,
        algorithm_mode="default",
    )

    from ephemeraldaddy.gui.features.charts.similar_charts_popout import (  # noqa: PLC0415
        render_similar_match_blocks,
    )

    html = render_similar_match_blocks(
        matches=[match],
        highlight_color="#ffffff",
        resolve_similarity_band=_band_for_test,
        similarity_average=70.0,
        similarity_standard_deviation=6.0,
    )

    assert "z=+2.00" in html
