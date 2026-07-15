"""Shared widgets for settings and preferences UI."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLabel, QLayout, QSizePolicy, QWidget

_SETTINGS_HELP_LABEL_EXTRA_VERTICAL_PADDING = 4
_SETTINGS_HELP_LABEL_TEXT_MARGIN = 4
_QWIDGETSIZE_MAX = 16777215


class SettingsHeaderFlowLayout(QLayout):
    """A compact flow layout that wraps Settings header buttons into rows."""

    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = 8) -> None:
        super().__init__(parent)
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def __del__(self) -> None:
        while self._items:
            self.takeAt(0)

    def addItem(self, item) -> None:  # noqa: ANN001 - Qt override signature
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):  # noqa: ANN001 - Qt override signature
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):  # noqa: ANN001 - Qt override signature
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, *, test_only: bool) -> int:
        margins = self.contentsMargins()
        effective_rect = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0
        spacing = self.spacing()
        for item in self._items:
            widget = item.widget()
            if widget is not None and not widget.isVisible():
                continue
            item_size = item.sizeHint()
            next_x = x + item_size.width() + spacing
            if x > effective_rect.x() and next_x - spacing > effective_rect.right() + 1:
                x = effective_rect.x()
                y += line_height + spacing
                next_x = x + item_size.width() + spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))
            x = next_x
            line_height = max(line_height, item_size.height())
        return y + line_height - rect.y() + margins.bottom()


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
