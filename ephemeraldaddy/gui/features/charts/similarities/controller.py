"""Controller for the Manage Charts Similarities Analysis feature.

The controller is the authoritative owner for Similarities Analysis panel state:
export sections, pair controls, chart lookup, DB baseline cache, info-panel
widgets/routing, and lifecycle entry points.  ``ManageChartsDialog`` delegates
panel construction and user-facing actions here while calculation-heavy helper
methods remain callable on the host during this extraction step.
"""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QCompleter,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.gui.features.charts.db_info_panel import DBInfoPanel
from ephemeraldaddy.gui.features.charts.similarities_analysis import (
    SimilaritiesDbBaselineCache,
)


class SimilaritiesController:
    """Own Similarities Analysis state and delegate host integration points."""

    _LEGACY_STATE_ATTRS = (
        "_similarities_export_sections",
        "_similarities_pair_button",
        "_dissimilarities_pair_button",
        "_similarities_pair_result_label",
        "_similarities_chart_lookup",
        "_similarities_first_chart_input",
        "_similarities_second_chart_input",
        "_similarities_first_use_checkbox",
        "_similarities_second_use_checkbox",
        "_similarities_db_baseline_cache",
    )

    def __init__(
        self,
        host: Any,
        *,
        panel_header_style: str,
        inactive_button_style: str,
        configure_export_button: Callable[..., None],
        get_share_icon_path: Callable[[], str | None],
        add_collapsible_section: Callable[..., tuple[Any, Any]],
    ) -> None:
        self.host = host
        self.panel_header_style = panel_header_style
        self.inactive_button_style = inactive_button_style
        self.configure_export_button = configure_export_button
        self.get_share_icon_path = get_share_icon_path
        self.add_collapsible_section = add_collapsible_section
        self.export_sections: list[tuple[str, list[tuple[Any, ...]]]] = []
        self.pair_button: QPushButton | None = None
        self.dissimilarity_pair_button: QPushButton | None = None
        self.pair_result_label: QLabel | None = None
        self.chart_lookup: dict[str, int] = {}
        self.first_chart_input: QLineEdit | None = None
        self.second_chart_input: QLineEdit | None = None
        self.first_use_checkbox: QCheckBox | None = None
        self.second_use_checkbox: QCheckBox | None = None
        self.db_baseline_cache = SimilaritiesDbBaselineCache()
        self.panel: QWidget | None = None
        self.panel_scroll: QWidget | None = None
        self.status_label: QLabel | None = None
        self.db_info_panel: QWidget | None = None

    def install_legacy_attributes(self) -> None:
        """Expose controller-owned state under historical host attr names.

        Existing similarity algorithms still read these names on the dialog.
        Keeping aliases here makes the controller authoritative without forcing a
        high-risk rewrite of every calculation helper in one change.
        """
        self.host._similarities_export_sections = self.export_sections
        self.host._similarities_pair_button = self.pair_button
        self.host._dissimilarities_pair_button = self.dissimilarity_pair_button
        self.host._similarities_pair_result_label = self.pair_result_label
        self.host._similarities_chart_lookup = self.chart_lookup
        self.host._similarities_first_chart_input = self.first_chart_input
        self.host._similarities_second_chart_input = self.second_chart_input
        self.host._similarities_first_use_checkbox = self.first_use_checkbox
        self.host._similarities_second_use_checkbox = self.second_use_checkbox
        self.host._similarities_db_baseline_cache = self.db_baseline_cache

    def capture_legacy_attributes(self) -> None:
        """Refresh controller references after legacy panel-building code runs."""
        self.export_sections = getattr(
            self.host, "_similarities_export_sections", self.export_sections
        )
        self.pair_button = getattr(self.host, "_similarities_pair_button", None)
        self.dissimilarity_pair_button = getattr(
            self.host, "_dissimilarities_pair_button", None
        )
        self.pair_result_label = getattr(
            self.host, "_similarities_pair_result_label", None
        )
        self.chart_lookup = getattr(
            self.host, "_similarities_chart_lookup", self.chart_lookup
        )
        self.first_chart_input = getattr(
            self.host, "_similarities_first_chart_input", None
        )
        self.second_chart_input = getattr(
            self.host, "_similarities_second_chart_input", None
        )
        self.first_use_checkbox = getattr(
            self.host, "_similarities_first_use_checkbox", None
        )
        self.second_use_checkbox = getattr(
            self.host, "_similarities_second_use_checkbox", None
        )
        self.db_baseline_cache = getattr(
            self.host, "_similarities_db_baseline_cache", self.db_baseline_cache
        )
        self.status_label = getattr(self.host, "similarities_status_label", None)
        self.db_info_panel = getattr(self.host, "similarities_db_info_panel", None)

    def build_panel(self) -> QWidget:
        """Build and retain the Similarities Analysis panel widget tree."""
        self.install_legacy_attributes()
        panel = QWidget()
        panel.setMinimumWidth(260)
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignTop)
        layout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        panel.setLayout(layout)

        title_row = QWidget()
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)
        title_row.setLayout(title_layout)

        title = QLabel("Similarities Analysis")
        title.setStyleSheet(self.panel_header_style)
        title_layout.addWidget(title)
        title_layout.addStretch(1)

        share_icon_path = self.get_share_icon_path()

        json_export_button = QPushButton()
        self.configure_export_button(
            json_export_button,
            label="data",
            tooltip="Export similarities analysis as Python",
            share_icon_path=share_icon_path,
        )
        json_export_button.clicked.connect(self.host._export_similarities_analysis_json)
        title_layout.addWidget(json_export_button, alignment=Qt.AlignRight)

        export_button = QPushButton()
        self.configure_export_button(
            export_button,
            label="text",
            tooltip="Export similarities analysis as CSV",
            share_icon_path=share_icon_path,
        )
        export_button.clicked.connect(self.host._export_similarities_analysis_csv)
        title_layout.addWidget(export_button, alignment=Qt.AlignRight)
        layout.addWidget(title_row)

        self.status_label = QLabel(
            "Select 2 or more charts to view similarities across selected charts."
        )
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #bbbbbb;")
        layout.addWidget(self.status_label)
        self.host.similarities_status_label = self.status_label

        self.refresh_chart_options()
        use_this_checkbox_style = (
            "QCheckBox { color: #9ee09e; }"
            "QCheckBox::indicator { width: 14px; height: 14px; }"
            "QCheckBox::indicator:unchecked {"
            "  border: 1px solid #3b5a3b;"
            "  background-color: #1b241b;"
            "}"
            "QCheckBox::indicator:checked {"
            "  border: 1px solid #4f8f4f;"
            "  background-color: #2f7f2f;"
            "}"
        )
        chart_labels = list(self.chart_lookup.keys())
        input_rows = (
            ("Select first chart", "first_chart_input", "first_use_checkbox"),
            ("Select second chart", "second_chart_input", "second_use_checkbox"),
        )
        for placeholder, input_attr, checkbox_attr in input_rows:
            input_row = QWidget()
            input_layout = QHBoxLayout()
            input_layout.setContentsMargins(0, 0, 0, 0)
            input_layout.setSpacing(6)
            input_row.setLayout(input_layout)

            chart_input = QLineEdit()
            chart_input.setPlaceholderText(placeholder)
            completer = QCompleter(chart_labels, chart_input)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            chart_input.setCompleter(completer)
            chart_input.textChanged.connect(
                lambda _text: self.update_analysis(self.host._selected_chart_ids())
            )
            input_layout.addWidget(chart_input, stretch=1)

            use_checkbox = QCheckBox("use this")
            use_checkbox.setStyleSheet(use_this_checkbox_style)
            use_checkbox.toggled.connect(
                lambda _checked: self.update_analysis(self.host._selected_chart_ids())
            )
            input_layout.addWidget(use_checkbox, stretch=0, alignment=Qt.AlignRight)

            setattr(self, input_attr, chart_input)
            setattr(self, checkbox_attr, use_checkbox)
            layout.addWidget(input_row)

        pair_row = QWidget()
        pair_layout = QHBoxLayout()
        pair_layout.setContentsMargins(0, 0, 0, 0)
        pair_layout.setSpacing(8)
        pair_row.setLayout(pair_layout)
        self.pair_button = QPushButton("Calculate Similarities")
        self.pair_button.setStyleSheet(self.inactive_button_style)
        self.pair_button.setToolTip("Select exactly 2 charts to compare.")
        self.pair_button.clicked.connect(
            self.host._calculate_pair_similarity_from_selection
        )
        pair_layout.addWidget(self.pair_button, alignment=Qt.AlignLeft)

        self.dissimilarity_pair_button = QPushButton("Calculate Dissimilarities")
        self.dissimilarity_pair_button.setStyleSheet(self.inactive_button_style)
        self.dissimilarity_pair_button.setToolTip("Select exactly 2 charts to compare.")
        self.dissimilarity_pair_button.clicked.connect(
            self.host._calculate_pair_dissimilarity_from_selection
        )
        pair_layout.addWidget(self.dissimilarity_pair_button, alignment=Qt.AlignLeft)
        pair_layout.addStretch(1)
        layout.addWidget(pair_row)

        self.pair_result_label = QLabel(
            "Select 2 charts, or use chart inputs with “use this” checked."
        )
        self.pair_result_label.setWordWrap(True)
        self.pair_result_label.setStyleSheet("color: #9b9b9b;")
        layout.addWidget(self.pair_result_label)

        similarities_list_style = (
            "QListWidget {"
            "  background-color: #151515;"
            "  border: 1px solid #333333;"
            "}"
            "QListWidget::item {"
            "  padding: 4px 6px;"
            "}"
        )
        sections = (
            ("common_positions", "Signs in positions in common", 160),
            ("houses_in_positions", "Houses in positions in common", 120),
            ("signs_in_houses", "Signs in houses in common", 120),
            ("dominant_signs", "Top 3 Dominant Signs in common", 100),
            ("dominant_bodies", "Top 3 Dominant Bodies in common", 100),
            ("dominant_houses", "Top 3 Dominant Houses in common", 100),
            ("dominant_nakshatras", "Dominant nakshatras in common", 100),
            ("common_aspects", "Aspects in common", 160),
            ("common_hd_gates", "Gates in common", 120),
            ("common_hd_channels", "Channels in common", 120),
            ("common_hd_defined_centers", "Defined Centers in common", 100),
            ("common_hd_authorities", "Authorities in common", 100),
            ("common_hd_profiles", "Profiles in common", 100),
            ("common_bazi_signs", "BaZi signs in common", 100),
        )
        for attr_name, title_text, min_height in sections:
            toggle, section_list = self.add_collapsible_section(
                layout,
                title_text,
                min_height=min_height,
                list_style=similarities_list_style,
            )
            setattr(self.host, f"similarities_{attr_name}_toggle", toggle)
            setattr(self.host, f"similarities_{attr_name}_list", section_list)

        self.db_info_panel = DBInfoPanel(panel)
        self.db_info_panel.setVisible(False)
        self.host.similarities_db_info_panel = self.db_info_panel
        layout.addWidget(self.db_info_panel)
        layout.addStretch(1)

        self.panel = panel
        self.install_legacy_attributes()
        return panel

    def set_panel_scroll(self, panel_scroll: QWidget | None) -> None:
        self.panel_scroll = panel_scroll

    def set_export_sections(
        self, sections: list[tuple[str, list[tuple[Any, ...]]]]
    ) -> None:
        self.export_sections = sections
        self.host._similarities_export_sections = self.export_sections

    def set_chart_lookup(self, chart_lookup: dict[str, int]) -> None:
        self.chart_lookup = chart_lookup
        self.host._similarities_chart_lookup = self.chart_lookup

    def refresh_chart_options(self) -> None:
        self.host._refresh_similarities_chart_options()
        self.capture_legacy_attributes()

    def update_analysis(self, chart_ids: list[int]) -> None:
        self.host._update_similarities_analysis(chart_ids)
        self.capture_legacy_attributes()

    def calculate_pair_similarity(self) -> None:
        self.host._calculate_pair_similarity_from_selection()
        self.capture_legacy_attributes()

    def calculate_pair_dissimilarity(self) -> None:
        self.host._calculate_pair_dissimilarity_from_selection()
        self.capture_legacy_attributes()

    def export_json(self) -> None:
        self.host._export_similarities_analysis_json()

    def export_csv(self) -> None:
        self.host._export_similarities_analysis_csv()

    def set_db_info_panel_visible(self, visible: bool) -> None:
        self.capture_legacy_attributes()
        info_panel = self.db_info_panel
        if info_panel is None:
            return
        info_panel.setVisible(bool(visible))
        if not visible:
            return
        panel_scroll = self.panel_scroll or getattr(
            self.host, "similarities_analysis_panel_scroll", None
        )
        if panel_scroll is not None:
            self.host._stabilize_left_scroll_panel_layout(panel_scroll)
            scrollbar = panel_scroll.verticalScrollBar()
            if scrollbar is not None:
                QTimer.singleShot(0, lambda sb=scrollbar: sb.setValue(sb.maximum()))
                QTimer.singleShot(120, lambda sb=scrollbar: sb.setValue(sb.maximum()))

    def toggle_db_info_panel(self) -> None:
        self.capture_legacy_attributes()
        info_panel = self.db_info_panel
        if info_panel is None:
            return
        self.set_db_info_panel_visible(not info_panel.isVisible())

    def handle_info_target_requested(self, target: str) -> None:
        self.capture_legacy_attributes()
        info_panel = self.db_info_panel
        if info_panel is None:
            return
        normalized_target = str(target or "").strip().lower()
        if not normalized_target:
            return
        self.set_db_info_panel_visible(True)
        target_output = info_panel.output

        def _render_target() -> None:
            if normalized_target.startswith("gate:"):
                gate_text = normalized_target.split(":", 1)[1]
                if gate_text.isdigit():
                    gate_number = int(gate_text)
                    if not self.host._invoke_db_info_renderer(
                        "_show_human_design_gate_line_info",
                        target_output,
                        gate_number,
                        None,
                    ):
                        self.host._render_db_gate_info_fallback(
                            target_output, gate_number
                        )
                    return
            if normalized_target.startswith("house:"):
                house_text = normalized_target.split(":", 1)[1]
                if house_text.isdigit():
                    house_number = int(house_text)
                    if not self.host._invoke_db_info_renderer(
                        "_show_house_keyword_info",
                        target_output,
                        house_number,
                    ):
                        self.host._render_db_house_info_fallback(
                            target_output, house_number
                        )
                    return
            target_output.setPlainText(
                "No DB info renderer is available for this item yet."
            )

        self.host._run_with_chart_info_output(target_output, _render_target)

    def clear_db_baseline_cache(self) -> None:
        self.db_baseline_cache.clear()
