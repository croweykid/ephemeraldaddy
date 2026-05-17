"""Database View info-panel helpers for similarities analytics."""

from __future__ import annotations

import math
from typing import Callable

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QSizePolicy,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from ephemeraldaddy.gui.style import DATABASE_VIEW_PANEL_HEADER_STYLE


from ephemeraldaddy.gui.features.charts.similarities_db_norm import (
    SIMILARITY_DELTA_MIN_GUIDE_SAMPLE_SIZE,
    similarity_delta_points,
    similarity_deviation_z_score,
)


class SimilarityPercentBar(QProgressBar):
    """Centered DB-norm gauge with a selection overlay and SE guide lines."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._standard_deviation_guides: tuple[tuple[float, int], ...] = ()
        self._norm_delta_overlay: (
            tuple[float, float, tuple[int, int, int]] | None
        ) = None

    def set_norm_delta_overlay(
        self,
        *,
        selection_percent: int | float,
        db_norm_percent: int | float,
        delta_rgb: tuple[int, int, int],
    ) -> None:
        """Set the selected-vs-DB-norm delta overlay for the progress bar.

        ``selection_percent`` is the row's filled progress value, while
        ``db_norm_percent`` is the baseline percentage for the full database.
        The overlay paints the signed distance between those two percentages so
        below-norm rows remain visually distinct from above-norm rows.
        """
        selection_value = float(selection_percent)
        db_norm_value = float(db_norm_percent)
        if not math.isfinite(selection_value) or not math.isfinite(db_norm_value):
            self._norm_delta_overlay = None
            self.update()
            return

        normalized_rgb = tuple(
            max(0, min(255, int(channel))) for channel in delta_rgb
        )
        self._norm_delta_overlay = (
            max(0.0, min(100.0, selection_value)),
            max(0.0, min(100.0, db_norm_value)),
            normalized_rgb,
        )
        self.update()

    def set_standard_deviation_guides(
        self,
        guide_percents: list[tuple[float, int]],
    ) -> None:
        self._standard_deviation_guides = tuple(
            (max(0.0, min(100.0, float(value))), max(0, min(255, int(alpha))))
            for value, alpha in guide_percents
            if math.isfinite(float(value))
        )
        self.update()

    @staticmethod
    def _centered_axis_span_percent(
        selection_percent: float,
        db_norm_percent: float,
        guide_percents: tuple[tuple[float, int], ...],
    ) -> float:
        distances = [abs(selection_percent - db_norm_percent), 1.0]
        distances.extend(
            abs(guide_percent - db_norm_percent)
            for guide_percent, _ in guide_percents
        )
        return min(100.0, max(distances) * 1.15)

    @staticmethod
    def _centered_percent_x(
        *,
        content_left: int,
        content_width: int,
        percent_value: float,
        db_norm_percent: float,
        axis_span_percent: float,
    ) -> int:
        center_x = content_left + round(content_width / 2.0)
        half_width = content_width / 2.0
        if axis_span_percent <= 0.0:
            return center_x
        normalized_delta = (percent_value - db_norm_percent) / axis_span_percent
        normalized_delta = max(-1.0, min(1.0, normalized_delta))
        return center_x + round(normalized_delta * half_width)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing, False)
            content_rect = self.rect().adjusted(2, 2, -2, -2)
            if content_rect.width() <= 0 or content_rect.height() <= 0:
                return

            painter.fillRect(content_rect, QColor(38, 38, 38, 235))
            border_pen = QPen(QColor(115, 115, 115, 180))
            border_pen.setWidth(1)
            painter.setPen(border_pen)
            painter.drawRect(content_rect)

            center_x = content_rect.left() + round(content_rect.width() / 2.0)
            midline_pen = QPen(QColor(95, 95, 95, 150))
            midline_pen.setWidth(1)
            painter.setPen(midline_pen)
            painter.drawLine(
                center_x, content_rect.top(), center_x, content_rect.bottom()
            )

            if self._norm_delta_overlay:
                selection_percent, db_norm_percent, delta_rgb = self._norm_delta_overlay
                axis_span_percent = self._centered_axis_span_percent(
                    selection_percent,
                    db_norm_percent,
                    self._standard_deviation_guides,
                )
                selection_x = self._centered_percent_x(
                    content_left=content_rect.left(),
                    content_width=content_rect.width(),
                    percent_value=selection_percent,
                    db_norm_percent=db_norm_percent,
                    axis_span_percent=axis_span_percent,
                )
                delta_left = min(selection_x, center_x)
                delta_width = max(1, abs(selection_x - center_x))
                painter.fillRect(
                    delta_left,
                    content_rect.top(),
                    delta_width,
                    content_rect.height(),
                    QColor(127, 255, 0, 74),
                )

                norm_pen = QPen(QColor(230, 230, 230, 210))
                norm_pen.setWidth(2)
                painter.setPen(norm_pen)
                painter.drawLine(
                    center_x, content_rect.top(), center_x, content_rect.bottom()
                )

                selection_pen = QPen(QColor(*delta_rgb, 235))
                selection_pen.setWidth(2)
                painter.setPen(selection_pen)
                painter.drawLine(
                    selection_x, content_rect.top(), selection_x, content_rect.bottom()
                )
            else:
                db_norm_percent = 50.0
                axis_span_percent = 50.0

            unique_guides = sorted(
                set(
                    (round(value, 4), alpha)
                    for value, alpha in self._standard_deviation_guides
                )
            )
            for guide_percent, alpha in unique_guides:
                color = QColor(255, 45, 45, alpha)
                pen = QPen(color)
                pen.setWidth(1)
                painter.setPen(pen)
                x = self._centered_percent_x(
                    content_left=content_rect.left(),
                    content_width=content_rect.width(),
                    percent_value=guide_percent,
                    db_norm_percent=db_norm_percent,
                    axis_span_percent=axis_span_percent,
                )
                painter.drawLine(x, content_rect.top(), x, content_rect.bottom())
        finally:
            painter.end()


def _standard_error_guide_percents(
    *,
    db_percent_value: int,
    total_count: int,
    show_standard_deviation_guides: bool,
) -> list[tuple[float, int]]:
    if (
        not show_standard_deviation_guides
        or total_count < SIMILARITY_DELTA_MIN_GUIDE_SAMPLE_SIZE
    ):
        return []
    probability = max(0.0, min(1.0, float(db_percent_value) / 100.0))
    standard_error_percent = (
        math.sqrt(probability * (1.0 - probability) / float(total_count)) * 100.0
    )
    if standard_error_percent <= 0.0 or not math.isfinite(standard_error_percent):
        return []
    guides: list[tuple[float, int]] = []
    for multiplier in (1, 2):
        offset = standard_error_percent * multiplier
        alpha = 220 if multiplier == 1 else 145
        for guide in (
            float(db_percent_value) - offset,
            float(db_percent_value) + offset,
        ):
            if 0.0 <= guide <= 100.0:
                guides.append((guide, alpha))
    return guides


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
        self.title_label.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
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
    show_standard_deviation_guides: bool = True,
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
        label_widget = QLabel()
        label_widget.setText(
            f'<a href="{info_target}" style="color: rgb({similarity_red}, {similarity_green}, {similarity_blue});">'
            f"({match_count}) {label}"
            "</a>"
        )
        label_widget.setTextFormat(Qt.RichText)
        label_widget.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label_widget.setOpenExternalLinks(False)
        label_widget.setCursor(Qt.PointingHandCursor)
        label_widget.linkActivated.connect(on_info_target_requested)
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

    percent_bar = SimilarityPercentBar()
    percent_bar.setRange(0, 100)
    percent_bar.setValue(percent_value)
    percent_bar.setTextVisible(False)
    percent_bar.setFixedWidth(120)
    percent_bar.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    percent_bar.set_norm_delta_overlay(
        selection_percent=percent_value,
        db_norm_percent=db_percent_value,
        delta_rgb=similarity_rgb,
    )
    delta_points = similarity_delta_points(percent_value, db_percent_value)
    z_score = (
        similarity_deviation_z_score(percent_value, db_percent_value, total_count)
        if total_count >= SIMILARITY_DELTA_MIN_GUIDE_SAMPLE_SIZE
        else None
    )
    direction_label = (
        "above DB norm"
        if delta_points > 0
        else "below DB norm" if delta_points < 0 else "at DB norm"
    )
    if total_count < SIMILARITY_DELTA_MIN_GUIDE_SAMPLE_SIZE:
        z_score_text = (
            f" Sample size n={total_count} is too small for reliable standard-error "
            "guide marks, so the guides are hidden."
        )
    else:
        z_score_text = (
            ""
            if z_score is None
            else f" ({z_score:+.2f} standard-error units)"
        )
    percent_bar.setToolTip(
        f"Database norm is centered; the green selection rectangle extends "
        f"{abs(delta_points):.0f}% pt(s) {direction_label}.{z_score_text}"
    )
    percent_bar.set_standard_deviation_guides(
        _standard_error_guide_percents(
            db_percent_value=db_percent_value,
            total_count=total_count,
            show_standard_deviation_guides=show_standard_deviation_guides,
        )
    )
    top_layout.addWidget(percent_bar, stretch=0, alignment=Qt.AlignRight)
    row_layout.addWidget(top_row)

    unknown_suffix = ""
    if selection_total_count > 0 and total_count < selection_total_count:
        unknown_count = selection_total_count - total_count
        unknown_percent_value = int(
            round((unknown_count / selection_total_count) * 100)
        )
        unknown_suffix = f" | {unknown_percent_value}% unknown"

    selection_percent_text = f"{percent_value}% of selection"
    delta_suffix = ""
    if delta_points != 0.0:
        delta_suffix = f" | {delta_points:+.0f}% pts {direction_label}"
    if total_count < SIMILARITY_DELTA_MIN_GUIDE_SAMPLE_SIZE:
        delta_suffix += " | n too small for SE"
    if percent_value < db_percent_value:
        selection_percent_text = (
            f'<span style="color: #ff2d2d;">{selection_percent_text}</span>'
        )
    elif percent_value > db_percent_value:
        selection_percent_text = (
            f'<span style="color: #7fff00;">{selection_percent_text}</span>'
        )

    tiny_label = QLabel(
        f"{selection_percent_text} | {db_percent_value}% of DB{delta_suffix}{unknown_suffix}"
    )
    tiny_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    tiny_label.setTextFormat(Qt.RichText)
    tiny_label.setStyleSheet("color: #9f9f9f; font-size: 8px;")
    row_layout.addWidget(tiny_label, stretch=0, alignment=Qt.AlignLeft)

    section_list.addItem(item)
    row_height = max(row_widget.sizeHint().height() + 6, 32)
    item.setSizeHint(QSize(0, row_height))
    section_list.setItemWidget(item, row_widget)
