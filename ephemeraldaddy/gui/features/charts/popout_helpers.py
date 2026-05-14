"""Shared popout-window helpers for chart feature dialogs.

These functions intentionally preserve the existing `gui.app` popout behavior while
allowing MainWindow and ManageChartsDialog to delegate generic popout plumbing out of
that module.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QPlainTextEdit,
    QToolButton,
    QWidget,
)


def register_popout_close_shortcuts(dialog: QWidget) -> None:
    """Install Ctrl/Cmd+W close shortcuts on a popout dialog/window."""
    dialog._shortcut_close_ctrl = QShortcut(QKeySequence("Ctrl+W"), dialog)
    dialog._shortcut_close_ctrl.activated.connect(dialog.close)
    dialog._shortcut_close_cmd = QShortcut(QKeySequence("Meta+W"), dialog)
    dialog._shortcut_close_cmd.activated.connect(dialog.close)


def position_popout_share_button(output_widget: QPlainTextEdit, button: QToolButton) -> None:
    """Pin a popout share/export button to the top-right of its host window."""
    host_window = output_widget.window()
    if not isinstance(host_window, QWidget):
        return

    anchor_parent = (
        button.parentWidget()
        if isinstance(button.parentWidget(), QWidget)
        else host_window
    )
    margin = 6
    button.move(
        max(margin, anchor_parent.width() - button.width() - margin),
        margin,
    )
    button.raise_()
    button.show()


def attach_popout_share_button(
    *,
    output_widget: QPlainTextEdit,
    default_file_stem: str,
    export_text_provider: Callable[[], str] | None = None,
    share_icon_path_provider: Callable[[], str | None] | None = None,
    export_callback: Callable[[QPlainTextEdit, str, Callable[[], str] | None], None],
) -> QToolButton:
    """Create and attach the standard popout share/export button."""
    host_window = output_widget.window()
    share_parent = host_window if isinstance(host_window, QWidget) else output_widget
    share_button = QToolButton(share_parent)
    share_icon_path = share_icon_path_provider() if callable(share_icon_path_provider) else None
    if share_icon_path:
        share_button.setIcon(QIcon(share_icon_path))
        share_button.setIconSize(QSize(14, 14))
    else:
        share_button.setText("↗")
    share_button.setAutoRaise(True)
    share_button.setCursor(Qt.PointingHandCursor)
    share_button.setToolTip("Export chart data output as Markdown or text")

    def _export_clicked(
        _checked: bool = False,
        widget: QPlainTextEdit = output_widget,
        stem: str = default_file_stem,
        provider: Callable[[], str] | None = export_text_provider,
    ) -> None:
        export_callback(
            widget,
            stem,
            provider,
        )

    share_button.clicked.connect(_export_clicked)
    share_button.resize(22, 22)
    position_popout_share_button(output_widget, share_button)
    return share_button


def export_popout_chart_data_output(
    *,
    owner: QWidget,
    output_widget: QPlainTextEdit,
    default_file_stem: str,
    sanitize_export_token: Callable[[str, str], str],
    export_text_provider: Callable[[], str] | None = None,
) -> None:
    """Export popout text content using the existing Markdown/Text dialog flow."""
    if callable(export_text_provider):
        summary_text = export_text_provider().strip()
    else:
        summary_text = output_widget.toPlainText().strip()
    if not summary_text:
        QMessageBox.information(
            owner,
            "Nothing to export",
            "Generate or load a chart before exporting chart data output.",
        )
        return

    safe_stem = sanitize_export_token(default_file_stem, "chart_data_output")
    file_path, selected_filter = QFileDialog.getSaveFileName(
        owner,
        "Export Chart Data Output",
        f"{safe_stem}.md",
        "Markdown Files (*.md);;Text Files (*.txt)",
    )
    if not file_path:
        return

    selected_extension = ".txt" if "*.txt" in selected_filter else ".md"
    if not file_path.lower().endswith((".md", ".txt")):
        file_path = f"{file_path}{selected_extension}"

    try:
        with open(file_path, "w", encoding="utf-8") as output_file:
            output_file.write(summary_text)
    except Exception as e:
        QMessageBox.critical(
            owner,
            "Export failed",
            f"Could not export chart data output:\n{e}",
        )
        return

    QMessageBox.information(
        owner,
        "Export complete",
        f"Saved chart data output to:\n{file_path}",
    )
