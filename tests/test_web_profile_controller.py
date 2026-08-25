from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets", exc_type=ImportError)

from ephemeraldaddy.gui.features.import_export import web_profile_controller as subject


class _Button:
    def __init__(self, label: str) -> None:
        self.label = label


class _MessageBox:
    selected_label = "Cancel import"
    instance = None

    class Icon:
        Information = object()

    class ButtonRole:
        RejectRole = object()
        AcceptRole = object()

    def __init__(self, parent) -> None:
        self.parent = parent
        self.buttons = []
        self.default_button = None
        self.escape_button = None
        self.text = ""
        type(self).instance = self

    def setIcon(self, _icon) -> None:
        pass

    def setWindowTitle(self, _title: str) -> None:
        pass

    def setText(self, text: str) -> None:
        self.text = text

    def addButton(self, label: str, role) -> _Button:
        button = _Button(label)
        self.buttons.append((button, role))
        return button

    def setDefaultButton(self, button: _Button) -> None:
        self.default_button = button

    def setEscapeButton(self, button: _Button) -> None:
        self.escape_button = button

    def exec(self) -> None:
        pass

    def clickedButton(self) -> _Button:
        return next(button for button, _role in self.buttons if button.label == self.selected_label)


def test_missing_birthplace_defaults_to_cancel(monkeypatch):
    monkeypatch.setattr(subject, "QMessageBox", _MessageBox)

    assert subject.confirm_manual_wikipedia_import(None, "Example Person") is False

    prompt = _MessageBox.instance
    assert [button.label for button, _role in prompt.buttons] == [
        "Cancel import",
        "Finish manually",
    ]
    assert prompt.default_button.label == "Cancel import"
    assert prompt.escape_button.label == "Cancel import"
    assert "no birth place info is available" in prompt.text


def test_missing_birthplace_can_continue_manually(monkeypatch):
    monkeypatch.setattr(subject, "QMessageBox", _MessageBox)
    _MessageBox.selected_label = "Finish manually"

    try:
        assert subject.confirm_manual_wikipedia_import(None, "Example Person") is True
    finally:
        _MessageBox.selected_label = "Cancel import"
