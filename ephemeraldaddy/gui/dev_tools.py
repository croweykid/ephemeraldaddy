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
from ephemeraldaddy.gui.style import (
    INACTIVE_ACTION_BUTTON_STYLE,
    similarity_gradient_rgb_for_range,
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
        self._usage_data: dict[str, list[dict[str, int | str | list[str]]]] = {}

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(intro_text))

        self._field_selector = QComboBox(self)
        self._field_selector.addItem("Sentiments", self.FIELD_SENTIMENTS)
        self._field_selector.addItem("Relationship types", self.FIELD_RELATIONSHIPS)
        self._field_selector.addItem("Tags", self.FIELD_TAGS)
        self._field_selector.currentIndexChanged.connect(self._refresh_list)
        self._field_selector.setVisible(not lock_field)
        layout.addWidget(self._field_selector)

        content_row = QHBoxLayout()

        self._list_widget = QListWidget(self)
        self._list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self._list_widget.itemSelectionChanged.connect(self._sync_action_buttons)
        self._list_widget.currentItemChanged.connect(
            lambda _current, _previous: self._refresh_assigned_charts_panel()
        )
        content_row.addWidget(self._list_widget, 1)

        right_panel = QVBoxLayout()
        self._assigned_header_label = QLabel("Charts with selected property")
        right_panel.addWidget(self._assigned_header_label)
        self._assigned_charts_list = QListWidget(self)
        self._assigned_charts_list.setSelectionMode(QListWidget.NoSelection)
        right_panel.addWidget(self._assigned_charts_list, 1)
        content_row.addLayout(right_panel, 1)
        layout.addLayout(content_row)

        if initial_field in {self.FIELD_SENTIMENTS, self.FIELD_RELATIONSHIPS, self.FIELD_TAGS}:
            index = self._field_selector.findData(initial_field)
            if index >= 0:
                self._field_selector.setCurrentIndex(index)

        button_row = QHBoxLayout()
        self._rename_button = QPushButton("Rename")
        self._rename_button.clicked.connect(self._rename_selected)
        self._delete_button = QPushButton("❌Delete")
        self._delete_button.clicked.connect(self._delete_selected)
        self._merge_button = QPushButton("Merge tags")
        self._merge_button.clicked.connect(self._merge_selected_tags)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)

        button_row.addWidget(self._rename_button)
        button_row.addWidget(self._delete_button)
        button_row.addWidget(self._merge_button)
        button_row.addStretch(1)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        # Defer loading so the dialog can render immediately before DB work runs.
        QTimer.singleShot(0, self._reload_usage)

    def _active_field(self) -> str:
        value = self._field_selector.currentData()
        return str(value or self.FIELD_SENTIMENTS)

    def _active_rows(self) -> list[dict[str, int | str | list[str]]]:
        return self._usage_data.get(self._active_field(), [])

    def _sync_action_buttons(self) -> None:
        if not hasattr(self, "_rename_button") or not hasattr(self, "_delete_button"):
            return
        selected_count = len(self._selected_labels())
        rename_enabled = selected_count == 1
        delete_enabled = selected_count >= 1
        self._rename_button.setEnabled(rename_enabled)
        self._delete_button.setEnabled(delete_enabled)
        self._rename_button.setStyleSheet("" if rename_enabled else INACTIVE_ACTION_BUTTON_STYLE)
        self._delete_button.setStyleSheet("" if delete_enabled else INACTIVE_ACTION_BUTTON_STYLE)

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
        minimum_count = min((int(row.get("count", 0) or 0) for row in rows), default=0)
        maximum_count = max((int(row.get("count", 0) or 0) for row in rows), default=0)
        for row in rows:
            label = str(row.get("label", "")).strip()
            count = int(row.get("count", 0) or 0)
            item = QListWidgetItem(f"{label}  ({count} charts)")
            item.setData(Qt.UserRole, label)
            item.setData(Qt.UserRole + 1, list(row.get("chart_names", []) or []))
            red, green, blue = similarity_gradient_rgb_for_range(
                count,
                minimum_count,
                maximum_count,
            )
            item.setForeground(QColor(red, green, blue))
            self._list_widget.addItem(item)
        self._sync_action_buttons()
        self._refresh_assigned_charts_panel()

    def _selected_label(self) -> str:
        labels = self._selected_labels()
        return labels[0] if labels else ""

    def _selected_labels(self) -> list[str]:
        labels: list[str] = []
        for item in self._list_widget.selectedItems():
            label = str(item.data(Qt.UserRole) or "").strip()
            if label:
                labels.append(label)
        return labels

    def _refresh_assigned_charts_panel(self) -> None:
        if not hasattr(self, "_assigned_charts_list"):
            return
        self._assigned_charts_list.clear()

        item = self._list_widget.currentItem()
        if item is None:
            selected_items = self._list_widget.selectedItems()
            item = selected_items[0] if selected_items else None
        if item is None:
            self._assigned_header_label.setText("Charts with selected property")
            return

        label = str(item.data(Qt.UserRole) or "").strip()
        chart_names = list(item.data(Qt.UserRole + 1) or [])
        self._assigned_header_label.setText(
            f"Charts with '{label}' ({len(chart_names)})"
        )
        for chart_name in chart_names:
            self._assigned_charts_list.addItem(str(chart_name))

    def _delete_selected(self) -> None:
        old_labels = self._selected_labels()
        if not old_labels:
            QMessageBox.information(self, "Manage metadata", "Select one or more labels to delete.")
            return
        if len(old_labels) == 1:
            confirm_message = (
                f"Delete '{old_labels[0]}' from all charts?\n\n"
                "This cannot be undone except by restoring a backup."
            )
            confirm_title = "Delete label"
        else:
            preview = ", ".join(old_labels[:6])
            if len(old_labels) > 6:
                preview += f", +{len(old_labels) - 6} more"
            confirm_message = (
                f"Delete {len(old_labels)} labels from all charts?\n\n"
                f"{preview}\n\n"
                "This cannot be undone except by restoring a backup."
            )
            confirm_title = "Delete labels"
        confirm = QMessageBox.question(
            self,
            confirm_title,
            confirm_message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        total_occurrences = 0
        total_rows = 0
        for index, old_label in enumerate(old_labels):
            summary = self._apply_change(
                field=self._active_field(),
                old_label=old_label,
                new_label="",
                create_backup=index == 0,
            )
            total_occurrences += int(summary.get("occurrences_updated", 0) or 0)
            total_rows += int(summary.get("rows_updated", 0) or 0)

        QMessageBox.information(
            self,
            "Delete complete",
            f"Removed {total_occurrences} occurrences across {total_rows} chart updates.",
        )
        self._reload_usage()

    def _rename_selected(self) -> None:
        item = self._list_widget.currentItem()
        old_label = str(item.data(Qt.UserRole) or "").strip() if item is not None else self._selected_label()
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
