from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace


class _QObject:
    def __init__(self, *_args, **_kwargs) -> None:
        pass


class _QEvent:
    KeyPress = 1
    MouseButtonPress = 2


class _QKeySequence:
    Close = object()


qt_core = ModuleType("PySide6.QtCore")
qt_core.QEvent = _QEvent
qt_core.QObject = _QObject
qt_gui = ModuleType("PySide6.QtGui")
qt_gui.QKeySequence = _QKeySequence
qt_widgets = ModuleType("PySide6.QtWidgets")
qt_widgets.QApplication = object
pyside = ModuleType("PySide6")
pyside.QtCore = qt_core
pyside.QtGui = qt_gui
pyside.QtWidgets = qt_widgets
sys.modules["PySide6"] = pyside
sys.modules["PySide6.QtCore"] = qt_core
sys.modules["PySide6.QtGui"] = qt_gui
sys.modules["PySide6.QtWidgets"] = qt_widgets

from ephemeraldaddy.gui.features.windowing import global_close_shortcut
from ephemeraldaddy.gui.features.windowing.global_close_shortcut import (
    GlobalCloseShortcutFilter,
)


class _Event:
    def __init__(self, event_type: int, *, matches_close: bool = False) -> None:
        self._event_type = event_type
        self._matches_close = matches_close

    def type(self) -> int:
        return self._event_type

    def matches(self, _sequence: object) -> bool:
        return self._matches_close


class _Window:
    def __init__(self) -> None:
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


def _patch_active_windows(monkeypatch, *, modal=None, active=None) -> None:
    application = SimpleNamespace(
        activeModalWidget=lambda: modal,
        activeWindow=lambda: active,
    )
    monkeypatch.setattr(global_close_shortcut, "QApplication", application)


def test_close_shortcut_prefers_active_modal_window(monkeypatch):
    modal = _Window()
    active = _Window()
    _patch_active_windows(monkeypatch, modal=modal, active=active)

    handled = GlobalCloseShortcutFilter().eventFilter(
        None, _Event(_QEvent.KeyPress, matches_close=True)
    )

    assert handled is True
    assert modal.close_calls == 1
    assert active.close_calls == 0


def test_close_shortcut_closes_active_window_without_modal(monkeypatch):
    active = _Window()
    _patch_active_windows(monkeypatch, active=active)

    handled = GlobalCloseShortcutFilter().eventFilter(
        None, _Event(_QEvent.KeyPress, matches_close=True)
    )

    assert handled is True
    assert active.close_calls == 1


def test_close_shortcut_is_unhandled_without_a_target(monkeypatch):
    _patch_active_windows(monkeypatch)

    handled = GlobalCloseShortcutFilter().eventFilter(
        None, _Event(_QEvent.KeyPress, matches_close=True)
    )

    assert handled is False


def test_non_close_events_are_unhandled_without_window_lookup(monkeypatch):
    def unexpected_lookup():
        raise AssertionError("inactive events must not inspect window state")

    monkeypatch.setattr(
        global_close_shortcut,
        "QApplication",
        SimpleNamespace(
            activeModalWidget=unexpected_lookup,
            activeWindow=unexpected_lookup,
        ),
    )
    event_filter = GlobalCloseShortcutFilter()

    assert event_filter.eventFilter(None, _Event(_QEvent.MouseButtonPress)) is False
    assert event_filter.eventFilter(
        None, _Event(_QEvent.KeyPress, matches_close=False)
    ) is False


def test_app_installs_windowing_owned_close_shortcut_filter():
    source = Path("ephemeraldaddy/gui/app.py").read_text()

    assert "class _GlobalCloseShortcutFilter" not in source
    assert (
        "from ephemeraldaddy.gui.features.windowing import GlobalCloseShortcutFilter"
        in source
    )
    assert "GlobalCloseShortcutFilter(app)" in source
