"""Reusable signed score slider with an emoji marker."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QSlider, QStyle, QStyleOptionSlider, QWidget


class SignedEmojiSlider(QSlider):
    """Horizontal -10…10 slider with an emoji marker tracking score thresholds."""

    userActivated = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Horizontal, parent)
        self.setRange(-10, 10)
        self.setSingleStep(1)
        self.setPageStep(1)
        self.setTickInterval(5)
        self.setValue(0)
        self.setMinimumHeight(34)
        self.setStyleSheet(
            "QSlider::groove:horizontal {"
            "height: 12px;"
            "border-radius: 6px;"
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            "stop:0 #c62828, stop:0.5 #7f7f7f, stop:1 #1565c0);"
            "}"
            "QSlider::handle:horizontal {"
            "background: transparent;"
            "border: none;"
            "width: 20px;"
            "margin: -8px 0px;"
            "}"
        )
        self._emoji_marker = QLabel(self)
        self._emoji_marker.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._emoji_marker.setAlignment(Qt.AlignCenter)
        self._emoji_marker.setFixedSize(24, 24)
        self._refresh_emoji()
        self.valueChanged.connect(self._refresh_emoji)

    @staticmethod
    def _emoji_for_value(value: int) -> str:
        if value <= -10:
            return "😈"
        if value <= -5:
            return "😠"
        if value < 5:
            return "⚖️"
        if value < 10:
            return "🙂"
        return "😇"

    def _refresh_emoji(self) -> None:
        self._emoji_marker.setText(self._emoji_for_value(self.value()))
        self._position_emoji_marker()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_emoji_marker()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.userActivated.emit(self.value())

    def keyPressEvent(self, event) -> None:
        super().keyPressEvent(event)
        if event.key() in {Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space}:
            self.userActivated.emit(self.value())

    def _position_emoji_marker(self) -> None:
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        handle_rect = self.style().subControlRect(
            QStyle.CC_Slider,
            option,
            QStyle.SC_SliderHandle,
            self,
        )
        x = handle_rect.center().x() - (self._emoji_marker.width() // 2)
        y = handle_rect.center().y() - (self._emoji_marker.height() // 2)
        self._emoji_marker.move(x, y)


# Compatibility name while existing callers migrate to the generic widget name.
AlignmentEmojiSlider = SignedEmojiSlider
