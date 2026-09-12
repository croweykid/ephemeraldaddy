"""Appwide handling for the platform-standard close-window shortcut."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication


class GlobalCloseShortcutFilter(QObject):
    """Close the active modal or top-level window for Ctrl/Cmd+W."""

    def eventFilter(self, _obj: QObject, event: QEvent) -> bool:
        if event.type() != QEvent.KeyPress:
            return False
        if not event.matches(QKeySequence.Close):
            return False

        target = QApplication.activeModalWidget() or QApplication.activeWindow()
        if target is None:
            return False

        target.close()
        return True
