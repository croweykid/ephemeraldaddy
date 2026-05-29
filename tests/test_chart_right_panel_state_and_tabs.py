import sys
import types
from types import SimpleNamespace


def _install_pyside_stubs() -> None:
    pyside = sys.modules.setdefault("PySide6", types.ModuleType("PySide6"))
    qt_core = sys.modules.setdefault("PySide6.QtCore", types.ModuleType("PySide6.QtCore"))
    qt_widgets = sys.modules.setdefault("PySide6.QtWidgets", types.ModuleType("PySide6.QtWidgets"))

    class _QTimer:
        @staticmethod
        def singleShot(_ms, fn):
            fn()

    class _Qt:
        StrongFocus = 0

    class _QWidget:
        def __init__(self, *_args, **_kwargs):
            self._visible = True

        def setVisible(self, visible):
            self._visible = bool(visible)

        def isVisible(self):
            return self._visible

        def findChildren(self, *_args, **_kwargs):
            return []

        def setGraphicsEffect(self, _effect):
            self._graphics_effect = _effect

    class _QScrollArea(_QWidget):
        def __init__(self):
            super().__init__()
            self._widget = _QWidget()

        def widget(self):
            return self._widget

    class _QAbstractButton(_QWidget):
        def __init__(self):
            super().__init__()
            self._enabled = True
            self._checked = False

        def isEnabled(self):
            return self._enabled

        def setEnabled(self, value):
            self._enabled = bool(value)

        def setChecked(self, value):
            self._checked = bool(value)

        def isCheckable(self):
            return True

    qt_core.QTimer = _QTimer
    qt_core.QPoint = object
    qt_core.QPropertyAnimation = object
    qt_core.QEasingCurve = object
    qt_core.Qt = _Qt
    qt_widgets.QWidget = _QWidget
    qt_widgets.QScrollArea = _QScrollArea
    qt_widgets.QAbstractButton = _QAbstractButton
    qt_widgets.QGraphicsOpacityEffect = object
    qt_widgets.QHBoxLayout = object
    qt_widgets.QPushButton = object
    qt_widgets.QSizePolicy = object
    qt_widgets.QStackedWidget = object
    qt_widgets.QVBoxLayout = object

    pyside.QtCore = qt_core
    pyside.QtWidgets = qt_widgets


_install_pyside_stubs()

from ephemeraldaddy.gui.features.charts.cv_right_panel_stack import (  # noqa: E402
    prepare_chart_right_panel_for_loading,
    reveal_chart_right_panel_after_loading,
    schedule_chart_render_for_active_right_panel,
    set_chart_right_panel,
    sync_chart_right_panel_placeholder_state,
)
from ephemeraldaddy.gui.features.charts.right_panel_state import ChartRightPanelState  # noqa: E402


class _FakeStack:
    def __init__(self):
        self.current = None

    def setCurrentWidget(self, widget):
        self.current = widget


class _FakeScroll:
    def __init__(self, name):
        self.name = name


class _FakeButton:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.checked = False
        self.visible = True

    def isEnabled(self):
        return self.enabled

    def setEnabled(self, value):
        self.enabled = bool(value)

    def setChecked(self, value):
        self.checked = bool(value)

    def setVisible(self, value):
        self.visible = bool(value)


def _owner():
    owner = SimpleNamespace()
    owner.chart_right_panel_stack = _FakeStack()
    owner.chart_analytics_panel_scroll = _FakeScroll("analytics")
    owner.predictions_panel_scroll = _FakeScroll("predictions")
    owner.subjective_notes_panel_scroll = _FakeScroll("subjective_notes")
    owner.chart_analytics_panel_button = _FakeButton(enabled=True)
    owner.predictions_panel_button = _FakeButton(enabled=True)
    owner.subjective_notes_panel_button = _FakeButton(enabled=True)
    owner._chart_right_panel_state = ChartRightPanelState(active_tab="subjective_notes")
    owner._schedule_chart_render_for_active_right_panel = lambda: None
    owner._collapse_similar_charts_section = lambda: None
    owner._is_placeholder_chart = lambda chart: bool(getattr(chart, "is_placeholder", False))
    owner.current_chart_id = 1
    return owner


def test_set_chart_right_panel_updates_state_stack_and_buttons():
    owner = _owner()

    set_chart_right_panel(owner, "predictions")

    assert owner._chart_right_panel_state.active_tab == "predictions"
    assert owner.chart_right_panel_stack.current is owner.predictions_panel_scroll
    assert owner.predictions_panel_button.checked is True
    assert owner.chart_analytics_panel_button.checked is False
    assert owner.subjective_notes_panel_button.checked is False


def test_set_chart_right_panel_falls_back_when_analytics_disabled():
    owner = _owner()
    owner.chart_analytics_panel_button.setEnabled(False)

    set_chart_right_panel(owner, "analytics")

    assert owner._chart_right_panel_state.active_tab == "subjective_notes"
    assert owner.chart_right_panel_stack.current is owner.subjective_notes_panel_scroll


def test_sync_placeholder_state_hides_analytics_and_predictions_for_placeholder_chart():
    owner = _owner()
    placeholder_chart = SimpleNamespace(is_placeholder=True)

    sync_chart_right_panel_placeholder_state(owner, placeholder_chart)

    assert owner.chart_analytics_panel_button.visible is False
    assert owner.chart_analytics_panel_button.enabled is False
    assert owner.predictions_panel_button.visible is False
    assert owner.predictions_panel_button.enabled is False
    assert owner._chart_right_panel_state.active_tab == "subjective_notes"


def test_schedule_render_for_active_tab_analytics():
    owner = _owner()
    owner._latest_chart = object()
    calls = []
    owner._schedule_chart_render = lambda chart, sections=None: calls.append(("analytics", chart, sections))
    owner._render_enneagram_predictions = lambda _chart: calls.append(("enneagram",))
    owner._render_dndification_predictions = lambda _chart: calls.append(("dnd",))
    owner._is_chart_analysis_section_visible = lambda _key: False
    owner._chart_right_panel_state.active_tab = "analytics"

    schedule_chart_render_for_active_right_panel(owner)

    assert calls == [("analytics", owner._latest_chart, None)]


def test_schedule_render_for_active_tab_predictions():
    owner = _owner()
    owner._latest_chart = object()
    calls = []
    owner._schedule_chart_render = lambda chart, sections=None: calls.append(("analytics", chart, sections))
    owner._render_enneagram_predictions = lambda _chart: calls.append(("enneagram",))
    owner._render_dndification_predictions = lambda _chart: calls.append(("dnd",))
    owner._is_chart_analysis_section_visible = lambda _key: False
    owner._chart_right_panel_state.active_tab = "predictions"

    schedule_chart_render_for_active_right_panel(owner)

    assert calls == [("enneagram",), ("dnd",)]


def test_schedule_render_for_active_tab_subjective_notes_when_anagrams_visible():
    owner = _owner()
    owner._latest_chart = object()
    calls = []
    owner._schedule_chart_render = lambda chart, sections=None: calls.append((chart, sections))
    owner._render_enneagram_predictions = lambda _chart: None
    owner._render_dndification_predictions = lambda _chart: None
    owner._is_chart_analysis_section_visible = lambda key: key == "anagrams"
    owner._chart_right_panel_state.active_tab = "subjective_notes"

    schedule_chart_render_for_active_right_panel(owner)

    assert calls == [(owner._latest_chart, {"anagrams"})]


from ephemeraldaddy.gui.features.controllers.chart_right_panel import (  # noqa: E402
    ChartRightPanelController,
)


def test_controller_methods_delegate_to_helper_functions():
    calls = []

    class _Owner:
        pass

    owner = _Owner()
    controller = ChartRightPanelController(owner)

    import ephemeraldaddy.gui.features.controllers.chart_right_panel as module

    original_set_visible = module.set_chart_right_panel_container_visible
    original_set_panel = module.set_chart_right_panel
    original_schedule = module.schedule_chart_render_for_active_right_panel
    original_sync = module.sync_chart_right_panel_placeholder_state
    try:
        module.set_chart_right_panel_container_visible = lambda o, visible: calls.append(("visible", o, visible))
        module.set_chart_right_panel = lambda o, key: calls.append(("panel", o, key))
        module.schedule_chart_render_for_active_right_panel = lambda o: calls.append(("schedule", o))
        module.sync_chart_right_panel_placeholder_state = lambda o, chart: calls.append(("sync", o, chart))

        chart = object()
        controller.set_container_visible(True)
        controller.set_active_panel("predictions")
        controller.schedule_render_for_active_panel()
        controller.sync_placeholder_state(chart)
    finally:
        module.set_chart_right_panel_container_visible = original_set_visible
        module.set_chart_right_panel = original_set_panel
        module.schedule_chart_render_for_active_right_panel = original_schedule
        module.sync_chart_right_panel_placeholder_state = original_sync

    assert calls == [
        ("visible", owner, True),
        ("panel", owner, "predictions"),
        ("schedule", owner),
        ("sync", owner, chart),
    ]


def test_set_chart_right_panel_invalid_key_defaults_to_analytics():
    owner = _owner()

    set_chart_right_panel(owner, "does_not_exist")

    assert owner._chart_right_panel_state.active_tab == "analytics"
    assert owner.chart_right_panel_stack.current is owner.chart_analytics_panel_scroll


def test_schedule_render_skips_when_no_latest_chart():
    owner = _owner()
    calls = []
    owner._schedule_chart_render = lambda chart, sections=None: calls.append(("analytics", chart, sections))
    owner._render_enneagram_predictions = lambda _chart: calls.append(("enneagram",))
    owner._render_dndification_predictions = lambda _chart: calls.append(("dnd",))
    owner._is_chart_analysis_section_visible = lambda _key: True
    owner._chart_right_panel_state.active_tab = "analytics"

    schedule_chart_render_for_active_right_panel(owner)

    assert calls == []


def test_schedule_render_for_subjective_notes_skips_when_anagrams_hidden():
    owner = _owner()
    owner._latest_chart = object()
    calls = []
    owner._schedule_chart_render = lambda chart, sections=None: calls.append((chart, sections))
    owner._render_enneagram_predictions = lambda _chart: None
    owner._render_dndification_predictions = lambda _chart: None
    owner._is_chart_analysis_section_visible = lambda _key: False
    owner._chart_right_panel_state.active_tab = "subjective_notes"

    schedule_chart_render_for_active_right_panel(owner)

    assert calls == []


def test_prepare_and_reveal_do_not_hide_visible_right_panel():
    from PySide6.QtWidgets import QWidget

    owner = _owner()
    owner.metrics_panel = QWidget()
    owner.metrics_panel.setVisible(True)
    owner._chart_right_panel_transition_active = True

    prepare_chart_right_panel_for_loading(owner)
    reveal_chart_right_panel_after_loading(owner)

    assert owner.metrics_panel.isVisible() is True
    assert owner._chart_right_panel_transition_active is False
