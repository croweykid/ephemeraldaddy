"""Compare the aggregate astrological norms of two chart collections."""

from __future__ import annotations

from collections import Counter
from typing import Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QListWidget,
    QListWidgetItem,
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
    CollectionContrast,
    collection_trait_export_sections,
    filter_aggregable_charts,
)
from ephemeraldaddy.gui.features.charts.db_info_panel import add_similarity_match_row
from ephemeraldaddy.gui.features.charts.exporters import (
    export_similarities_analysis_json_dialog,
)
from ephemeraldaddy.gui.features.charts.similarities_db_norm import similarity_delta_rgb
from ephemeraldaddy.gui.features.charts.similarities_analysis import (
    build_similarity_factor_counts_for_charts,
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
            for item in sorted(
                self._custom_collections.values(), key=lambda item: item.name.casefold()
            )
        ]
        self.setWindowTitle("Compare-Contrast Collections")
        self.resize(1050, 650)
        layout = QVBoxLayout(self)
        intro = QLabel(
            "Choose two different collections. As in Similarities Analysis, a norm is a "
            "factual chart feature shared by at least two usable charts in its collection. "
            "The outer columns show norms exclusive to that collection; norms found on "
            "both sides appear only in the middle."
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

        self.compare_button = QPushButton("Compare & Contrast!", self)
        self.compare_button.clicked.connect(self._compare)
        layout.addWidget(self.compare_button, alignment=Qt.AlignHCenter)
        self.omission_notice = QLabel(self)
        self.omission_notice.setWordWrap(True)
        self.omission_notice.setVisible(False)
        layout.addWidget(self.omission_notice)
        self._populate_combos()
        columns = QHBoxLayout()
        self.result_browsers: list[QListWidget] = []
        self.export_buttons: list[QPushButton] = []
        self._trait_export_sections = [(), (), ()]
        for column_index in range(3):
            column = QVBoxLayout()
            export_button = QPushButton("Export Trait Profile", self)
            export_button.setEnabled(False)
            export_button.setToolTip(
                "Export this column independently as a traits-import-ready Python file."
            )
            export_button.clicked.connect(
                lambda _checked=False, index=column_index: self._export_column(index)
            )
            self.export_buttons.append(export_button)
            column.addWidget(export_button)
            browser = QListWidget(self)
            self.result_browsers.append(browser)
            column.addWidget(browser, 1)
            columns.addLayout(column, 1)
        layout.addLayout(columns, 1)
        self._render_empty()

    def _populate_combos(self) -> None:
        first_id = self._options[0][1] if self._options else ""
        second_id = self._options[1][1] if len(self._options) > 1 else ""
        self._rebuild_selector(self.collection_a_combo, first_id, excluded_id=second_id)
        self._rebuild_selector(self.collection_b_combo, second_id, excluded_id=first_id)
        self.compare_button.setEnabled(bool(first_id and second_id))

    def _rebuild_selector(
        self, combo: QComboBox, selected_id: str, *, excluded_id: str
    ) -> None:
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
        self._rebuild_selector(
            self.collection_a_combo, selected_a, excluded_id=selected_b
        )
        self._rebuild_selector(
            self.collection_b_combo, selected_b, excluded_id=selected_a
        )
        self._syncing_selectors = False
        self.compare_button.setEnabled(
            bool(selected_a and selected_b and selected_a != selected_b)
        )

    def _load_chart_population(self) -> dict[str, object]:
        """Hydrate the UID-keyed database population once for one comparison."""
        rows = db.list_charts()
        uid_by_row = db.get_chart_uid_map(row[0] for row in rows)
        return dict(db.load_charts_by_uids(uid_by_row.values()))

    def _charts_for_collection(
        self,
        collection_id: str,
        *,
        charts_by_uid: Mapping[str, object],
    ) -> list[object]:
        return [
            chart
            for chart_uid, chart in charts_by_uid.items()
            if chart is not None
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
            QMessageBox.information(
                self, self.windowTitle(), "Choose two different collections."
            )
            return
        charts_by_uid = self._load_chart_population()
        collection_members_a = self._charts_for_collection(
            collection_a, charts_by_uid=charts_by_uid
        )
        collection_members_b = self._charts_for_collection(
            collection_b, charts_by_uid=charts_by_uid
        )
        charts_a, omitted_a = filter_aggregable_charts(collection_members_a)
        charts_b, omitted_b = filter_aggregable_charts(collection_members_b)
        database_population, omitted_database = filter_aggregable_charts(
            charts_by_uid.values()
        )
        self._show_omission_notice(
            omitted_a,
            omitted_b,
            omitted_database,
        )
        if not charts_a or not charts_b:
            QMessageBox.information(
                self,
                self.windowTitle(),
                "Both collections need at least one usable chart.",
            )
            return
        provider = self.parent()
        required_methods = (
            "_similarities_body_label",
            "_dominant_sign_top_three_labels",
            "_dominant_planet_top_three_labels",
            "_dominant_house_top_three_labels",
            "_extract_human_design_profile",
            "_chart_human_design_profile",
        )
        if provider is None or not all(hasattr(provider, name) for name in required_methods):
            QMessageBox.critical(
                self, self.windowTitle(), "The Similarities Analysis provider is unavailable."
            )
            return
        factors_a = build_similarity_factor_counts_for_charts(provider, charts_a)
        factors_b = build_similarity_factor_counts_for_charts(provider, charts_b)
        database_factors = build_similarity_factor_counts_for_charts(
            provider, database_population
        )
        norms_a, counts_a, known_a = self._factor_counters(factors_a)
        norms_b, counts_b, known_b = self._factor_counters(factors_b)
        _database_norms, database_counts, database_known = self._factor_counters(
            database_factors
        )
        result = CollectionContrast(
            only_a=tuple(sorted(norms_a - norms_b)),
            overlap=tuple(sorted(norms_a & norms_b)),
            only_b=tuple(sorted(norms_b - norms_a)),
        )
        total_a, total_b = len(charts_a), len(charts_b)
        shared_counts = counts_a + counts_b
        shared_known = known_a + known_b
        labels = (
            f"Only {self.collection_a_combo.currentText()}",
            "Shared norms",
            f"Only {self.collection_b_combo.currentText()}",
        )
        self._render_norms(
            self.result_browsers[0],
            labels[0],
            result.only_a,
            counts_a,
            known_a,
            total_a,
            database_counts,
            database_known,
        )
        self._set_export_column(
            0,
            collection_trait_export_sections(
                result.only_a, counts_a, known_a, database_counts, database_known
            ),
        )
        shared_rows = tuple(
            (norm, counts_a, known_a, total_a, "A") for norm in result.overlap
        ) + tuple((norm, counts_b, known_b, total_b, "B") for norm in result.overlap)
        self._render_shared_norms(
            self.result_browsers[1],
            labels[1],
            shared_rows,
            database_counts,
            database_known,
        )
        self._set_export_column(
            1,
            collection_trait_export_sections(
                result.overlap,
                shared_counts,
                shared_known,
                database_counts,
                database_known,
            ),
        )
        self._render_norms(
            self.result_browsers[2],
            labels[2],
            result.only_b,
            counts_b,
            known_b,
            total_b,
            database_counts,
            database_known,
        )
        self._set_export_column(
            2,
            collection_trait_export_sections(
                result.only_b, counts_b, known_b, database_counts, database_known
            ),
        )

    def _set_export_column(self, index: int, export_sections: tuple) -> None:
        self._trait_export_sections[index] = export_sections
        self.export_buttons[index].setEnabled(bool(export_sections))

    @staticmethod
    def _factor_counters(factors: Mapping[str, tuple[dict[str, int], dict[str, int]]]):
        counts: Counter[CollectionNorm] = Counter()
        known: Counter[CollectionNorm] = Counter()
        norms: set[CollectionNorm] = set()
        for contrast_title, (section_counts, section_totals) in factors.items():
            section_title = contrast_title.replace(" in contrast", " in common")
            for label, count in section_counts.items():
                norm = CollectionNorm(section_title, label)
                counts[norm] = count
                known[norm] = section_totals.get(label, 0)
                if count >= min(2, max(1, known[norm])):
                    norms.add(norm)
        return norms, counts, known

    def _export_column(self, index: int) -> None:
        export_similarities_analysis_json_dialog(
            self, self._trait_export_sections[index]
        )

    def _show_omission_notice(
        self, omitted_a: int, omitted_b: int, omitted_db: int
    ) -> None:
        notices = []
        for label, count in (
            ("Collection A", omitted_a),
            ("Collection B", omitted_b),
            ("Database baseline", omitted_db),
        ):
            if count:
                noun = "chart was" if count == 1 else "charts were"
                notices.append(
                    f"{label}: {count} placeholder/hypothetical {noun} omitted from analysis."
                )
        self.omission_notice.setText(" ".join(notices))
        self.omission_notice.setVisible(bool(notices))

    @staticmethod
    def _add_heading(browser: QListWidget, text: str) -> None:
        item = QListWidgetItem(text)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        browser.addItem(item)

    def _render_norms(
        self,
        browser: QListWidget,
        heading: str,
        norms: tuple[CollectionNorm, ...],
        counts: Counter[CollectionNorm],
        known_totals: Counter[CollectionNorm],
        selection_total: int,
        database_counts: Counter[CollectionNorm],
        database_known_totals: Counter[CollectionNorm],
        *,
        label_prefix: str = "",
    ) -> None:
        browser.clear()
        self._add_heading(browser, heading)
        if not norms:
            browser.addItem("No aggregate norms.")
            return
        category = None
        for norm in norms:
            if norm.category != category:
                category = norm.category
                self._add_heading(browser, category)
            match_count = counts[norm]
            known_total = known_totals[norm]
            percent = round(match_count / known_total * 100) if known_total else 0
            database_known_total = database_known_totals[norm]
            db_percent = (
                round(database_counts[norm] / database_known_total * 100)
                if database_known_total
                else 0
            )
            add_similarity_match_row(
                section_list=browser,
                section_title=norm.category,
                label=f"{label_prefix}{norm.label}",
                match_count=match_count,
                percent_value=percent,
                db_percent_value=db_percent,
                selection_total_count=selection_total,
                total_count=known_total,
                similarity_rgb=similarity_delta_rgb(percent, db_percent, known_total),
                selection_label="collection",
                database_label="database",
            )

    def _render_shared_norms(
        self,
        browser: QListWidget,
        heading: str,
        rows: tuple[
            tuple[
                CollectionNorm,
                Counter[CollectionNorm],
                Counter[CollectionNorm],
                int,
                str,
            ],
            ...,
        ],
        database_counts: Counter[CollectionNorm],
        database_known_totals: Counter[CollectionNorm],
    ) -> None:
        browser.clear()
        self._add_heading(browser, heading)
        if not rows:
            browser.addItem("No aggregate norms.")
            return
        for norm, counts, known_totals, selection_total, collection_label in rows:
            match_count = counts[norm]
            known_total = known_totals[norm]
            percent = round(match_count / known_total * 100) if known_total else 0
            database_known_total = database_known_totals[norm]
            db_percent = (
                round(database_counts[norm] / database_known_total * 100)
                if database_known_total
                else 0
            )
            add_similarity_match_row(
                section_list=browser,
                section_title=norm.category,
                label=f"{collection_label}: {norm.label}",
                match_count=match_count,
                percent_value=percent,
                db_percent_value=db_percent,
                selection_total_count=selection_total,
                total_count=known_total,
                similarity_rgb=similarity_delta_rgb(percent, db_percent, known_total),
                selection_label="collection",
                database_label="database",
            )

    def _render_empty(self) -> None:
        self._trait_export_sections = [(), (), ()]
        for button in self.export_buttons:
            button.setEnabled(False)
        for browser, heading in zip(
            self.result_browsers,
            ("Only Collection A", "Shared norms", "Only Collection B"),
            strict=True,
        ):
            browser.clear()
            self._add_heading(browser, heading)
            browser.addItem("Run a comparison to see results.")


def show_compare_collections_dialog(
    parent: QWidget, *, custom_collections: Mapping[str, CustomCollection] | None = None
) -> CompareCollectionsDialog:
    dialog = CompareCollectionsDialog(parent, custom_collections=custom_collections)
    dialog.setAttribute(Qt.WA_DeleteOnClose)
    dialog.show()
    return dialog
