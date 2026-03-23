"""Animated loading overlay for Chart View."""

from __future__ import annotations

import math

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QWidget


class ChartLoadingOverlay(QWidget):
    """Animated loading overlay displayed above the natal chart canvas."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        dim_alpha: int = 102,
    ) -> None:
        super().__init__(parent)
        self._spin_angle = 0.0
        self._dim_alpha = max(0, min(255, int(dim_alpha)))
        self._timer = QTimer(self)
        self._timer.setInterval(75)
        self._timer.timeout.connect(self._advance_spinner)
        self.hide()

    def start(self) -> None:
        self._spin_angle = 0.0
        self.show()
        self.raise_()
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def stop(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        self.hide()

    def _advance_spinner(self) -> None:
        self._spin_angle = (self._spin_angle + 14.0) % 360.0
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.isVisible():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.fillRect(self.rect(), QColor(8, 8, 12, self._dim_alpha))

        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        min_dim = max(1.0, float(min(self.width(), self.height())))
        emoji_font_size = int(max(54, min(180, min_dim * 0.22)))
        ring_font_size = int(max(18, min(54, min_dim * 0.085)))
        ring_radius = max(70.0, min_dim * 0.21)

        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self._spin_angle)
        swirl_font = QFont(self.font())
        swirl_font.setPointSize(emoji_font_size)
        painter.setFont(swirl_font)
        painter.setPen(QColor(255, 255, 255, 153))
        painter.drawText(
            -emoji_font_size,
            int(emoji_font_size * 0.45),
            "🌀",
        )
        painter.restore()

        orbit_radius = ring_radius * 0.72
        orbit_angle = math.radians(self._spin_angle * 2.0)
        orbit_x = center_x + (orbit_radius * math.cos(orbit_angle))
        orbit_y = center_y + (orbit_radius * math.sin(orbit_angle))
        orbit_font = QFont(self.font())
        orbit_font.setPointSize(max(20, int(ring_font_size * 1.15)))
        painter.setFont(orbit_font)
        painter.setPen(QColor("#f1c7ff"))
        painter.drawText(int(orbit_x), int(orbit_y), "✦")

        loading_text = "Loading★Loading✬Loading𖤐"
        ring_font = QFont(self.font())
        ring_font.setBold(True)
        ring_font.setPointSize(max(16, ring_font_size - 2))
        painter.setFont(ring_font)
        painter.setPen(QColor("#c000ff"))
        step_degrees = 360.0 / max(1, len(loading_text))
        for index, letter in enumerate(loading_text):
            angle_deg = self._spin_angle + (index * step_degrees)
            angle_rad = math.radians(angle_deg)
            x = center_x + (ring_radius * math.cos(angle_rad))
            y = center_y + (ring_radius * math.sin(angle_rad))
            fm = QFontMetrics(ring_font)
            text_width = fm.horizontalAdvance(letter)
            text_height = fm.height()
            painter.drawText(
                int(x - (text_width / 2)),
                int(y + (text_height / 3)),
                letter,
            )
