"""Separate-process animated startup frame shown behind the load bar."""

from __future__ import annotations

import math
import random
import sys

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QWidget


class StartupAnimationWindow(QWidget):
    """Animated companion window rendered in a separate process."""

    def __init__(self, *, x: int, y: int, width: int, height: int) -> None:
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowFlag(Qt.WindowStaysOnBottomHint, True)
        self.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
        self.setGeometry(x, y, width, height)

        self._wave_phase = 0.0
        self._wave_amplitude = 4.0
        self._wave_length = 28.0
        self._edge_padding = 10.0
        self._star_particles = self._create_star_particles(count=24)

        self._wave_timer = QTimer(self)
        self._wave_timer.setInterval(33)
        self._wave_timer.timeout.connect(self._advance_wave_animation)
        self._wave_timer.start()

    def _advance_wave_animation(self) -> None:
        self._wave_phase = (self._wave_phase + 0.35) % (2.0 * math.pi)
        self.update()

    def _create_star_particles(
        self, *, count: int
    ) -> list[tuple[float, float, float, float]]:
        rng = random.Random(7331)
        particles: list[tuple[float, float, float, float]] = []
        for _ in range(count):
            particles.append(
                (
                    rng.uniform(0.08, 0.92),
                    rng.uniform(0.12, 0.88),
                    rng.uniform(0.0, 2.0 * math.pi),
                    rng.uniform(0.7, 1.35),
                )
            )
        return particles

    def _draw_starburst_particles(self, painter: QPainter, rect: QRectF) -> None:
        for x_norm, y_norm, phase_offset, size_mult in self._star_particles:
            sparkle_wave = (self._wave_phase * 1.8) + phase_offset
            sparkle_strength = (math.sin(sparkle_wave) + 1.0) / 2.0
            if sparkle_strength < 0.38:
                continue
            alpha = int(85 + (sparkle_strength * 160))
            radius = (0.9 + sparkle_strength * 1.8) * size_mult
            center = QPointF(
                rect.left() + (rect.width() * x_norm),
                rect.top() + (rect.height() * y_norm),
            )
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(243, 230, 255, alpha))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(QColor(206, 169, 255, min(alpha + 20, 255)), 1.0))
            painter.drawLine(
                QPointF(center.x() - (radius * 2.0), center.y()),
                QPointF(center.x() + (radius * 2.0), center.y()),
            )
            painter.drawLine(
                QPointF(center.x(), center.y() - (radius * 2.0)),
                QPointF(center.x(), center.y() + (radius * 2.0)),
            )

    def _build_wavy_rect_path(self, rect: QRectF) -> QPainterPath:
        step = 4.0
        path = QPainterPath()
        path.moveTo(rect.left(), rect.top())
        x = rect.left()
        while x <= rect.right():
            y = rect.top() + math.sin((x / self._wave_length) + self._wave_phase) * self._wave_amplitude
            path.lineTo(QPointF(x, y))
            x += step
        y = rect.top()
        while y <= rect.bottom():
            x = rect.right() + math.sin((y / self._wave_length) + self._wave_phase) * self._wave_amplitude
            path.lineTo(QPointF(x, y))
            y += step
        x = rect.right()
        while x >= rect.left():
            y = rect.bottom() + math.sin((x / self._wave_length) + self._wave_phase + math.pi) * self._wave_amplitude
            path.lineTo(QPointF(x, y))
            x -= step
        y = rect.bottom()
        while y >= rect.top():
            x = rect.left() + math.sin((y / self._wave_length) + self._wave_phase + math.pi) * self._wave_amplitude
            path.lineTo(QPointF(x, y))
            y -= step
        path.closeSubpath()
        return path

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        outer_rect = self.rect().adjusted(3, 3, -3, -3)
        content_rect = QRectF(
            outer_rect.left() + self._edge_padding,
            outer_rect.top() + self._edge_padding,
            outer_rect.width() - (self._edge_padding * 2.0),
            outer_rect.height() - (self._edge_padding * 2.0),
        )
        wave_path = self._build_wavy_rect_path(content_rect)
        painter.fillPath(wave_path, QColor("#141218"))
        painter.save()
        painter.setClipPath(wave_path)
        self._draw_starburst_particles(painter, content_rect)
        painter.restore()
        painter.setPen(QPen(QColor("#aa77ff"), 1.5))
        painter.drawPath(wave_path)


def main() -> int:
    if len(sys.argv) != 5:
        return 1
    try:
        x, y, width, height = (int(arg) for arg in sys.argv[1:])
    except ValueError:
        return 1
    app = QApplication([])
    window = StartupAnimationWindow(x=x, y=y, width=width, height=height)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
