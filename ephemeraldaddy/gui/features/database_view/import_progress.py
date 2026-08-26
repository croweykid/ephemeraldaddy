"""Subtle footer progress presentation for Database View imports."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QLabel, QWidget


class DatabaseImportProgressLabel(QLabel):
    """Selection footer whose background doubles as an import progress bar."""

    _PROGRESS_COLOR = QColor("#343434")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._progress_fraction: float | None = None

    def set_import_progress(
        self,
        task_name: str,
        verb: str,
        items: str,
        current: int,
        total: int,
    ) -> None:
        safe_total = max(0, int(total))
        safe_current = max(0, min(int(current), safe_total)) if safe_total else 0
        self._progress_fraction = safe_current / safe_total if safe_total else 0.0
        self.setToolTip(
            f"{task_name}: {verb} {items} {safe_current} / {safe_total}"
        )
        self.update()

    def clear_import_progress(self) -> None:
        self._progress_fraction = None
        self.setToolTip("")
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        if self._progress_fraction is not None:
            painter = QPainter(self)
            progress_width = round(self.width() * self._progress_fraction)
            painter.fillRect(0, 0, progress_width, self.height(), self._PROGRESS_COLOR)
            painter.end()
        super().paintEvent(event)

