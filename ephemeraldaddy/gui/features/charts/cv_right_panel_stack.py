"""Chart View right-panel stack helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


@dataclass
class ChartRightPanelStack:
    """Container + controls used by Chart View's right-side panel stack."""

    container: QWidget
    analytics_button: QPushButton
    subjective_notes_button: QPushButton
    stack: QStackedWidget
    analytics_scroll: QScrollArea
    subjective_notes_scroll: QScrollArea


def build_chart_right_panel_stack(
    *,
    analytics_content_widget: QWidget,
    subjective_notes_content_widget: QWidget,
    on_show_analytics: Callable[[], None],
    on_show_subjective_notes: Callable[[], None],
    scrollbar_style: str,
) -> ChartRightPanelStack:
    """Build the Chart View right panel with analytics/subjective notes toggle."""
    container = QWidget()
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    container.setLayout(layout)
    container.setMinimumWidth(200)

    analytics_button = QPushButton("📊")
    analytics_button.setObjectName("chart_view_toggle_analytics_panel_button")
    analytics_button.clicked.connect(on_show_analytics)
    subjective_notes_button = QPushButton("💭")
    subjective_notes_button.setObjectName("chart_view_toggle_subjective_notes_panel_button")
    subjective_notes_button.clicked.connect(on_show_subjective_notes)

    for control_button in (analytics_button, subjective_notes_button):
        control_button.setCheckable(True)
        control_button.setAutoDefault(False)
        control_button.setDefault(False)
        control_button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        control_button.setMinimumWidth(0)
        control_button.setStyleSheet("padding: 1px 5px; font-size: 11px;")

    controls_row = QWidget()
    controls_layout = QHBoxLayout()
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setSpacing(4)
    controls_row.setLayout(controls_layout)
    controls_layout.addWidget(analytics_button)
    controls_layout.addWidget(subjective_notes_button)
    controls_layout.addStretch(1)
    layout.addWidget(controls_row)

    stack = QStackedWidget()
    stack.setMinimumWidth(0)
    layout.addWidget(stack, 1)

    analytics_scroll = QScrollArea()
    analytics_scroll.setWidgetResizable(True)
    analytics_scroll.setFrameShape(QScrollArea.NoFrame)
    analytics_scroll.setMinimumWidth(240)
    analytics_scroll.setStyleSheet(scrollbar_style)
    analytics_scroll.setFocusPolicy(Qt.StrongFocus)
    analytics_scroll.setWidget(analytics_content_widget)
    stack.addWidget(analytics_scroll)

    subjective_notes_scroll = QScrollArea()
    subjective_notes_scroll.setWidgetResizable(True)
    subjective_notes_scroll.setFrameShape(QScrollArea.NoFrame)
    subjective_notes_scroll.setMinimumWidth(240)
    subjective_notes_scroll.setStyleSheet(scrollbar_style)
    subjective_notes_scroll.setFocusPolicy(Qt.StrongFocus)
    subjective_notes_scroll.setWidget(subjective_notes_content_widget)
    stack.addWidget(subjective_notes_scroll)

    return ChartRightPanelStack(
        container=container,
        analytics_button=analytics_button,
        subjective_notes_button=subjective_notes_button,
        stack=stack,
        analytics_scroll=analytics_scroll,
        subjective_notes_scroll=subjective_notes_scroll,
    )
