from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class SizeCheckerPopup(QDialog):
    """Non-modal developer popup that reports current window/panel dimensions."""

    def __init__(
        self,
        parent_window: QWidget,
        splitter: QSplitter,
        panel_labels: tuple[str, str, str] = ("Left", "Middle", "Right"),
        title: str = "Size Checker",
    ) -> None:
        super().__init__(None)
        self._parent_window: QWidget | None = None
        self._splitter: QSplitter | None = None
        self._panel_labels = panel_labels

        self.setWindowTitle(title)
        self.setModal(False)
        self.setWindowFlag(Qt.Window, True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)

        self._copy_button = QPushButton(self)
        self._copy_button.setToolTip("Copy size readout")
        self._copy_button.setCursor(Qt.PointingHandCursor)
        self._copy_button.clicked.connect(self._copy_readout)

        copy_icon_path = Path(__file__).resolve().parents[1] / "graphics" / "copy_icon.png"
        if copy_icon_path.exists():
            self._copy_button.setIcon(QIcon(str(copy_icon_path)))
            self._copy_button.setText("")
        else:
            self._copy_button.setText("Copy")

        self._readout = QTextEdit(self)
        self._readout.setReadOnly(True)
        self._readout.setStyleSheet(
            "QTextEdit {"
            "background-color: rgba(20, 20, 20, 0.9);"
            "color: #f5f5f5;"
            "padding: 8px;"
            "border: 1px solid #777777;"
            "font-family: 'Courier New', monospace;"
            "font-size: 11px;"
            "}"
        )

        header_layout = QHBoxLayout()
        header_layout.addStretch(1)
        header_layout.addWidget(self._copy_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(header_layout)
        layout.addWidget(self._readout)

        self.resize(360, 170)

        self.set_target(
            parent_window=parent_window,
            splitter=splitter,
            panel_labels=panel_labels,
            title=title,
        )

    def set_target(
        self,
        parent_window: QWidget,
        splitter: QSplitter,
        panel_labels: tuple[str, str, str] | None = None,
        title: str | None = None,
    ) -> None:
        if self._parent_window is not None:
            self._parent_window.removeEventFilter(self)
        if self._splitter is not None:
            try:
                self._splitter.splitterMoved.disconnect(self.refresh)
            except (RuntimeError, TypeError):
                pass
            self._splitter.removeEventFilter(self)

        self._parent_window = parent_window
        self._splitter = splitter
        if panel_labels is not None:
            self._panel_labels = panel_labels
        if title is not None:
            self.setWindowTitle(title)

        self._parent_window.installEventFilter(self)
        self._splitter.installEventFilter(self)
        self._splitter.splitterMoved.connect(self.refresh)

        self.refresh()

    def closeEvent(self, event) -> None:
        if self._splitter is not None:
            try:
                self._splitter.splitterMoved.disconnect(self.refresh)
            except (RuntimeError, TypeError):
                pass
            self._splitter.removeEventFilter(self)
        if self._parent_window is not None:
            self._parent_window.removeEventFilter(self)
        self._splitter = None
        self._parent_window = None
        super().closeEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if event.type() in (QEvent.Resize, QEvent.Move, QEvent.Show):
            self.refresh()
        return super().eventFilter(watched, event)

    def refresh(self) -> None:
        if self._parent_window is None or self._splitter is None:
            return
        splitter_sizes = self._splitter.sizes()
        if len(splitter_sizes) < 3:
            return

        total = sum(max(0, value) for value in splitter_sizes)
        if total <= 0:
            ratios = (0.0, 0.0, 0.0)
        else:
            ratios = tuple((size / total) for size in splitter_sizes[:3])

        window_size = self._parent_window.size()
        lines = [
            f"Window: {window_size.width()}w × {window_size.height()}h",
            f"{self._panel_labels[0]} panel: {splitter_sizes[0]}w",
            f"{self._panel_labels[1]} panel: {splitter_sizes[1]}w",
            f"{self._panel_labels[2]} panel: {splitter_sizes[2]}w",
            "Ratio (L:M:R): "
            f"{ratios[0]:.3f} : {ratios[1]:.3f} : {ratios[2]:.3f}",
        ]
        self._readout.setPlainText("\n".join(lines))

        anchor = self._parent_window.mapToGlobal(QPoint(0, self._parent_window.height()))
        self.move(anchor.x() + 14, anchor.y() - self.height() - 14)

    def _copy_readout(self) -> None:
        QApplication.clipboard().setText(self._readout.toPlainText())
