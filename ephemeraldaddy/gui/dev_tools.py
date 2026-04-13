from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from ephemeraldaddy.gui.style import similarity_gradient_rgb_for_range


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


class _RenameLabelDialog(QDialog):
    def __init__(self, *, parent: QWidget, title: str, old_label: str, max_length: int) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(360, 130)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Rename '{old_label}' to:"))

        self._line_edit = QLineEdit(self)
        self._line_edit.setMaxLength(max_length)
        self._line_edit.setPlaceholderText(f"Max {max_length} characters")
        self._line_edit.setText(old_label)
        self._line_edit.selectAll()
        layout.addWidget(self._line_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def value(self) -> str:
        return self._line_edit.text().strip()


class _MergeLabelsDialog(QDialog):
    def __init__(
        self,
        *,
        parent: QWidget,
        title: str,
        choices: list[tuple[str, int]],
        default_consolidate: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(420, 180)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Consolidate tag:"))
        self._consolidate_combo = QComboBox(self)
        for label, count in choices:
            self._consolidate_combo.addItem(f"{label} ({count})", label)
        layout.addWidget(self._consolidate_combo)

        layout.addWidget(QLabel("Into tag:"))
        self._into_combo = QComboBox(self)
        for label, count in choices:
            self._into_combo.addItem(f"{label} ({count})", label)
        layout.addWidget(self._into_combo)

        if default_consolidate:
            consolidate_index = self._consolidate_combo.findData(default_consolidate)
            if consolidate_index >= 0:
                self._consolidate_combo.setCurrentIndex(consolidate_index)
                into_index = 0 if consolidate_index != 0 else 1
                if 0 <= into_index < self._into_combo.count():
                    self._into_combo.setCurrentIndex(into_index)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str]:
        consolidate = str(self._consolidate_combo.currentData() or "").strip()
        into = str(self._into_combo.currentData() or "").strip()
        return consolidate, into


class ManageMetadataLabelsDialog(QDialog):
    FIELD_SENTIMENTS = "sentiments"
    FIELD_RELATIONSHIPS = "relationship_types"
    FIELD_TAGS = "tags"

    def __init__(
        self,
        *,
        parent: QWidget,
        load_usage,
        apply_change,
        label_limit: int,
        initial_field: str | None = None,
        lock_field: bool = False,
        window_title: str = "Manage sentiments & relationship types",
        intro_text: str = "Current + legacy labels found in database (including unused/orphaned).",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(window_title)
        self.resize(580, 520)
        self._load_usage = load_usage
        self._apply_change = apply_change
        self._label_limit = max(1, label_limit)
        self._usage_data: dict[str, list[dict[str, int | str]]] = {}

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(intro_text))

        self._field_selector = QComboBox(self)
        self._field_selector.addItem("Sentiments", self.FIELD_SENTIMENTS)
        self._field_selector.addItem("Relationship types", self.FIELD_RELATIONSHIPS)
        self._field_selector.addItem("Tags", self.FIELD_TAGS)
        self._field_selector.currentIndexChanged.connect(self._refresh_list)
        self._field_selector.setVisible(not lock_field)
        layout.addWidget(self._field_selector)

        self._list_widget = QListWidget(self)
        layout.addWidget(self._list_widget)

        if initial_field in {self.FIELD_SENTIMENTS, self.FIELD_RELATIONSHIPS, self.FIELD_TAGS}:
            index = self._field_selector.findData(initial_field)
            if index >= 0:
                self._field_selector.setCurrentIndex(index)

        button_row = QHBoxLayout()
        self._rename_button = QPushButton("Rename selected")
        self._rename_button.clicked.connect(self._rename_selected)
        self._delete_button = QPushButton("Delete selected")
        self._delete_button.clicked.connect(self._delete_selected)
        self._merge_button = QPushButton("Merge tags")
        self._merge_button.clicked.connect(self._merge_selected_tags)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._reload_usage)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)

        button_row.addWidget(self._rename_button)
        button_row.addWidget(self._delete_button)
        button_row.addWidget(self._merge_button)
        button_row.addStretch(1)
        button_row.addWidget(refresh_button)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        # Defer loading so the dialog can render immediately before DB work runs.
        QTimer.singleShot(0, self._reload_usage)

    def _active_field(self) -> str:
        value = self._field_selector.currentData()
        return str(value or self.FIELD_SENTIMENTS)

    def _active_rows(self) -> list[dict[str, int | str]]:
        return self._usage_data.get(self._active_field(), [])

    def _sync_action_buttons(self) -> None:
        if not hasattr(self, "_merge_button"):
            return
        is_tags = self._active_field() == self.FIELD_TAGS
        self._merge_button.setVisible(is_tags)
        self._merge_button.setEnabled(is_tags and len(self._active_rows()) >= 2)

    def _reload_usage(self) -> None:
        try:
            self._usage_data = self._load_usage()
        except Exception as exc:
            QMessageBox.critical(self, "Manage metadata", f"Could not load labels:\n{exc}")
            self._usage_data = {
                self.FIELD_SENTIMENTS: [],
                self.FIELD_RELATIONSHIPS: [],
                self.FIELD_TAGS: [],
            }
        self._refresh_list()

    def _refresh_list(self) -> None:
        rows = self._active_rows()
        self._list_widget.clear()
        minimum_count = 0
        maximum_count = 0
        if self._active_field() == self.FIELD_TAGS and rows:
            counts = [int(row.get("count", 0) or 0) for row in rows]
            minimum_count = min(counts)
            maximum_count = max(counts)
        for row in rows:
            label = str(row.get("label", "")).strip()
            count = int(row.get("count", 0) or 0)
            item = QListWidgetItem(f"{label}  ({count} charts)")
            item.setData(Qt.UserRole, label)
            if self._active_field() == self.FIELD_TAGS:
                red, green, blue = similarity_gradient_rgb_for_range(
                    count,
                    minimum_count,
                    maximum_count,
                )
                item.setForeground(QColor(red, green, blue))
            self._list_widget.addItem(item)
        self._sync_action_buttons()

    def _selected_label(self) -> str:
        item = self._list_widget.currentItem()
        if item is None:
            return ""
        return str(item.data(Qt.UserRole) or "").strip()

    def _rename_selected(self) -> None:
        old_label = self._selected_label()
        if not old_label:
            QMessageBox.information(self, "Manage metadata", "Select a label to rename.")
            return

        editor = _RenameLabelDialog(
            parent=self,
            title="Rename label",
            old_label=old_label,
            max_length=self._label_limit,
        )
        if editor.exec() != QDialog.Accepted:
            return

        new_label = editor.value()
        if not new_label:
            QMessageBox.warning(self, "Manage metadata", "New label cannot be empty.")
            return
        if new_label == old_label:
            return

        summary = self._apply_change(
            field=self._active_field(),
            old_label=old_label,
            new_label=new_label,
        )
        QMessageBox.information(
            self,
            "Rename complete",
            f"Updated {summary.get('occurrences_updated', 0)} occurrences across "
            f"{summary.get('rows_updated', 0)} chart(s).",
        )
        self._reload_usage()

    def _delete_selected(self) -> None:
        old_label = self._selected_label()
        if not old_label:
            QMessageBox.information(self, "Manage metadata", "Select a label to delete.")
            return
        confirm = QMessageBox.question(
            self,
            "Delete label",
            f"Delete '{old_label}' from all charts?\n\nThis cannot be undone except by restoring a backup.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        summary = self._apply_change(
            field=self._active_field(),
            old_label=old_label,
            new_label="",
        )
        QMessageBox.information(
            self,
            "Delete complete",
            f"Removed {summary.get('occurrences_updated', 0)} occurrences across "
            f"{summary.get('rows_updated', 0)} chart(s).",
        )
        self._reload_usage()

    def _merge_selected_tags(self) -> None:
        if self._active_field() != self.FIELD_TAGS:
            return

        rows = self._active_rows()
        choices: list[tuple[str, int]] = []
        for row in rows:
            label = str(row.get("label", "")).strip()
            if not label:
                continue
            count = int(row.get("count", 0) or 0)
            choices.append((label, count))
        if len(choices) < 2:
            QMessageBox.information(
                self,
                "Merge tags",
                "Need at least two tags to merge.",
            )
            return

        picker = _MergeLabelsDialog(
            parent=self,
            title="Merge tags",
            choices=choices,
            default_consolidate=self._selected_label(),
        )
        if picker.exec() != QDialog.Accepted:
            return

        consolidate_label, into_label = picker.values()
        if not consolidate_label or not into_label:
            QMessageBox.warning(self, "Merge tags", "Select both tags before merging.")
            return
        if consolidate_label == into_label:
            QMessageBox.warning(self, "Merge tags", "Consolidate and Into tags must be different.")
            return

        summary = self._apply_change(
            field=self.FIELD_TAGS,
            old_label=consolidate_label,
            new_label=into_label,
        )
        QMessageBox.information(
            self,
            "Merge complete",
            f"Merged '{consolidate_label}' into '{into_label}'.\n\n"
            f"Updated {summary.get('occurrences_updated', 0)} occurrences across "
            f"{summary.get('rows_updated', 0)} chart(s).",
        )
        self._reload_usage()
