from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from ephemeraldaddy.gui.style import (
    DEFAULT_DROPDOWN_STYLE,
    DATABASE_VIEW_HEADER_COLOR,
    INACTIVE_ACTION_BUTTON_STYLE,
    similarity_gradient_rgb_for_range,
)

SIMILARITY_CALCULATOR_FACTOR_ROWS: tuple[tuple[str, str], ...] = (
    ("placement", "Placement score"),
    ("aspect", "Aspect score"),
    ("distribution", "Distribution score"),
    ("combined_dominance", "Combined dominance score"),
    ("nakshatra_placement", "Nakshatra placement score"),
    ("nakshatra_dominance", "Nakshatra dominance score"),
    ("defined_centers", "Defined centers score"),
    ("human_design_gates", "Human Design gates score"),
)


def build_similarity_calculator_settings_section(
    *,
    dialog: QDialog,
    section_layout: QVBoxLayout,
    subheader_style: str,
    on_mode_default_toggled: Callable[[bool], None],
    on_mode_comprehensive_toggled: Callable[[bool], None],
    on_mode_custom_toggled: Callable[[bool], None],
    on_checkbox_toggled: Callable[[str, bool], None],
    on_weight_changed: Callable[[str, float], None],
    on_placement_weighting_mode_changed: Callable[[str], None],
    on_reset_weights_clicked: Callable[[], None],
    on_calibrate_clicked: Callable[[], None],
    on_save_thresholds_clicked: Callable[[], None],
    on_reset_thresholds_clicked: Callable[[], None],
    threshold_rows: tuple[tuple[str, str], ...],
) -> dict[str, object]:
    similar_charts_algo_label = QLabel("Similarities Calculator")
    similar_charts_algo_label.setStyleSheet(subheader_style)
    section_layout.addWidget(similar_charts_algo_label)
    section_layout.addWidget(
        QLabel(
            "Choose which matching algorithm powers Similar Charts results."
        )
    )

    default_radio = QRadioButton("use default")
    comprehensive_radio = QRadioButton("use comprehensive")
    custom_radio = QRadioButton("use custom")
    similar_charts_algo_group = QButtonGroup(dialog)
    similar_charts_algo_group.setExclusive(True)
    similar_charts_algo_group.addButton(default_radio)
    similar_charts_algo_group.addButton(comprehensive_radio)
    similar_charts_algo_group.addButton(custom_radio)
    default_radio.toggled.connect(on_mode_default_toggled)
    comprehensive_radio.toggled.connect(on_mode_comprehensive_toggled)
    custom_radio.toggled.connect(on_mode_custom_toggled)
    section_layout.addWidget(default_radio)
    section_layout.addWidget(comprehensive_radio)
    section_layout.addWidget(custom_radio)

    calculator_checkboxes: dict[str, QCheckBox] = {}
    calculator_weights: dict[str, QDoubleSpinBox] = {}
    calculator_grid = QGridLayout()
    calculator_grid.setContentsMargins(0, 0, 0, 0)
    calculator_grid.setHorizontalSpacing(8)
    calculator_grid.setVerticalSpacing(6)
    calculator_grid.addWidget(QLabel("Factor"), 0, 1)
    calculator_grid.addWidget(QLabel("Weight"), 0, 2)
    calculator_grid.addWidget(QLabel("Selected Total"), 0, 3)
    total_weight_value_label = QLabel("0.00 / 1.00 (0.0%)")
    total_weight_value_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
    calculator_grid.addWidget(
        total_weight_value_label,
        1,
        3,
        len(SIMILARITY_CALCULATOR_FACTOR_ROWS),
        1,
        alignment=Qt.AlignRight | Qt.AlignTop,
    )
    for row_index, (key, label_text) in enumerate(SIMILARITY_CALCULATOR_FACTOR_ROWS, start=1):
        calculator_grid.addWidget(QLabel(label_text), row_index, 1)
        enabled_checkbox = QCheckBox()
        enabled_checkbox.setChecked(True)
        enabled_checkbox.stateChanged.connect(
            lambda _state, row_key=key, checkbox=enabled_checkbox: on_checkbox_toggled(
                row_key,
                checkbox.isChecked(),
            )
        )
        calculator_grid.addWidget(enabled_checkbox, row_index, 0, alignment=Qt.AlignCenter)
        weight_spinbox = QDoubleSpinBox()
        weight_spinbox.setDecimals(2)
        weight_spinbox.setRange(0.0, 1.0)
        weight_spinbox.setSingleStep(0.01)
        weight_spinbox.setAlignment(Qt.AlignRight)
        weight_spinbox.valueChanged.connect(
            lambda _value, row_key=key, spinbox=weight_spinbox: on_weight_changed(
                row_key,
                float(spinbox.value()),
            )
        )
        calculator_grid.addWidget(weight_spinbox, row_index, 2)
        calculator_checkboxes[key] = enabled_checkbox
        calculator_weights[key] = weight_spinbox
    section_layout.addLayout(calculator_grid)

    weighting_mode_row = QHBoxLayout()
    weighting_mode_label = QLabel("Placement weighting mode")
    weighting_mode_combo = QComboBox()
    weighting_mode_combo.addItem("Chart-defined weights", "chart_defined")
    weighting_mode_combo.addItem("Generic base weights", "generic")
    weighting_mode_combo.addItem("Hybrid (generic + dominant body bonuses)", "hybrid")
    weighting_mode_combo.currentIndexChanged.connect(
        lambda _index: on_placement_weighting_mode_changed(
            str(weighting_mode_combo.currentData() or "chart_defined")
        )
    )
    weighting_mode_row.addWidget(weighting_mode_label)
    weighting_mode_row.addWidget(weighting_mode_combo)
    weighting_mode_row.addStretch(1)
    section_layout.addLayout(weighting_mode_row)

    reset_similarity_weights_button = QPushButton("Reset Weights to Default")
    reset_similarity_weights_button.clicked.connect(on_reset_weights_clicked)
    section_layout.addWidget(reset_similarity_weights_button, alignment=Qt.AlignLeft)

    section_divider = QFrame()
    section_divider.setFrameShape(QFrame.HLine)
    section_divider.setFrameShadow(QFrame.Sunken)
    section_layout.addWidget(section_divider)

    calibrate_similarity_button = QPushButton("Calibrate Similarity Norms")
    calibrate_similarity_button.setToolTip(
        "Compute min/max/avg/median/mode similarity across saved chart pairs and save thresholds."
    )
    calibrate_similarity_button.clicked.connect(on_calibrate_clicked)
    section_layout.addWidget(calibrate_similarity_button)

    similarity_thresholds_label = QLabel("Similarity Thresholds (%)")
    similarity_thresholds_label.setStyleSheet(subheader_style)
    section_layout.addWidget(similarity_thresholds_label)
    section_layout.addWidget(
        QLabel(
            "Manual override for band cutoffs (q20/q40/q60/q80). "
            "Values are auto-sorted and saved systemwide."
        )
    )

    thresholds_grid = QGridLayout()
    thresholds_grid.setContentsMargins(0, 0, 0, 0)
    thresholds_grid.setHorizontalSpacing(8)
    thresholds_grid.setVerticalSpacing(6)
    threshold_spinboxes: dict[str, QDoubleSpinBox] = {}
    for row_index, (key, label_text) in enumerate(threshold_rows):
        label = QLabel(label_text)
        spinbox = QDoubleSpinBox()
        spinbox.setDecimals(1)
        spinbox.setRange(0.0, 100.0)
        spinbox.setSingleStep(0.5)
        spinbox.setSuffix("%")
        spinbox.setAlignment(Qt.AlignRight)
        thresholds_grid.addWidget(label, row_index, 0)
        thresholds_grid.addWidget(spinbox, row_index, 1)
        threshold_spinboxes[key] = spinbox
    section_layout.addLayout(thresholds_grid)

    thresholds_button_row = QHBoxLayout()
    thresholds_save_button = QPushButton("Save Threshold Overrides")
    thresholds_save_button.clicked.connect(on_save_thresholds_clicked)
    thresholds_reset_button = QPushButton("Reset Thresholds to Defaults")
    thresholds_reset_button.clicked.connect(on_reset_thresholds_clicked)
    thresholds_button_row.addWidget(thresholds_save_button)
    thresholds_button_row.addWidget(thresholds_reset_button)
    thresholds_button_row.addStretch(1)
    section_layout.addLayout(thresholds_button_row)

    return {
        "default_radio": default_radio,
        "comprehensive_radio": comprehensive_radio,
        "custom_radio": custom_radio,
        "calculator_checkboxes": calculator_checkboxes,
        "calculator_weights": calculator_weights,
        "calculator_total_label": total_weight_value_label,
        "placement_weighting_mode_combo": weighting_mode_combo,
        "threshold_spinboxes": threshold_spinboxes,
    }


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


class MetadataMigrationPanel(QDialog):
    """Floating metadata migration utility that stays above other app windows."""

    def __init__(
        self,
        *,
        parent: QWidget,
        on_alias_to_from_clicked: Callable[[], None],
        on_comments_to_source_clicked: Callable[[], None],
        on_clean_biography_clicked: Callable[[], None],
        on_get_bio_clicked: Callable[[], None],
        on_clean_birthplace_clicked: Callable[[], None],
    ) -> None:
        super().__init__(None)
        self.setWindowTitle("Metadata Cleanup Panel")
        self.setModal(False)
        self.setWindowFlag(Qt.Window, True)
        self.setWindowFlag(Qt.Tool, True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.resize(300, 560)
        self.setMinimumSize(200, 400)
        self.setStyleSheet(
            "QDialog { background-color: #26004d; }"
            "QLabel { color: #f5f5f5; }"
            "QPushButton {"
            "background-color: #1e6bd6;"
            "color: #ffffff;"
            "border: 1px solid #0f4eab;"
            "border-radius: 4px;"
            "padding: 6px 8px;"
            "}"
            "QPushButton:hover { background-color: #2a7be8; }"
            "QPushButton:pressed { background-color: #1559ba; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        intro = QLabel(
            "Runs metadata cleanup scripts against currently selected charts "
            "(Chart View: open chart, Database View: middle-panel selection)."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        alias_button = QPushButton("Alias -> From")
        alias_button.clicked.connect(on_alias_to_from_clicked)
        layout.addWidget(alias_button)

        alias_caption = QLabel(
            "takes the 'alias' property's value for each selected chart and moves it to each "
            "respective chart's 'from_whence' property"
        )
        alias_caption.setWordWrap(True)
        alias_caption.setStyleSheet("color: #ddd7df; font-style: italic;")
        layout.addWidget(alias_caption)

        comments_button = QPushButton("Comments -> Source")
        comments_button.clicked.connect(on_comments_to_source_clicked)
        layout.addWidget(comments_button)

        comments_caption = QLabel(
            "Finds all instances of URLs in these charts' Comments property and migrates "
            "them to the Source property"
        )
        comments_caption.setWordWrap(True)
        comments_caption.setStyleSheet("color: #ddd7df; font-style: italic;")
        layout.addWidget(comments_caption)

        biography_button = QPushButton("Clean up Biography Text")
        biography_button.clicked.connect(on_clean_biography_clicked)
        layout.addWidget(biography_button)

        biography_caption = QLabel(
            "For selected charts, keep biography text up to (but not including) "
            "'Astrological Profile of', and remove everything from that phrase onward"
        )
        biography_caption.setWordWrap(True)
        biography_caption.setStyleSheet("color: #ddd7df; font-style: italic;")
        layout.addWidget(biography_caption)

        get_bio_button = QPushButton("Get Bio")
        get_bio_button.clicked.connect(on_get_bio_clicked)
        layout.addWidget(get_bio_button)

        get_bio_caption = QLabel(
            "Imports biography from Astrotheme for selected chart(s). "
            "When multiple charts are selected, requests are delayed 1–6 seconds each."
        )
        get_bio_caption.setWordWrap(True)
        get_bio_caption.setStyleSheet("color: #ddd7df; font-style: italic;")
        layout.addWidget(get_bio_caption)

        birthplace_button = QPushButton("Clean up Birthplace")
        birthplace_button.clicked.connect(on_clean_birthplace_clicked)
        layout.addWidget(birthplace_button)

        birthplace_caption = QLabel(
            "Converts verbose imported birthplace metadata to concise Gazetteer-friendly "
            "city/region/country labels (removes street addresses, ZIP/postal codes, counties, and landmarks)."
        )
        birthplace_caption.setWordWrap(True)
        birthplace_caption.setStyleSheet("color: #ddd7df; font-style: italic;")
        layout.addWidget(birthplace_caption)
        layout.addStretch(1)

        if isinstance(parent, QWidget):
            self._anchor_near_parent(parent)

    def _anchor_near_parent(self, parent: QWidget) -> None:
        anchor = parent.mapToGlobal(QPoint(0, 0))
        self.move(anchor.x() + 36, anchor.y() + 84)


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
    FIELD_TAGS = "tags"
    FIELD_COLLECTIONS = "collections"
    FIELD_RELATIONSHIPS = "relationship_types"
    FIELD_SENTIMENTS = "sentiments"

    SORT_FREQUENCY = "frequency"
    SORT_ALPHABETICAL = "alphabetical"

    def __init__(
        self,
        *,
        parent: QWidget,
        load_usage,
        apply_change,
        label_limit: int,
        load_chart_names=None,
        collection_actions: dict[str, object] | None = None,
        initial_field: str | None = None,
        lock_field: bool = False,
        window_title: str = "Property Manager",
        intro_text: str = "Current + legacy labels found in database (including unused/orphaned).",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(window_title)
        self.resize(580, 520)
        self._load_usage = load_usage
        self._apply_change = apply_change
        self._load_chart_names = load_chart_names
        self._collection_actions = collection_actions or {}
        self._label_limit = max(1, label_limit)
        self._usage_data: dict[str, list[dict[str, int | str]]] = {}

        layout = QVBoxLayout(self)

        self._field_selector = QComboBox(self)
        self._field_selector.addItem("TAGS", self.FIELD_TAGS)
        self._field_selector.addItem("COLLECTIONS", self.FIELD_COLLECTIONS)
        self._field_selector.addItem("RELATIONSHIPS", self.FIELD_RELATIONSHIPS)
        self._field_selector.addItem("SENTIMENTS", self.FIELD_SENTIMENTS)
        for index in range(self._field_selector.count()):
            self._field_selector.setItemData(index, Qt.AlignCenter, Qt.TextAlignmentRole)
        self._field_selector.currentIndexChanged.connect(self._refresh_list)
        self._field_selector.setVisible(not lock_field)
        self._field_selector.setStyleSheet(
            DEFAULT_DROPDOWN_STYLE
            + """
QComboBox {
    min-height: 36px;
    padding: 6px 8px;
    text-align: center;
    color: """
            + DATABASE_VIEW_HEADER_COLOR
            + """;
    font-weight: 700;
}
QComboBox QAbstractItemView {
    color: """
            + DATABASE_VIEW_HEADER_COLOR
            + """;
    font-weight: 700;
}
"""
        )
        layout.addWidget(self._field_selector)

        layout.addSpacing(8)
        intro_label = QLabel(intro_text)
        intro_label.setStyleSheet("font-style: italic;")
        layout.addWidget(intro_label)

        sort_row = QHBoxLayout()
        sort_row.addStretch(1)
        sort_row.addWidget(QLabel("Sort:"))
        self._sort_selector = QComboBox(self)
        self._sort_selector.addItem("Frequency", self.SORT_FREQUENCY)
        self._sort_selector.addItem("Alphabetical", self.SORT_ALPHABETICAL)
        self._sort_selector.setStyleSheet(DEFAULT_DROPDOWN_STYLE)
        self._sort_selector.currentIndexChanged.connect(self._refresh_list)
        sort_row.addWidget(self._sort_selector)
        layout.addLayout(sort_row)

        split_layout = QHBoxLayout()
        self._list_widget = QListWidget(self)
        self._list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self._list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        split_layout.addWidget(self._list_widget, 2)

        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("Charts with selected property"))
        self._chart_names_list = QListWidget(self)
        self._chart_names_list.setSelectionMode(QAbstractItemView.NoSelection)
        right_panel.addWidget(self._chart_names_list, 1)
        split_layout.addLayout(right_panel, 1)
        layout.addLayout(split_layout)

        if initial_field in {
            self.FIELD_SENTIMENTS,
            self.FIELD_RELATIONSHIPS,
            self.FIELD_TAGS,
            self.FIELD_COLLECTIONS,
        }:
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
        self._new_button = QPushButton("New")
        self._new_button.clicked.connect(self._create_collection)
        self._add_selected_button = QPushButton("Add Selected Charts")
        self._add_selected_button.clicked.connect(self._add_selected_to_collection)
        self._remove_selected_button = QPushButton("Remove Selected Charts")
        self._remove_selected_button.clicked.connect(self._remove_selected_from_collection)
        # refresh_button = QPushButton("Refresh")
        # refresh_button.clicked.connect(self._reload_usage)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)

        button_row.addWidget(self._rename_button)
        button_row.addWidget(self._delete_button)
        button_row.addWidget(self._merge_button)
        button_row.addWidget(self._new_button)
        button_row.addWidget(self._add_selected_button)
        button_row.addWidget(self._remove_selected_button)
        button_row.addStretch(1)
        #button_row.addWidget(refresh_button)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

        # Defer loading so the dialog can render immediately before DB work runs.
        QTimer.singleShot(0, self._reload_usage)

    def _active_field(self) -> str:
        value = self._field_selector.currentData()
        return str(value or self.FIELD_SENTIMENTS)

    def _active_rows(self) -> list[dict[str, int | str]]:
        rows = list(self._usage_data.get(self._active_field(), []))
        sort_mode = self.SORT_FREQUENCY
        if hasattr(self, "_sort_selector"):
            sort_mode = str(self._sort_selector.currentData() or self.SORT_FREQUENCY)
        if sort_mode == self.SORT_ALPHABETICAL:
            rows.sort(key=lambda row: str(row.get("label", "")).casefold())
            return rows
        rows.sort(
            key=lambda row: (
                -int(row.get("count", 0) or 0),
                str(row.get("label", "")).casefold(),
            )
        )
        return rows

    def _sync_action_buttons(self) -> None:
        if not hasattr(self, "_rename_button") or not hasattr(self, "_delete_button"):
            return
        selected_count = len(self._selected_labels())
        is_collections = self._active_field() == self.FIELD_COLLECTIONS
        selected_key = self._selected_key()
        selected_row = self._row_for_key(selected_key)
        can_edit_selected = selected_row is not None and bool(selected_row.get("editable", True))
        rename_enabled = selected_count == 1 and can_edit_selected
        delete_enabled = selected_count >= 1
        if selected_count == 1 and not can_edit_selected:
            delete_enabled = False
        if is_collections:
            delete_enabled = selected_count == 1 and can_edit_selected
        self._rename_button.setEnabled(rename_enabled)
        self._delete_button.setEnabled(delete_enabled)
        self._rename_button.setStyleSheet("" if rename_enabled else INACTIVE_ACTION_BUTTON_STYLE)
        self._delete_button.setStyleSheet("" if delete_enabled else INACTIVE_ACTION_BUTTON_STYLE)

        if not hasattr(self, "_merge_button"):
            return
        is_tags = self._active_field() == self.FIELD_TAGS
        self._merge_button.setVisible(is_tags)
        self._merge_button.setEnabled(is_tags and len(self._active_rows()) >= 2)
        self._new_button.setVisible(is_collections)
        self._add_selected_button.setVisible(is_collections)
        self._remove_selected_button.setVisible(is_collections)
        can_modify_collection = is_collections and selected_count == 1 and can_edit_selected
        self._add_selected_button.setEnabled(can_modify_collection)
        self._remove_selected_button.setEnabled(can_modify_collection)
        self._add_selected_button.setStyleSheet("" if can_modify_collection else INACTIVE_ACTION_BUTTON_STYLE)
        self._remove_selected_button.setStyleSheet("" if can_modify_collection else INACTIVE_ACTION_BUTTON_STYLE)

    def _reload_usage(self) -> None:
        try:
            self._usage_data = self._load_usage()
        except Exception as exc:
            QMessageBox.critical(self, "Manage metadata", f"Could not load labels:\n{exc}")
            self._usage_data = {
                self.FIELD_SENTIMENTS: [],
                self.FIELD_RELATIONSHIPS: [],
                self.FIELD_TAGS: [],
                self.FIELD_COLLECTIONS: [],
            }
        self._refresh_list()

    def _refresh_list(self) -> None:
        rows = self._active_rows()
        self._list_widget.clear()
        minimum_count = 0
        maximum_count = 0
        if rows:
            counts = [int(row.get("count", 0) or 0) for row in rows]
            minimum_count = min(counts)
            maximum_count = max(counts)
        for row in rows:
            label = str(row.get("label", "")).strip()
            count = int(row.get("count", 0) or 0)
            item = QListWidgetItem(f"{label}  ({count} charts)")
            item.setData(Qt.UserRole, label)
            item.setData(Qt.UserRole + 1, str(row.get("key", label)))
            red, green, blue = similarity_gradient_rgb_for_range(
                count,
                minimum_count,
                maximum_count,
            )
            item.setForeground(QColor(red, green, blue))
            self._list_widget.addItem(item)
        self._on_selection_changed()

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

    def _selected_key(self) -> str:
        item = self._list_widget.currentItem()
        if item is None:
            return ""
        return str(item.data(Qt.UserRole + 1) or "").strip()

    def _row_for_key(self, key: str) -> dict[str, int | str] | None:
        for row in self._active_rows():
            row_key = str(row.get("key", row.get("label", ""))).strip()
            if row_key == key:
                return row
        return None

    def _on_selection_changed(self) -> None:
        self._sync_action_buttons()
        self._refresh_chart_names()

    def _refresh_chart_names(self) -> None:
        self._chart_names_list.clear()
        if not callable(self._load_chart_names):
            return
        selected_label = self._selected_label()
        selected_key = self._selected_key()
        if not selected_label:
            return
        try:
            chart_names = self._load_chart_names(self._active_field(), selected_label, selected_key)
        except Exception:
            chart_names = []
        for chart_name in chart_names:
            clean_name = str(chart_name).strip()
            if clean_name:
                self._chart_names_list.addItem(clean_name)

    def _delete_selected(self) -> None:
        if self._active_field() == self.FIELD_COLLECTIONS:
            self._delete_selected_collection()
            return
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
        if self._active_field() == self.FIELD_COLLECTIONS:
            self._rename_selected_collection()
            return
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

    def _create_collection(self) -> None:
        action = self._collection_actions.get("create")
        if not callable(action):
            return
        action()
        self._reload_usage()

    def _rename_selected_collection(self) -> None:
        key = self._selected_key()
        action = self._collection_actions.get("rename")
        if not key or not callable(action):
            return
        action(key)
        self._reload_usage()

    def _delete_selected_collection(self) -> None:
        key = self._selected_key()
        action = self._collection_actions.get("delete")
        if not key or not callable(action):
            return
        action(key)
        self._reload_usage()

    def _add_selected_to_collection(self) -> None:
        key = self._selected_key()
        action = self._collection_actions.get("add_selected")
        if not key or not callable(action):
            return
        action(key)
        self._reload_usage()

    def _remove_selected_from_collection(self) -> None:
        key = self._selected_key()
        action = self._collection_actions.get("remove_selected")
        if not key or not callable(action):
            return
        action(key)
        self._reload_usage()

    # def _delete_selected(self) -> None:
    #     old_label = self._selected_label()
    #     if not old_label:
    #         QMessageBox.information(self, "Manage metadata", "Select a label to delete.")
    #         return
    #     confirm = QMessageBox.question(
    #         self,
    #         "Delete label",
    #         f"Delete '{old_label}' from all charts?\n\nThis cannot be undone except by restoring a backup.",
    #         QMessageBox.Yes | QMessageBox.No,
    #         QMessageBox.No,
    #     )
    #     if confirm != QMessageBox.Yes:
    #         return

    #     summary = self._apply_change(
    #         field=self._active_field(),
    #         old_label=old_label,
    #         new_label="",
    #     )
    #     QMessageBox.information(
    #         self,
    #         "Delete complete",
    #         f"Removed {summary.get('occurrences_updated', 0)} occurrences across "
    #         f"{summary.get('rows_updated', 0)} chart(s).",
    #     )
    #     self._reload_usage()

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
