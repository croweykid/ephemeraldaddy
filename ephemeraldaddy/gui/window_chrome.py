from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ephemeraldaddy.gui.about import ABOUT_ONBOARDING_MARKDOWN
from ephemeraldaddy.gui.about_sparkle import AboutCloseSparkleOverlay
from ephemeraldaddy.gui.style import (
    ABOUT_DIALOG_ACCENT_BUTTON_COLOR,
    ABOUT_DIALOG_INTRO_STYLE,
    ABOUT_DIALOG_MARKDOWN_STYLESHEET,
    WINDOW_CHROME_MENU_STYLE,
)

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication, QLayout, QMainWindow, QWidget

APP_DISPLAY_NAME = "Ephemeral Daddy"


_ACTIVE_ABOUT_SPARKLES: list[AboutCloseSparkleOverlay] = []


def _show_about_close_sparkles(target_rect) -> None:
    overlay = AboutCloseSparkleOverlay(target_rect, duration_ms=1000)
    _ACTIVE_ABOUT_SPARKLES.append(overlay)

    def _cleanup(*_args) -> None:
        if overlay in _ACTIVE_ABOUT_SPARKLES:
            _ACTIVE_ABOUT_SPARKLES.remove(overlay)

    overlay.destroyed.connect(_cleanup)
    overlay.start()


def _resolve_current_chart_name(window: "QWidget") -> str:
    latest_chart = getattr(window, "_latest_chart", None)
    latest_name = getattr(latest_chart, "name", None)
    if isinstance(latest_name, str) and latest_name.strip():
        return latest_name.strip()

    name_edit = getattr(window, "name_edit", None)
    if name_edit is not None:
        text = getattr(name_edit, "text", None)
        if callable(text):
            value = text()
            if isinstance(value, str) and value.strip():
                return value.strip()
    return "No chart selected"


def update_main_window_title(window: "QMainWindow") -> None:
    chart_name = _resolve_current_chart_name(window)
    window.setWindowTitle(f"{APP_DISPLAY_NAME} | Natal Chart of {chart_name}")


def _bind_menu_action(menu, label: str, window: "QWidget", *handler_names: str) -> None:
    """Attach a menu action to the first available window handler.

    This keeps startup resilient across builds where a handler may have moved
    or been renamed.
    """

    handler: Callable[..., Any] | None = None
    for name in handler_names:
        candidate = getattr(window, name, None)
        if callable(candidate):
            handler = candidate
            break

    if handler is None:
        action = menu.addAction(label)
        action.setEnabled(False)
        return

    menu.addAction(label, handler)


def _add_preferences_submenu(app_menu, owner: "QWidget") -> None:
    """Attach the Preferences submenu and known preference actions."""
    preferences_menu = app_menu.addMenu("Preferences")
    _bind_menu_action(
        preferences_menu,
        "Settings",
        owner,
        "_on_open_settings",
        "on_open_settings",
    )


def _configure_menu_bar_visibility(menu_bar) -> None:
    """Prefer native menu positioning; allow opt-in in-window menu bars on macOS."""
    if (
        sys.platform == "darwin"
        and not getattr(sys, "frozen", False)
        and os.environ.get("EPHEMERALDADDY_FORCE_IN_WINDOW_MENUBAR") == "1"
    ):
        menu_bar.setNativeMenuBar(False)

def _is_human_design_menu_enabled(owner: "QWidget") -> bool:
    visibility_store = getattr(owner, "_visibility", None)
    if visibility_store is None:
        return False
    get_visibility = getattr(visibility_store, "get", None)
    if not callable(get_visibility):
        return False
    return bool(get_visibility("chart_data.human_design_alpha_prototype"))


def _show_about_from_onboarding(owner: "QWidget") -> None:
    """Show About dialog content bundled directly into the app binary."""
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTextBrowser, QVBoxLayout

    title = f"About {APP_DISPLAY_NAME}"

    content = ABOUT_ONBOARDING_MARKDOWN.strip()
    if not content:
        content = "About content is unavailable."

    def _apply_inline_markdown_formatting(text: str) -> str:
        formatted = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        formatted = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", formatted)
        return formatted

    styled_content_lines: list[str] = []
    for line in content.splitlines():
        stripped = line.lstrip()
        prefix_whitespace = line[: len(line) - len(stripped)]
        if not stripped:
            styled_content_lines.append("")
            continue
        if stripped.startswith("### "):
            heading_text = stripped[4:].strip()
            if heading_text.startswith("**") and heading_text.endswith("**"):
                heading_text = heading_text[2:-2].strip()
            heading_text = _apply_inline_markdown_formatting(heading_text)
            if heading_text.startswith("Q."):
                styled_content_lines.append(
                    f"{prefix_whitespace}<h3 class='about-question'>{heading_text}</h3>"
                )
            elif heading_text.startswith("A."):
                styled_content_lines.append(
                    f"{prefix_whitespace}<h3 class='about-answer'>{heading_text}</h3>"
                )
            else:
                styled_content_lines.append(
                    f"{prefix_whitespace}<h3 class='about-subheader'>{heading_text}</h3>"
                )
        elif stripped.startswith("## "):
            heading_text = stripped[3:].strip()
            heading_text = _apply_inline_markdown_formatting(heading_text)
            is_major_header = bool(
                re.match(r"^\d+\)", heading_text)
                or heading_text.lower().startswith("faq")
                or heading_text == "Final Takeaways"
            )
            heading_class = "about-major-header" if is_major_header else "about-subheader"
            styled_content_lines.append(
                f"{prefix_whitespace}<h2 class='{heading_class}'>{heading_text}</h2>"
            )
        elif stripped.startswith("#### "):
            heading_text = stripped[5:].strip()
            heading_text = _apply_inline_markdown_formatting(heading_text)
            styled_content_lines.append(
                f"{prefix_whitespace}<h4 class='about-subheader'>{heading_text}</h4>"
            )
        elif stripped.startswith("Q."):
            styled_content_lines.append(
                f"{prefix_whitespace}<span class='about-question'>{_apply_inline_markdown_formatting(stripped)}</span><br/>"
            )
        elif stripped.startswith("A."):
            styled_content_lines.append(
                f"{prefix_whitespace}<span class='about-answer'>{_apply_inline_markdown_formatting(stripped)}</span><br/>"
            )
        else:
            styled_content_lines.append(f"{_apply_inline_markdown_formatting(line)}<br/>")
    styled_content = "\n".join(styled_content_lines)

    dialog = QDialog(owner)
    dialog.setModal(False)
    dialog.setWindowTitle(title)
    dialog.resize(720, 560)

    layout = QVBoxLayout(dialog)
    intro = QLabel("This is not my beautiful house. This is not my beautiful wife. My god. How did I get here?")
    intro.setStyleSheet(ABOUT_DIALOG_INTRO_STYLE)
    layout.addWidget(intro)

    content_view = QTextBrowser(dialog)
    content_view.setOpenExternalLinks(True)
    content_view.document().setDefaultStyleSheet(ABOUT_DIALOG_MARKDOWN_STYLESHEET)
    content_view.setHtml(styled_content)
    layout.addWidget(content_view, 1)

    buttons = QDialogButtonBox(parent=dialog)
    groovy_button = buttons.addButton("Groovy", QDialogButtonBox.AcceptRole)
    groovy_button.setStyleSheet(
        f"background-color: {ABOUT_DIALOG_ACCENT_BUTTON_COLOR}; color: #ffffff; font-weight: 700;"
    )
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)

    dialog.finished.connect(lambda _result: _show_about_close_sparkles(dialog.frameGeometry()))
    dialog.show()

def _minimize_window(owner: QWidget) -> None:
    from PySide6.QtCore import Qt

    window = owner.window()

    if not window.testAttribute(Qt.WA_WState_Created):
        window.show()

    if not window.isWindow():
        window.setWindowFlag(Qt.Window, True)
        window.show()

    window.showMinimized()

#     Alternately, try:
# def _minimize_window(owner: QWidget) -> None:
#     owner.window().showMinimized()

def _quit_application() -> None:
    """Request a full application shutdown via QApplication."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        app.quit()

def configure_splitter_handle_resize_cursor(splitter) -> None:
    """Ensure splitter handles show the expected directional resize cursor."""
    from PySide6.QtCore import Qt

    cursor_shape = (
        Qt.SplitHCursor
        if splitter.orientation() == Qt.Horizontal
        else Qt.SplitVCursor
    )
    for handle_index in range(1, splitter.count()):
        handle = splitter.handle(handle_index)
        if handle is not None:
            handle.setCursor(cursor_shape)

def configure_application_identity(app: "QApplication") -> None:
    """Set a consistent application identity shown by the OS shell and Qt."""
    app.setApplicationName(APP_DISPLAY_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setOrganizationName(APP_DISPLAY_NAME)



def _show_sidereal_discussion_help(owner: "QWidget") -> None:
    """Open a placeholder sidereal discussion page from Guide to the Galaxy."""
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

    dialog = QDialog(owner)
    dialog.setModal(False)
    dialog.setWindowTitle("Sidereal Discussion")
    dialog.resize(560, 360)

    layout = QVBoxLayout(dialog)
    label = QLabel(
        "<h2>Sidereal Discussion</h2>"
        "<p>This help page is intentionally blank for now.</p>"
        "<p>Future notes can compare tropical and sidereal reference frames, "
        "ayanāṃśa choices, and why astrological traditions do not always "
        "map one-to-one onto astronomy.</p>"
    )
    label.setWordWrap(True)
    label.setOpenExternalLinks(False)
    layout.addWidget(label, 1)

    buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=dialog)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.show()


def _show_guide_to_the_galaxy(owner: "QWidget") -> None:
    """Show an animated, draggable astrology-oriented solar-system explainer."""
    from math import cos, pi, sin

    from PySide6.QtCore import QPointF, QRectF, QTimer, Qt
    from PySide6.QtGui import QColor, QFont, QPainter, QPen
    from PySide6.QtWidgets import (
        QDialog,
        QDialogButtonBox,
        QHBoxLayout,
        QLabel,
        QTextBrowser,
        QVBoxLayout,
        QWidget,
    )

    bodies = (
        {"name": "Moon", "period": 27.32, "distance": 0.18, "color": "#d7dde8", "size": 6},
        {"name": "Mercury", "period": 87.97, "distance": 0.30, "color": "#b9a58d", "size": 6},
        {"name": "Venus", "period": 224.70, "distance": 0.40, "color": "#e4c477", "size": 7},
        {"name": "Sun", "period": 365.25, "distance": 0.52, "color": "#ffcc45", "size": 9},
        {"name": "Mars", "period": 686.98, "distance": 0.62, "color": "#d46a4c", "size": 7},
        {"name": "Jupiter", "period": 4332.59, "distance": 0.73, "color": "#d2a679", "size": 10},
        {"name": "Saturn", "period": 10759.22, "distance": 0.83, "color": "#c5b070", "size": 9},
        {"name": "Uranus", "period": 30688.5, "distance": 0.91, "color": "#78c7d8", "size": 8},
        {"name": "Neptune", "period": 60182.0, "distance": 0.98, "color": "#5c7dff", "size": 8},
        {"name": "Pluto", "period": 90560.0, "distance": 1.05, "color": "#b8a6a0", "size": 5},
    )

    class SolarSystemModel(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setMinimumSize(520, 520)
            self.setMouseTracking(True)
            self._time_days = 0.0
            self._dragging = False
            self._drag_start_x = 0
            self._drag_start_time = 0.0
            self._paused = False
            self._selected = "Earth"
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._tick)
            self._timer.start(33)

        def _tick(self):
            if not self._paused and not self._dragging:
                self._time_days += 3.0
                self.update()

        def _body_positions(self):
            rect = self.rect().adjusted(34, 34, -34, -34)
            center = QPointF(rect.center())
            max_radius = min(rect.width(), rect.height()) / 2.0 * 0.86
            positions = []
            for body in bodies:
                radius = max_radius * float(body["distance"]) / 1.05
                angle = (self._time_days / float(body["period"]) * 2.0 * pi) - pi / 2.0
                point = QPointF(center.x() + cos(angle) * radius, center.y() + sin(angle) * radius)
                positions.append((body, point, radius))
            return center, positions

        def paintEvent(self, event):  # noqa: ANN001 - Qt override signature varies.
            super().paintEvent(event)
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillRect(self.rect(), QColor("#08101f"))
            center, positions = self._body_positions()
            painter.setPen(QPen(QColor("#2f4265"), 1))
            for body, _point, radius in positions:
                painter.drawEllipse(center, radius, radius)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#65a7ff"))
            painter.drawEllipse(center, 11, 11)
            painter.setPen(QColor("#dbe7ff"))
            painter.drawText(QRectF(center.x() - 28, center.y() + 14, 56, 18), Qt.AlignCenter, "Earth")
            for body, point, _radius in positions:
                size = int(body["size"])
                painter.setBrush(QColor(str(body["color"])))
                painter.setPen(QPen(QColor("#ffffff") if body["name"] == self._selected else QColor("#18253f"), 2))
                painter.drawEllipse(point, size, size)
                painter.setPen(QColor("#dbe7ff"))
                painter.drawText(QRectF(point.x() - 38, point.y() + size + 2, 76, 18), Qt.AlignCenter, str(body["name"]))
            painter.setFont(QFont("", 9))
            painter.setPen(QColor("#9fb5d9"))
            painter.drawText(14, self.height() - 18, f"Drag left/right to scrub time • click bodies • model days elapsed: {int(self._time_days):,}")

        def mousePressEvent(self, event):  # noqa: ANN001
            if event.button() == Qt.LeftButton:
                self._dragging = True
                self._paused = True
                self._drag_start_x = event.position().x()
                self._drag_start_time = self._time_days
                center, positions = self._body_positions()
                if (event.position() - center).manhattanLength() < 16:
                    self._selected = "Earth"
                for body, point, _radius in positions:
                    if (event.position() - point).manhattanLength() <= int(body["size"]) + 8:
                        self._selected = str(body["name"])
                self.update()
            super().mousePressEvent(event)

        def mouseMoveEvent(self, event):  # noqa: ANN001
            if self._dragging:
                self._time_days = max(0.0, self._drag_start_time + (event.position().x() - self._drag_start_x) * 10.0)
                self.update()
            super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event):  # noqa: ANN001
            if event.button() == Qt.LeftButton:
                self._dragging = False
                self._paused = False
            super().mouseReleaseEvent(event)

    dialog = QDialog(owner)
    dialog.setModal(False)
    dialog.setWindowTitle("Guide to the Galaxy")
    dialog.resize(1060, 720)
    layout = QVBoxLayout(dialog)
    title = QLabel("<h1>Guide to the Galaxy</h1>")
    layout.addWidget(title)
    subhead = QTextBrowser(dialog)
    subhead.setOpenExternalLinks(False)
    subhead.setMaximumHeight(96)
    subhead.setHtml(
        "<p><em>This is not astronomy. The two are connected, but astronomy is an empirical, "
        "materialist science. Astrology is subjective metaphysics, and many people would deem it "
        "a pseudoscience in the pejorative sense. They do reference many of the same basic tools, "
        "but they are not entirely in accord. For instance, the "
        "<a href='ephemeraldaddy://help/sidereal-discussion'>sidereal discussion</a>.</em></p>"
    )
    subhead.anchorClicked.connect(lambda _url: _show_sidereal_discussion_help(dialog))
    layout.addWidget(subhead)

    row = QHBoxLayout()
    model = SolarSystemModel(dialog)
    row.addWidget(model, 3)
    explain = QTextBrowser(dialog)
    explain.setOpenExternalLinks(False)
    explain.setHtml(
        "<h2>Compressed model caveat</h2>"
        "<p>The solar system is far vaster than any comfortable screen model. Orbit sizes, planet sizes, "
        "and speeds are deliberately compressed so the pattern is legible. Earth is fixed at the center "
        "because this is illustrating how astrology interprets sky positions from here on Earth.</p>"
        "<h2>How quickly chart factors can change</h2>"
        "<table border='1' cellspacing='0' cellpadding='4'>"
        "<tr><th>Factor</th><th>Minimum</th><th>Modal / typical</th><th>Maximum</th></tr>"
        "<tr><td>Ascendant / houses</td><td>Minutes</td><td>~2 hours per sign</td><td>~2.5 hours per sign</td></tr>"
        "<tr><td>Moon sign</td><td>Hours near a boundary</td><td>~2.3 days per sign</td><td>~2.7 days per sign</td></tr>"
        "<tr><td>Sun sign</td><td>Hours near a cusp</td><td>~30 days per sign</td><td>~31 days per sign</td></tr>"
        "<tr><td>Mercury sign</td><td>Days</td><td>2-3 weeks</td><td>~2 months with retrograde loops</td></tr>"
        "<tr><td>Venus sign</td><td>Days</td><td>3-4 weeks</td><td>Several months during retrograde</td></tr>"
        "<tr><td>Mars sign</td><td>Weeks</td><td>~6-8 weeks</td><td>~7 months during retrograde</td></tr>"
        "<tr><td>Jupiter sign</td><td>Months</td><td>~1 year</td><td>~13 months</td></tr>"
        "<tr><td>Saturn sign</td><td>Months</td><td>~2.5 years</td><td>~3 years</td></tr>"
        "<tr><td>Uranus sign</td><td>Months</td><td>~7 years</td><td>~8 years</td></tr>"
        "<tr><td>Neptune sign</td><td>Months</td><td>~14 years</td><td>~15 years</td></tr>"
        "<tr><td>Pluto sign</td><td>Months</td><td>~12-31 years</td><td>~31+ years</td></tr>"
        "</table>"
        "<p><strong>Rule of thumb:</strong> inner bodies personalize fast; outer bodies describe broader cohorts. "
        "Exact chart angles can change within minutes, so birth time matters most for houses and angles.</p>"
    )
    row.addWidget(explain, 2)
    layout.addLayout(row, 1)
    buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=dialog)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    dialog.show()


def configure_main_window_chrome(window: "QMainWindow") -> None:
    """Attach a top-level menu bar and app title for the main window."""
    update_main_window_title(window)

    menu_bar = window.menuBar()
    _configure_menu_bar_visibility(menu_bar)
    menu_bar.setStyleSheet(WINDOW_CHROME_MENU_STYLE)
    menu_bar.clear()

    app_menu = menu_bar.addMenu(APP_DISPLAY_NAME)
    _add_preferences_submenu(app_menu, window)
    app_menu.addAction("About", lambda: _show_about_from_onboarding(window))
    app_menu.addAction("Minimize", lambda: _minimize_window(window))
    app_menu.addSeparator()
    app_menu.addAction(f"Exit", _quit_application)

    chart_menu = menu_bar.addMenu("Charts") #note: chart_menu is "Chart View"'s version of Database Views charts_menu
    _bind_menu_action(chart_menu, "New Chart", window, "on_new_chart")
    _bind_menu_action(chart_menu, "Export Chart", window, "on_export_chart")
    chart_menu.addSeparator()
    _bind_menu_action(chart_menu, "🐉 BaZi Chart", window, "on_open_bazi_window")
    _bind_menu_action(chart_menu, "🌎 Personal Transit", window, "on_get_current_transits")
    _bind_menu_action(chart_menu, "🧬 Synastry Chart", window, "on_get_synastry_chart")
    if _is_human_design_menu_enabled(window):
        human_design_menu = chart_menu.addMenu("🪷 Human Design Chart")
        _bind_menu_action(
            human_design_menu,
            "Human Design Chart",
            window,
            "_on_menu_get_human_design_info",
            "on_get_human_design_info",
        )
        _bind_menu_action(
            human_design_menu,
            "Human Design Synastry Chart",
            window,
            "on_get_human_design_synastry_chart",
        )

    tools_menu = menu_bar.addMenu("Tools")
    _bind_menu_action(
        tools_menu,
        "👯 See Similar Charts",
        window,
        "_show_similar_charts_popout",
        "on_show_similar_charts_popout",
    )
    _bind_menu_action(tools_menu, "💎 Create Gemstone Chart", window, "on_create_gemstone_chartwheel")
    _bind_menu_action(tools_menu, "🧓 Interpret Astro Age (alpha)", window, "on_interpret_astro_age")
    _bind_menu_action(tools_menu, "🔮 Chart Predictor Quiz (alpha)", window, "on_open_chart_predictor_quiz")
    _bind_menu_action(tools_menu, "🕗 Rectification Engine", window, "_on_retcon_engine")
    _bind_menu_action(tools_menu, "🔘 Sign Degrees Reference Circle", window, "_on_open_sign_degrees_reference_circle",
                      "on_open_sign_degrees_reference_circle")

    # view_menu = menu_bar.addMenu("View")
    # _bind_menu_action(view_menu, "Chart Analytics", window, "on_show_chart_analytics_panel")

    help_menu = menu_bar.addMenu("HALP!")
    help_menu.addAction("Guide to the Galaxy", lambda: _show_guide_to_the_galaxy(window))
    _bind_menu_action(help_menu, "Tutorial", window, "_on_manage_help_overlay", "on_manage_help_overlay", "_toggle_help_overlay")
    _bind_menu_action(help_menu, "About", window, "_show_about_from_onboarding(dialog)")

def configure_manage_dialog_chrome(dialog: "QWidget", layout: "QLayout") -> None:
    """Attach a Database View menu bar matching the requested hierarchy."""
    from PySide6.QtWidgets import QMenuBar

    dialog.setWindowTitle(f"{APP_DISPLAY_NAME} | Database View")

    menu_bar = QMenuBar(dialog)
    _configure_menu_bar_visibility(menu_bar)
    menu_bar.setStyleSheet(WINDOW_CHROME_MENU_STYLE)

    app_menu = menu_bar.addMenu(APP_DISPLAY_NAME)
    _add_preferences_submenu(app_menu, dialog)
    app_menu.addAction("Minimize", lambda: _minimize_window(dialog))
    app_menu.addSeparator()
    app_menu.addAction(f"Exit", _quit_application)

    file_menu = menu_bar.addMenu("Database")
    import_menu = file_menu.addMenu("Import from CSV")
    _bind_menu_action(import_menu, "Import from CSV (Type 1)", dialog, "_on_import_csv_type_1")
    _bind_menu_action(import_menu, "Import from CSV (The Pattern app)", dialog, "_on_import_csv_pattern")
    _bind_menu_action(file_menu, "Export Selection to CSV", dialog, "_on_export_selected")
    _bind_menu_action(file_menu, "Backup Database", dialog, "_on_export_database")
    _bind_menu_action(file_menu, "Restore Database", dialog, "_on_import_database")
    _bind_menu_action(file_menu, "Refresh Database", dialog, "_on_force_refresh_database_analysis")
    # _bind_menu_action(file_menu, "Batch Edit Entries", dialog, "_toggle_edit_panel")
    charts_menu = menu_bar.addMenu("Charts")
    _bind_menu_action(charts_menu, "New chart", dialog, "_on_new_chart", "on_new_chart")
    _bind_menu_action(charts_menu, "Edit chart", dialog, "_on_edit_chart_from_menu")
    _bind_menu_action(charts_menu, "Delete chart(s)", dialog, "_on_delete", "on_delete")
    _bind_menu_action(charts_menu, "Current Transits", dialog, "_show_current_transits_panel")
    _bind_menu_action(charts_menu, "🌎 Personal Transit Chart", dialog, "_on_generate_personal_transit_for_selected_chart")
    _bind_menu_action(charts_menu, "Export Chart as MD/TXT", dialog, "_on_menu_export_chart")
    charts_menu.addSeparator()
    _bind_menu_action(charts_menu, "🧬 Synastry Chart", dialog, "_on_generate_composite_chart")
    _bind_menu_action(charts_menu, "🐉 BaZi Chart", dialog, "_on_menu_open_bazi_window")
    if _is_human_design_menu_enabled(dialog):
        human_design_menu = charts_menu.addMenu("🪷 Human Design Chart")
        _bind_menu_action(human_design_menu, "Human Design Chart", dialog, "_on_menu_get_human_design_info")
        _bind_menu_action(
            human_design_menu,
            "Human Design Synastry Chart",
            dialog,
            "_on_menu_get_human_design_synastry_chart",
        )

    tools_menu = menu_bar.addMenu("Tools")
    _bind_menu_action(
        tools_menu,
        "👯 See Similar Charts",
        dialog,
        "_on_menu_see_similar_charts",
    )
    _bind_menu_action(tools_menu, "🕗 Rectification Engine", dialog, "_on_retcon_engine")
    _bind_menu_action(tools_menu, "🧓 Interpret Astro Age (alpha)", dialog, "_on_menu_interpret_astro_age")
    _bind_menu_action(tools_menu, "💎 Create Gemstone Chart", dialog, "_on_menu_create_gemstone_chart")
    #to do: add a link here to find charts most similar to the currently selected chart if one is selected, the text will say "Find Similar Charts"
    _bind_menu_action(
        tools_menu,
        "🔮 Chart Predictor Quiz (alpha)",
        dialog,
        "_on_menu_open_chart_predictor_quiz",
        "on_open_chart_predictor_quiz",
    )
    _bind_menu_action(tools_menu, "🔘 Sign Degrees Reference Circle", dialog, "_on_open_sign_degrees_reference_circle",
                      "on_open_sign_degrees_reference_circle")

    view_menu = menu_bar.addMenu("View")
    _bind_menu_action(view_menu, "Database Analytics", dialog, "_show_database_analytics_panel")
    _bind_menu_action(view_menu, "Similarities Analysis", dialog, "_show_similarities_panel")
    _bind_menu_action(view_menu, "General Population Comparison", dialog, "_show_gen_pop_comparison_panel")
    _bind_menu_action(view_menu, "Manage Collections", dialog, "_show_manage_collections_panel")
    _bind_menu_action(view_menu, "Search Database", dialog, "_show_search_database_panel")
    _bind_menu_action(view_menu, "Database Manager", dialog, "_toggle_edit_panel")

    help_menu = menu_bar.addMenu("HALP!")
    help_menu.addAction("Guide to the Galaxy", lambda: _show_guide_to_the_galaxy(dialog))
    _bind_menu_action(help_menu, "HALP!", dialog, "_on_manage_help_overlay", "on_manage_help_overlay")
    #_bind_menu_action(help_menu, "Sign Degrees Reference Circle", dialog, "_on_open_sign_degrees_reference_circle", "on_open_sign_degrees_reference_circle")
    help_menu.addAction("About", lambda: _show_about_from_onboarding(dialog))

    layout.setMenuBar(menu_bar)
