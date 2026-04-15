"""Database View info-panel helpers for similarities analytics."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


def parse_similarity_info_target(section_title: str, label: str) -> str | None:
    """Return a normalized info target key for supported similarities rows."""
    section_key = str(section_title or "").strip().lower()
    normalized_label = str(label or "").strip()

    if section_key == "gates in common":
        gate_token = normalized_label.replace("Gate", "").strip()
        if gate_token.isdigit():
            return f"gate:{int(gate_token)}"

    if section_key == "top 3 dominant houses in common":
        house_token = normalized_label.replace("House", "").strip()
        if house_token.isdigit():
            return f"house:{int(house_token)}"

    return None


class DBInfoPanel(QWidget):
    """Dismissible DB Info panel for the Database View left rail."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dbInfoPanel")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.setLayout(layout)

        header = QWidget(self)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        header.setLayout(header_layout)

        self.title_label = QLabel("DB Info Panel", header)
        self.title_label.setStyleSheet("font-weight: 600; color: #f4d27a;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)

        self.close_button = QToolButton(header)
        self.close_button.setText("✕")
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.setAutoRaise(True)
        self.close_button.setToolTip("Close DB Info Panel")
        self.close_button.setFixedSize(20, 20)
        self.close_button.clicked.connect(self.hide)
        header_layout.addWidget(self.close_button, alignment=Qt.AlignRight)

        layout.addWidget(header)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setPlaceholderText(
            "Click a supported Similarities item to view DB info here."
        )
        self.output.setMinimumHeight(140)
        layout.addWidget(self.output, 1)


def add_similarity_match_row(
    *,
    section_list: QListWidget,
    section_title: str,
    label: str,
    match_count: int,
    percent_value: int,
    db_percent_value: int,
    selection_total_count: int,
    total_count: int,
    similarity_rgb: tuple[int, int, int],
    on_info_target_requested: Callable[[str], None] | None = None,
) -> None:
    """Render one similarities list row, with optional clickable info target."""
    similarity_red, similarity_green, similarity_blue = similarity_rgb
    info_target = parse_similarity_info_target(section_title, label)

    item = QListWidgetItem()
    row_widget = QWidget(section_list)
    row_layout = QVBoxLayout(row_widget)
    row_layout.setContentsMargins(6, 2, 6, 2)
    row_layout.setSpacing(2)

    top_row = QWidget(row_widget)
    top_layout = QHBoxLayout(top_row)
    top_layout.setContentsMargins(0, 0, 0, 0)
    top_layout.setSpacing(10)

    if info_target and callable(on_info_target_requested):
        label_widget = QPushButton(f"({match_count}) {label}")
        label_widget.setFlat(True)
        label_widget.setCursor(Qt.PointingHandCursor)
        label_widget.setStyleSheet(
            "QPushButton {"
            f"  color: rgb({similarity_red}, {similarity_green}, {similarity_blue});"
            "  text-align: left;"
            "  border: none;"
            "  padding: 0;"
            "  text-decoration: underline;"
            "}"
            "QPushButton:hover { text-decoration: none; }"
        )
        label_widget.clicked.connect(lambda _checked=False, target=info_target: on_info_target_requested(target))
    else:
        label_widget = QLabel(f"({match_count}) {label}")
        label_widget.setStyleSheet(
            f"color: rgb({similarity_red}, {similarity_green}, {similarity_blue});"
        )

    label_widget.setWordWrap(True)
    label_font = label_widget.font()
    label_font.setPointSize(max(1, label_font.pointSize() - 1))
    label_widget.setFont(label_font)
    top_layout.addWidget(label_widget, stretch=1)

    percent_bar = QProgressBar()
    percent_bar.setRange(0, 100)
    percent_bar.setValue(percent_value)
    percent_bar.setTextVisible(False)
    percent_bar.setFixedWidth(120)
    percent_bar.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    top_layout.addWidget(percent_bar, stretch=0, alignment=Qt.AlignRight)
    row_layout.addWidget(top_row)

    unknown_suffix = ""
    if selection_total_count > 0 and total_count < selection_total_count:
        unknown_count = selection_total_count - total_count
        unknown_percent_value = int(round((unknown_count / selection_total_count) * 100))
        unknown_suffix = f" | {unknown_percent_value}% unknown"

    tiny_label = QLabel(
        f"{percent_value}% of selection | {db_percent_value}% of DB{unknown_suffix}"
    )
    tiny_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    tiny_label.setStyleSheet("color: #9f9f9f; font-size: 8px;")
    row_layout.addWidget(tiny_label, stretch=0, alignment=Qt.AlignLeft)

    section_list.addItem(item)
    row_height = max(row_widget.sizeHint().height() + 6, 32)
    item.setSizeHint(QSize(0, row_height))
    section_list.setItemWidget(item, row_widget)
