"""Shared startup/loading UI primitives for GUI entrypoints."""

from __future__ import annotations

import math
import random
from typing import Protocol, runtime_checkable

from PySide6.QtCore import QCoreApplication, QEventLoop, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QProgressBar, QStyle, QStyleOptionProgressBar, QVBoxLayout, QWidget

from ephemeraldaddy.gui.style import DATABASE_VIEW_PANEL_HEADER_STYLE


@runtime_checkable
class StartupProgress(Protocol):
    """Protocol used by the startup cockpit to report launch progress."""

    def show(self) -> None: ...

    def close(self) -> None: ...

    def update_status(self, message: str, progress: int) -> None: ...


class _StartupAnimationBackground(QWidget):
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


class _SparkleProgressBar(QProgressBar):
    """Progress bar that keeps the launch sparkle layer visible above the chunk."""

    def __init__(self) -> None:
        super().__init__()
        self._sparkle_phase = 0.0
        self._sparkle_timer = QTimer(self)
        self._sparkle_timer.setInterval(45)
        self._sparkle_timer.timeout.connect(self._advance_sparkles)
        self._sparkle_timer.start()

    def _advance_sparkles(self) -> None:
        self._sparkle_phase = (self._sparkle_phase + 0.28) % (2.0 * math.pi)
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)
        if self.maximum() <= self.minimum():
            return

        option = QStyleOptionProgressBar()
        self.initStyleOption(option)
        groove = self.style().subElementRect(
            QStyle.SE_ProgressBarGroove, option, self
        )
        fill_ratio = (self.value() - self.minimum()) / (self.maximum() - self.minimum())
        fill_width = max(0.0, groove.width() * min(max(fill_ratio, 0.0), 1.0))
        if fill_width < 8.0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setClipRect(
            QRectF(groove.left(), groove.top(), fill_width, groove.height())
        )
        sparkle_count = 7
        for index in range(sparkle_count):
            phase = self._sparkle_phase + (index * 1.17)
            x = groove.left() + ((index + 0.6) / sparkle_count) * fill_width
            y = groove.center().y() + math.sin(phase * 1.4) * (groove.height() * 0.22)
            strength = (math.sin(phase) + 1.0) / 2.0
            alpha = int(90 + strength * 150)
            radius = 1.0 + strength * 1.5
            center = QPointF(x, y)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 244, 210, alpha))
            painter.drawEllipse(center, radius, radius)
            painter.setPen(QPen(QColor(255, 255, 255, min(alpha + 20, 255)), 1.0))
            painter.drawLine(
                QPointF(x - radius * 2.2, y), QPointF(x + radius * 2.2, y)
            )
            painter.drawLine(
                QPointF(x, y - radius * 2.2), QPointF(x, y + radius * 2.2)
            )


class StartupLoadingWidget(QWidget):
    """Small splash-like loading surface shown while the app initializes."""

    _BACKGROUND_SCALE = 1.25
    _FOREGROUND_WIDTH = 360

    def __init__(self) -> None:
        # Use splash-screen window semantics to avoid OS-level "tool window"
        # taskbar/alt-tab flashing during startup (especially noticeable on Windows).
        super().__init__(None, Qt.SplashScreen | Qt.FramelessWindowHint)
        self.setWindowTitle("Starting EphemeralDaddy")
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._background_animation = _StartupAnimationBackground(self)
        self._background_animation.lower()

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setAlignment(Qt.AlignCenter)
        self.setLayout(root_layout)

        foreground = QWidget(self)
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)
        foreground.setLayout(layout)
        foreground.setFixedWidth(self._FOREGROUND_WIDTH)
        root_layout.addWidget(foreground, alignment=Qt.AlignCenter)

        title = QLabel("Ephemeral Daddy will be with you shortly…")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setStyleSheet(DATABASE_VIEW_PANEL_HEADER_STYLE)
        layout.addWidget(title)

        self._status_label = QLabel("...hold your horses while we get all pretty…")
        self._status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._status_label.setStyleSheet("color: #efe9ff; font-size: 12px;")
        layout.addWidget(self._status_label)

        self._progress = _SparkleProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(5)
        self._progress.setStyleSheet(
            "QProgressBar {"
            "  border: 1px solid #47345d;"
            "  border-radius: 4px;"
            "  color: #efe9ff;"
            "  background-color: #0e0b12;"
            "  text-align: center;"
            "  min-height: 14px;"
            "}"
            "QProgressBar::chunk {"
            "  background-color: #9933ff;"
            "}"
        )
        layout.addWidget(self._progress)

        foreground.adjustSize()
        background_width = math.ceil(foreground.width() * self._BACKGROUND_SCALE)
        background_height = math.ceil(foreground.height() * self._BACKGROUND_SCALE)
        self.setFixedSize(background_width, background_height)
        self._center_on_primary_screen()
        self._background_animation.setGeometry(self.rect())

    def _center_on_primary_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        screen_rect = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(screen_rect.center())
        self.move(frame.topLeft())

    def update_status(self, message: str, progress: int) -> None:
        self._status_label.setText(message)
        self._progress.setValue(min(max(progress, 0), 100))
        self.raise_()
        QCoreApplication.processEvents(QEventLoop.AllEvents, 50)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._background_animation.setGeometry(self.rect())
        self.raise_()
        QCoreApplication.processEvents(QEventLoop.AllEvents, 50)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._background_animation.setGeometry(self.rect())

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._background_animation.stop()
        super().closeEvent(event)

    def shutdown(self) -> None:
        self._background_animation.stop()
        self.close()
        self.deleteLater()