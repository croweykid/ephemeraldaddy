"""Widgets and dialogs for the Database View Collection Manager panel.

This module owns collection-panel-only UI behavior so ``app.py`` can remain a
thin coordinator while Database View collection interactions move toward the
workflow package requested by the app refactor manifesto.
"""

from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCompleter,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.gui.features.charts.collections import (
    DEFAULT_COLLECTION_IDS,
    normalize_collection_id,
)

CHART_UIDS_MIME_TYPE = "application/x-ephemeraldaddy-chart-uids"


def chart_drag_mime_data(mime_data, items: list[QListWidgetItem]):
    """Add UID-first Database View chart identity to a Qt drag payload."""

    chart_uids: list[str] = []
    for item in items:
        chart_uid = str(item.data(Qt.UserRole + 2) or item.data(Qt.UserRole) or "").strip().upper()
        if chart_uid:
            chart_uids.append(chart_uid)
    if chart_uids:
        mime_data.setData(CHART_UIDS_MIME_TYPE, "\n".join(chart_uids).encode("utf-8"))
    return mime_data


def show_collection_confirmation(parent: QWidget, message: str) -> None:
    """Show the collection action acknowledgement requested for membership edits."""

    prompt = QMessageBox(parent)
    prompt.setWindowTitle("Collections")
    prompt.setIcon(QMessageBox.Information)
    prompt.setText(message)
    cool_button = prompt.addButton("cool", QMessageBox.AcceptRole)
    prompt.setDefaultButton(cool_button)
    prompt.exec()


class CollectionsListWidget(QListWidget):
    """Collection list that accepts Database View chart UID drags."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.drop_chart_uids_on_collection: Callable[[str, list[str]], None] | None = None
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(CHART_UIDS_MIME_TYPE):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        item = self.itemAt(event.position().toPoint())
        collection_id = self._custom_collection_id_for_item(item)
        if collection_id:
            self.setCurrentItem(item)
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event) -> None:
        item = self.itemAt(event.position().toPoint())
        collection_id = self._custom_collection_id_for_item(item)
        if not collection_id:
            event.ignore()
            return
        raw_uids = bytes(event.mimeData().data(CHART_UIDS_MIME_TYPE)).decode("utf-8")
        chart_uids = [uid.strip().upper() for uid in raw_uids.splitlines() if uid.strip()]
        if chart_uids and callable(self.drop_chart_uids_on_collection):
            self.setCurrentItem(item)
            self.drop_chart_uids_on_collection(collection_id, chart_uids)
            event.acceptProposedAction()
            return
        event.ignore()

    @staticmethod
    def _custom_collection_id_for_item(item: QListWidgetItem | None) -> str | None:
        if item is None:
            return None
        collection_id = normalize_collection_id(item.data(Qt.UserRole))
        if collection_id and collection_id not in DEFAULT_COLLECTION_IDS:
            return collection_id
        return None


def prompt_chart_selection_for_collection_add(
    parent: QWidget,
    *,
    collection_name: str,
    chart_rows,
    chart_uid_by_local_id: dict[int, str],
) -> tuple[str, str] | None:
    """Prompt for one saved chart to add to the selected collection."""

    dialog = QDialog(parent)
    dialog.setWindowTitle(f"Search Chart to Add • {collection_name}")
    dialog.setModal(True)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(8)

    helper_label = QLabel("Search for a chart, then add it to this collection.")
    helper_label.setWordWrap(True)
    layout.addWidget(helper_label)

    chart_lookup: dict[str, tuple[str, str]] = {}
    labels: list[str] = []
    for row in chart_rows:
        chart_id, name, alias, *_rest = row
        local_id = int(chart_id)
        chart_uid = str(chart_uid_by_local_id.get(local_id) or "").strip().upper()
        if not chart_uid:
            continue
        display_name = name.strip() if isinstance(name, str) and name.strip() else f"Chart {chart_uid}"
        if alias:
            display_name = f"{display_name} ({alias})"
        label = f"{display_name}  [{chart_uid}]"
        labels.append(label)
        chart_lookup[label] = (chart_uid, display_name)

    chart_input = QLineEdit(dialog)
    chart_input.setPlaceholderText("Search chart name")
    completer = QCompleter(labels, chart_input)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)
    chart_input.setCompleter(completer)
    layout.addWidget(chart_input)

    buttons_row = QHBoxLayout()
    buttons_row.addStretch(1)
    cancel_button = QPushButton("Never mind", dialog)
    add_button = QPushButton(f"Add to {collection_name}", dialog)
    buttons_row.addWidget(cancel_button)
    buttons_row.addWidget(add_button)
    layout.addLayout(buttons_row)

    selected_chart: tuple[str, str] | None = None

    def _resolve_chart(raw_value: str) -> tuple[str, str] | None:
        query = raw_value.strip()
        if not query:
            return None
        direct_match = chart_lookup.get(query)
        if direct_match is not None:
            return direct_match
        for label, chart in chart_lookup.items():
            if query.lower() == label.lower():
                return chart
        return None

    def _submit() -> None:
        nonlocal selected_chart
        chart = _resolve_chart(chart_input.text())
        if chart is None:
            QMessageBox.warning(
                dialog,
                "Collections",
                "Select a saved chart from autocomplete before adding.",
            )
            return
        selected_chart = chart
        dialog.accept()

    add_button.clicked.connect(_submit)
    cancel_button.clicked.connect(dialog.reject)
    chart_input.returnPressed.connect(_submit)
    QTimer.singleShot(0, chart_input.setFocus)

    if dialog.exec() != QDialog.Accepted:
        return None
    return selected_chart
