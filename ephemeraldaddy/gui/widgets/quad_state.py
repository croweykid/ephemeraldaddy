"""Reusable tri-state and quad-state filter widgets."""

from __future__ import annotations

from typing import Mapping

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QToolButton, QWidget

from ephemeraldaddy.gui.style import QUAD_STATE_SLIDER_VISUALS


class TriStateCheckBox(QCheckBox):
    def __init__(self, label: str) -> None:
        super().__init__(label)
        self.setTristate(True)

    def nextCheckState(self) -> None:
        current_state = self.checkState()
        if current_state == Qt.Unchecked:
            self.setCheckState(Qt.Checked)
        elif current_state == Qt.Checked:
            self.setCheckState(Qt.PartiallyChecked)
        else:
            self.setCheckState(Qt.Unchecked)


class _QuadStateIndicatorButton(QToolButton):
    """Small manually-painted button for Database View quad-state filters.

    Some Qt/platform combinations can leave the previous QToolButton text glyph
    in the backing store after a style-sheet/text transition (most visibly the
    red exclusion X). Painting the indicator ourselves clears the full button
    rectangle on every state change before drawing the current glyph.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._quad_state_text = ""
        self._quad_state_background = "#111111"
        self._quad_state_foreground = "#dddddd"
        self._quad_state_border = "#444444"

    def setQuadStateVisual(self, visual: Mapping[str, object]) -> None:
        self._quad_state_text = str(visual.get("text") or "")
        self._quad_state_background = str(visual.get("background") or "#111111")
        self._quad_state_foreground = str(visual.get("foreground") or "#dddddd")
        self._quad_state_border = str(visual.get("border") or "#444444")
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), self.palette().window())
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(QColor(self._quad_state_background))
        painter.setPen(QPen(QColor(self._quad_state_border), 1))
        painter.drawRoundedRect(rect, 10, 10)
        if self._quad_state_text:
            painter.setPen(QColor(self._quad_state_foreground))
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, self._quad_state_text)


class QuadStateSlider(QWidget):
    modeChanged = Signal(int)

    MODE_EMPTY = 0
    MODE_TRUE = 1
    MODE_FALSE = 2
    MODE_MIXED = 3

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mode = self.MODE_EMPTY
        self._button = _QuadStateIndicatorButton(self)
        self._button.setCheckable(False)
        self._button.clicked.connect(self._advance_mode)
        self._label = QLabel(label)
        self._label.setStyleSheet("padding-left: 2px;")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._button)
        layout.addWidget(self._label)
        layout.addStretch(1)
        self.setLayout(layout)
        self._render_mode()

    def setLabelColor(self, color_hex: str | None) -> None:
        label_style = "padding-left: 2px;"
        color_value = str(color_hex or "").strip()
        if color_value:
            label_style += f" color: {color_value};"
        self._label.setStyleSheet(label_style)

    def mode(self) -> int:
        return self._mode

    def setMode(self, mode: int, emit_signal: bool = False) -> None:
        mode = int(mode)
        if mode == self._mode:
            return
        self._mode = mode
        self._render_mode()
        if emit_signal:
            self.modeChanged.emit(self._mode)

    def _advance_mode(self) -> None:
        if self._mode in (self.MODE_EMPTY, self.MODE_MIXED):
            next_mode = self.MODE_TRUE
        elif self._mode == self.MODE_TRUE:
            next_mode = self.MODE_FALSE
        else:
            next_mode = self.MODE_EMPTY
        self.setMode(next_mode, emit_signal=True)

    def _render_mode(self) -> None:
        if self._mode == self.MODE_TRUE:
            visual = QUAD_STATE_SLIDER_VISUALS["true"]
        elif self._mode == self.MODE_FALSE:
            visual = QUAD_STATE_SLIDER_VISUALS["false"]
        elif self._mode == self.MODE_MIXED:
            visual = QUAD_STATE_SLIDER_VISUALS["mixed"]
        else:
            visual = QUAD_STATE_SLIDER_VISUALS["empty"]

        # Keep the native button text empty and paint the indicator manually.
        # This avoids stale foreground glyphs from previous states (especially
        # the red exclusion X) being retained by QToolButton backing-store/style
        # transitions after the red background has already been cleared.
        self._button.setText("")
        self._button.setToolTip(str(visual["tooltip"]))
        self._button.setFixedWidth(28)
        self._button.setQuadStateVisual(visual)
