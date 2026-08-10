"""Compare the aggregate astrological norms of two chart collections."""

from __future__ import annotations

from html import escape
from typing import Iterable, Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.core import db
from ephemeraldaddy.gui.features.charts.collections import (
    DEFAULT_COLLECTION_OPTIONS,
    CustomCollection,
    chart_belongs_to_collection,
)
from ephemeraldaddy.gui.features.similarities.collection_contrast import (
    CollectionNorm,
    contrast_collection_norms,
)


class CompareCollectionsDialog(QDialog):
    """Collection picker and three-column, Venn-like comparison result view."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        custom_collections: Mapping[str, CustomCollection] | None = None,
    ) -> None:
        super().__init__(parent)
        self._custom_collections = dict(custom_collections or {})
        self._syncing_selectors = False
        self._options = list(DEFAULT_COLLECTION_OPTIONS) + [
            (item.name, item.collection_id)
            for item in sorted(self._custom_collections.values(), key=lambda item: item.name.casefold())
        ]
        self.setWindowTitle("Compare-Contrast Collections")
        self.resize(1050, 650)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Choose two different collections. A norm is a factual chart feature shared by at least half of the usable charts in its collection."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        selectors = QHBoxLayout()
        self.collection_a_combo = QComboBox(self)
        self.collection_b_combo = QComboBox(self)
        selectors.addWidget(QLabel("Collection A:"))
        selectors.addWidget(self.collection_a_combo, 1)
        selectors.addWidget(QLabel("Collection B:"))
        selectors.addWidget(self.collection_b_combo, 1)
        layout.addLayout(selectors)
        self.collection_a_combo.currentIndexChanged.connect(self._selection_changed)
        self.collection_b_combo.currentIndexChanged.connect(self._selection_changed)
        self._populate_combos()

        self.compare_button = QPushButton("Compare & Contrast!", self)
        self.compare_button.clicked.connect(self._compare)
        layout.addWidget(self.compare_button, alignment=Qt.AlignHCenter)
        columns = QHBoxLayout()
        self.result_browsers: list[QTextBrowser] = []
        for _ in range(3):
            browser = QTextBrowser(self)
            self.result_browsers.append(browser)
            columns.addWidget(browser, 1)
        layout.addLayout(columns, 1)
        self._render_empty()

    def _populate_combos(self) -> None:
        first_id = self._options[0][1] if self._options else ""
        second_id = self._options[1][1] if len(self._options) > 1 else ""
        self._rebuild_selector(self.collection_a_combo, first_id, excluded_id=second_id)
        self._rebuild_selector(self.collection_b_combo, second_id, excluded_id=first_id)
        self.compare_button.setEnabled(bool(first_id and second_id))

    def _rebuild_selector(self, combo: QComboBox, selected_id: str, *, excluded_id: str) -> None:
        combo.blockSignals(True)
        combo.clear()
        selected_index = -1
        for label, collection_id in self._options:
            if collection_id == excluded_id:
                continue
            combo.addItem(label, collection_id)
            if collection_id == selected_id:
                selected_index = combo.count() - 1
        combo.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        combo.blockSignals(False)

    def _selection_changed(self, *_args: object) -> None:
        if self._syncing_selectors:
            return
        self._syncing_selectors = True
        selected_a = str(self.collection_a_combo.currentData() or "")
        selected_b = str(self.collection_b_combo.currentData() or "")
        self._rebuild_selector(self.collection_a_combo, selected_a, excluded_id=selected_b)
        self._rebuild_selector(self.collection_b_combo, selected_b, excluded_id=selected_a)
        self._syncing_selectors = False
        self.compare_button.setEnabled(bool(selected_a and selected_b and selected_a != selected_b))

    def _charts_for_collection(self, collection_id: str) -> list[object]:
        rows = db.list_charts()
        uid_by_row = db.get_chart_uid_map(row[0] for row in rows)
        charts_by_uid = db.load_charts_by_uids(uid_by_row.values())
        return [
            chart
            for chart_uid, chart in charts_by_uid.items()
            if chart is not None
            and not bool(getattr(chart, "is_placeholder", False))
            and chart_belongs_to_collection(
                collection_id,
                chart=chart,
                source=getattr(chart, "source", None),
                custom_collections=self._custom_collections,
                chart_uid=chart_uid,
            )
        ]

    def _compare(self) -> None:
        collection_a = str(self.collection_a_combo.currentData() or "")
        collection_b = str(self.collection_b_combo.currentData() or "")
        if not collection_a or not collection_b or collection_a == collection_b:
            QMessageBox.information(self, self.windowTitle(), "Choose two different collections.")
            return
        charts_a = self._charts_for_collection(collection_a)
        charts_b = self._charts_for_collection(collection_b)
        if not charts_a or not charts_b:
            QMessageBox.information(self, self.windowTitle(), "Both collections need at least one usable chart.")
            return
        result = contrast_collection_norms(charts_a, charts_b)
        labels = (
            f"Only {self.collection_a_combo.currentText()}",
            "Shared norms",
            f"Only {self.collection_b_combo.currentText()}",
        )
        for browser, heading, norms in zip(
            self.result_browsers, labels, (result.only_a, result.overlap, result.only_b), strict=True
        ):
            browser.setHtml(self._norms_html(heading, norms))

    @staticmethod
    def _norms_html(heading: str, norms: Iterable[CollectionNorm]) -> str:
        grouped: dict[str, list[str]] = {}
        for norm in norms:
            grouped.setdefault(norm.category, []).append(norm.label)
        parts = [f"<h2>{escape(heading)}</h2>"]
        if not grouped:
            parts.append("<p><i>No aggregate norms.</i></p>")
        for category, labels in grouped.items():
            parts.append(f"<h3>{escape(category)}</h3><ul>")
            parts.extend(f"<li>{escape(label)}</li>" for label in labels)
            parts.append("</ul>")
        return "".join(parts)

    def _render_empty(self) -> None:
        for browser, heading in zip(
            self.result_browsers, ("Only Collection A", "Shared norms", "Only Collection B"), strict=True
        ):
            browser.setHtml(f"<h2>{heading}</h2><p>Run a comparison to see results.</p>")


def show_compare_collections_dialog(
    parent: QWidget, *, custom_collections: Mapping[str, CustomCollection] | None = None
) -> CompareCollectionsDialog:
    dialog = CompareCollectionsDialog(parent, custom_collections=custom_collections)
    dialog.setAttribute(Qt.WA_DeleteOnClose)
    dialog.show()
    return dialog
