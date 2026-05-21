"""Transient sparkle trail shown after closing the About window."""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class AboutCloseSparkleOverlay(QWidget):
    """Top-level transparent overlay that renders a short sparkle burst."""

    def __init__(self, target_rect: QRect, *, duration_ms: int = 1000) -> None:
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.NoFocus)
        self.setGeometry(target_rect)

        self._duration_ms = max(200, duration_ms)
        self._elapsed_ms = 0
        self._tick_ms = 33
        self._rng = random.Random(814)
        self._particles = self._create_particles(count=34)

        self._timer = QTimer(self)
        self._timer.setInterval(self._tick_ms)
        self._timer.timeout.connect(self._advance)

    def _create_particles(self, *, count: int) -> list[dict[str, float]]:
        particles: list[dict[str, float]] = []
        center_x = self.width() * 0.5
        center_y = self.height() * 0.5
        for _ in range(count):
            angle = self._rng.uniform(0.0, math.tau)
            speed = self._rng.uniform(20.0, 95.0)
            particles.append(
                {
                    "x": center_x + self._rng.uniform(-20.0, 20.0),
                    "y": center_y + self._rng.uniform(-10.0, 10.0),
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "size": self._rng.uniform(1.0, 2.8),
                    "phase": self._rng.uniform(0.0, math.tau),
                }
            )
        return particles

    def start(self) -> None:
        self.show()
        self.raise_()
        self._timer.start()

    def _advance(self) -> None:
        self._elapsed_ms += self._tick_ms
        t = self._tick_ms / 1000.0
        for p in self._particles:
            p["x"] += p["vx"] * t
            p["y"] += p["vy"] * t
            p["vx"] *= 0.94
            p["vy"] *= 0.94
        if self._elapsed_ms >= self._duration_ms:
            self._timer.stop()
            self.close()
            self.deleteLater()
            return
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        progress = min(max(self._elapsed_ms / self._duration_ms, 0.0), 1.0)
        fade = 1.0 - progress

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        for p in self._particles:
            pulse = (math.sin((progress * 8.0) + p["phase"]) + 1.0) * 0.5
            alpha = int((55 + (200 * pulse)) * fade)
            if alpha <= 0:
                continue
            radius = p["size"] * (0.8 + pulse * 0.75)
            center = QPointF(p["x"], p["y"])
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(241, 222, 255, alpha))
            painter.drawEllipse(center, radius, radius)
            cross_alpha = max(0, min(255, alpha + 28))
            painter.setPen(QPen(QColor(208, 165, 255, cross_alpha), 1.0))
            span = radius * 2.0
            painter.drawLine(QPointF(center.x() - span, center.y()), QPointF(center.x() + span, center.y()))
            painter.drawLine(QPointF(center.x(), center.y() - span), QPointF(center.x(), center.y() + span))
