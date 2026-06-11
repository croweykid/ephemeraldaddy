"""Shared widgets for settings and preferences UI."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QLabel, QSizePolicy

_SETTINGS_HELP_LABEL_EXTRA_VERTICAL_PADDING = 4
_SETTINGS_HELP_LABEL_TEXT_MARGIN = 4
_QWIDGETSIZE_MAX = 16777215


class SettingsHelpLabel(QLabel):
    """A word-wrapped label whose height follows its rendered text.

    Qt's default QLabel size hint can be too compact for wrapped text in hidden
    or recently expanded layouts.  This label computes height-for-width from the
    current font metrics and keeps its minimum height updated on resize, so the
    containing settings section grows instead of clipping the first or last row
    of text.
    """

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(text, parent)
        configure_settings_help_label(self)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        contents_margins = self.contentsMargins()
        horizontal_margin = (
            (self.margin() * 2)
            + contents_margins.left()
            + contents_margins.right()
        )
        vertical_margin = (
            (self.margin() * 2)
            + contents_margins.top()
            + contents_margins.bottom()
        )
        available_width = max(1, int(width) - horizontal_margin)
        flags = int(self.alignment()) | int(Qt.TextWordWrap)
        text = self.text() or " "
        text_rect = self.fontMetrics().boundingRect(
            0,
            0,
            available_width,
            _QWIDGETSIZE_MAX,
            flags,
            text,
        )
        return max(
            self.fontMetrics().lineSpacing(),
            text_rect.height(),
        ) + vertical_margin + _SETTINGS_HELP_LABEL_EXTRA_VERTICAL_PADDING

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        width = self.width() if self.width() > 0 else hint.width()
        return QSize(hint.width(), max(hint.height(), self.heightForWidth(width)))

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        width = self.width() if self.width() > 0 else hint.width()
        return QSize(hint.width(), max(hint.height(), self.heightForWidth(width)))

    def resizeEvent(self, event) -> None:  # noqa: ANN001 - Qt override signature
        super().resizeEvent(event)
        self.refresh_dynamic_height()

    def refresh_dynamic_height(self) -> None:
        self.setMinimumHeight(self.heightForWidth(max(1, self.width())))
        self.updateGeometry()


def configure_settings_help_label(label: QLabel) -> None:
    """Configure settings/help text labels with dynamic wrapped sizing."""
    label.setWordWrap(True)
    label.setMinimumWidth(0)
    label.setMinimumHeight(0)
    label.setMaximumHeight(_QWIDGETSIZE_MAX)
    label.setMargin(max(label.margin(), _SETTINGS_HELP_LABEL_TEXT_MARGIN))
    label.setAlignment(label.alignment() | Qt.AlignTop)
    label_size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    label_size_policy.setHeightForWidth(True)
    label.setSizePolicy(label_size_policy)
    if isinstance(label, SettingsHelpLabel):
        label.refresh_dynamic_height()
    else:
        label.updateGeometry()
