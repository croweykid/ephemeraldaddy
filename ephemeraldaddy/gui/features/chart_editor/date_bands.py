"""Normalized optional date/time inputs and proportional timeline bands."""

from __future__ import annotations

import datetime as dt

from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QIntValidator,
    QLinearGradient,
    QPainter,
    QRegularExpressionValidator,
)
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget


from ephemeraldaddy.gui.features.chart_editor.date_band_values import (
    UNKNOWN_PORTION,
    date_band_geometry,
    normalized_optional_datetime,
    parse_optional_datetime,
)


class OptionalDateTimeInput(QWidget):
    """Blank-capable normalized ``DD MM YYYY`` and 24-hour ``TT:TT`` fields."""

    valueChanged = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.day_edit = self._part("DD", 2, QIntValidator(1, 31, self))
        self.month_edit = self._part("MM", 2, QIntValidator(1, 12, self))
        self.year_edit = self._part("YYYY", 4, QIntValidator(1, 9999, self))
        self.time_edit = self._part("TT:TT", 5, None)
        self.time_edit.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]"), self
            )
        )
        for index, edit in enumerate(
            (self.day_edit, self.month_edit, self.year_edit, self.time_edit)
        ):
            if index:
                layout.addWidget(QLabel("/" if index < 3 else "  "))
            layout.addWidget(edit)

    def _part(self, placeholder: str, length: int, validator: QIntValidator | None) -> QLineEdit:
        edit = QLineEdit(self)
        edit.setPlaceholderText(placeholder)
        edit.setAccessibleName(placeholder)
        edit.setMaxLength(length)
        edit.setFixedWidth(52 if length > 2 else 34)
        if validator is not None:
            edit.setValidator(validator)
        edit.textChanged.connect(self.valueChanged)
        return edit

    def value(self) -> dt.datetime | None:
        return parse_optional_datetime(
            self.day_edit.text(),
            self.month_edit.text(),
            self.year_edit.text(),
            self.time_edit.text(),
        )

    def normalized_value(self) -> str:
        return normalized_optional_datetime(self.value())

    def setValue(self, value: dt.datetime | None) -> None:  # noqa: N802 - Qt API style
        parts = ("", "", "", "") if value is None else (
            value.strftime("%d"), value.strftime("%m"), value.strftime("%Y"), value.strftime("%H:%M")
        )
        for edit, text in zip(
            (self.day_edit, self.month_edit, self.year_edit, self.time_edit), parts, strict=True
        ):
            edit.setText(text)


class ProportionalDateBand(QWidget):
    """Paint a proportional beginning/peak/end band with faded unknown regions."""

    def __init__(self, color: QColor | str = "#6fa8dc", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self._geometry = date_band_geometry(None, None, None)
        self.setMinimumHeight(12)

    def setDates(  # noqa: N802 - Qt API style
        self,
        beginning: dt.datetime | None,
        peak: dt.datetime | None,
        end: dt.datetime | None,
    ) -> None:
        self._geometry = date_band_geometry(beginning, peak, end)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API style
        del event
        rect = self.rect().adjusted(0, 2, -1, -2)
        if rect.width() <= 0:
            return
        gradient = QLinearGradient(rect.topLeft(), rect.topRight())
        opaque = QColor(self._color)
        transparent = QColor(self._color)
        transparent.setAlpha(0)
        stops: list[tuple[float, QColor]] = [(0.0, opaque), (1.0, opaque)]
        if self._geometry.beginning_unknown:
            stops.extend(((0.0, transparent), (UNKNOWN_PORTION, opaque)))
        if self._geometry.end_unknown:
            stops.extend(((1.0 - UNKNOWN_PORTION, opaque), (1.0, transparent)))
        if self._geometry.peak_unknown:
            half = UNKNOWN_PORTION / 2.0
            stops.extend(((0.5 - half, opaque), (0.5, transparent), (0.5 + half, opaque)))
        for position, color in sorted(stops, key=lambda item: item[0]):
            gradient.setColorAt(position, color)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
