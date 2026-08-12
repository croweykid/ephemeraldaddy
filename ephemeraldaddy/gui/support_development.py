"""Privacy-conscious handoff to EphemeralDaddy's external support page."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ephemeraldaddy.gui.support_content import (
    SUPPORT_DIALOG_TEXT,
    SUPPORT_DIALOG_TITLE,
    SUPPORT_URL,
)


def show_support_development_dialog(owner: QWidget) -> None:
    """Explain the external handoff and open it only after explicit consent."""

    dialog = QDialog(owner)
    dialog.setModal(True)
    dialog.setWindowTitle(SUPPORT_DIALOG_TITLE)
    dialog.setMinimumWidth(520)

    layout = QVBoxLayout(dialog)
    message = QLabel(SUPPORT_DIALOG_TEXT, dialog)
    message.setWordWrap(True)
    layout.addWidget(message)

    buttons = QDialogButtonBox(QDialogButtonBox.Cancel, parent=dialog)
    continue_button = buttons.addButton("Continue to Patreon", QDialogButtonBox.AcceptRole)
    continue_button.setDefault(False)
    continue_button.setAutoDefault(False)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() == QDialog.Accepted:
        if not QDesktopServices.openUrl(QUrl(SUPPORT_URL)):
            QMessageBox.warning(
                owner,
                SUPPORT_DIALOG_TITLE,
                "Your browser could not be opened. No support transaction was started.",
            )
