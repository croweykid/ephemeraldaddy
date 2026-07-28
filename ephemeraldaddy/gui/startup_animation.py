"""Dependency-light shared renderer for startup animation surfaces."""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class StartupAnimationFrame(QWidget):
    """Animated frame painted directly into the startup widget background."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
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

    def stop(self) -> None:
        self._wave_timer.stop()

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

        def top_point(x: float) -> QPointF:
            return QPointF(
                x,
                rect.top()
                + math.sin((x / self._wave_length) + self._wave_phase)
                * self._wave_amplitude,
            )

        def right_point(y: float) -> QPointF:
            return QPointF(
                rect.right()
                + math.sin((y / self._wave_length) + self._wave_phase)
                * self._wave_amplitude,
                y,
            )

        def bottom_point(x: float) -> QPointF:
            return QPointF(
                x,
                rect.bottom()
                + math.sin((x / self._wave_length) + self._wave_phase + math.pi)
                * self._wave_amplitude,
            )

        def left_point(y: float) -> QPointF:
            return QPointF(
                rect.left()
                + math.sin((y / self._wave_length) + self._wave_phase + math.pi)
                * self._wave_amplitude,
                y,
            )

        path = QPainterPath(top_point(rect.left()))
        x = rect.left() + step
        while x < rect.right():
            path.lineTo(top_point(x))
            x += step
        path.lineTo(top_point(rect.right()))

        y = rect.top() + step
        while y < rect.bottom():
            path.lineTo(right_point(y))
            y += step
        path.lineTo(right_point(rect.bottom()))

        x = rect.right() - step
        while x > rect.left():
            path.lineTo(bottom_point(x))
            x -= step
        path.lineTo(bottom_point(rect.left()))

        y = rect.bottom() - step
        while y > rect.top():
            path.lineTo(left_point(y))
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
        border_pen = QPen(QColor("#aa77ff"), 1.8)
        border_pen.setJoinStyle(Qt.RoundJoin)
        border_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(border_pen)
        painter.drawPath(wave_path)

