from __future__ import annotations

from datetime import datetime, timezone
import sys
import types

from matplotlib.figure import Figure
from matplotlib.patches import Rectangle


class _QtStub:
    PointingHandCursor = object()
    DownArrow = object()
    RightArrow = object()
    ToolButtonTextBesideIcon = object()


class _SizePolicyStub:
    Expanding = object()
    Preferred = object()


class _DummyQtObject:
    def __init__(self, *args, **kwargs):
        pass


def _dummy_module_attr(_name: str) -> type[_DummyQtObject]:
    return _DummyQtObject


def _blend_hex_colors_stub(start_hex: str, _end_hex: str, _ratio: float) -> str:
    return start_hex


sys.modules.setdefault("PySide6", types.ModuleType("PySide6"))
qtcore_stub = sys.modules.setdefault("PySide6.QtCore", types.ModuleType("PySide6.QtCore"))
qtcore_stub.QSize = _DummyQtObject
qtcore_stub.Qt = getattr(qtcore_stub, "Qt", _QtStub)
qtcore_stub.__getattr__ = _dummy_module_attr
qtgui_stub = sys.modules.setdefault("PySide6.QtGui", types.ModuleType("PySide6.QtGui"))
qtgui_stub.QIcon = _DummyQtObject
qtgui_stub.__getattr__ = _dummy_module_attr
qtwidgets_stub = sys.modules.setdefault("PySide6.QtWidgets", types.ModuleType("PySide6.QtWidgets"))
qtwidgets_stub.QAbstractButton = _DummyQtObject
qtwidgets_stub.QComboBox = _DummyQtObject
qtwidgets_stub.QListView = _DummyQtObject
qtwidgets_stub.QSizePolicy = getattr(qtwidgets_stub, "QSizePolicy", _SizePolicyStub)
qtwidgets_stub.QToolButton = _DummyQtObject
qtwidgets_stub.__getattr__ = _dummy_module_attr
style_stub = sys.modules.get("ephemeraldaddy.gui.style")
if style_stub is not None and not hasattr(style_stub, "blend_hex_colors"):
    style_stub.blend_hex_colors = _blend_hex_colors_stub

from ephemeraldaddy.core.human_design_system import HumanDesignResult
from ephemeraldaddy.gui.features.charts.human_design_plot import draw_human_design_chart


def _minimal_hd_result(*, defined_centers: frozenset[str]) -> HumanDesignResult:
    return HumanDesignResult(
        birth_utc=datetime(2000, 1, 1, tzinfo=timezone.utc),
        design_utc=datetime(1999, 12, 15, tzinfo=timezone.utc),
        personality_activations=(),
        design_activations=(),
        active_gates=frozenset(),
        defined_channels=(),
        defined_centers=defined_centers,
        hd_type="Projector",
        authority="None",
        profile="1/3",
        strategy="Wait for the Invitation",
        split_definition="None",
        incarnation_cross="Unknown",
    )


def _center_patch_alpha_by_label(figure: Figure) -> dict[str, float]:
    ax = figure.axes[0]
    rectangles = [patch for patch in ax.patches if isinstance(patch, Rectangle)]
    center_text_by_position = {
        (round(text.get_position()[0], 6), round(text.get_position()[1], 6)): text.get_text()
        for text in ax.texts
    }
    alpha_by_label: dict[str, float] = {}
    for rect in rectangles:
        rect_center = (
            round(rect.get_x() + rect.get_width() / 2, 6),
            round(rect.get_y() + rect.get_height() / 2, 6),
        )
        alpha_by_label[center_text_by_position[rect_center]] = rect.get_alpha()
    return alpha_by_label


def test_draw_human_design_chart_uses_defined_center_override_union() -> None:
    figure = Figure()
    hd_result = _minimal_hd_result(defined_centers=frozenset({"Head"}))

    draw_human_design_chart(
        figure,
        hd_result,
        chart_theme_colors={"background": "#000000", "spine": "#222222"},
        defined_centers_override={"Head", "Sacral"},
    )

    alpha_by_center = _center_patch_alpha_by_label(figure)
    assert alpha_by_center["Head"] == 1.0
    assert alpha_by_center["Sacral"] == 1.0
    assert alpha_by_center["Root"] == 0.15
