from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget


def confirm_manual_wikipedia_import(parent: QWidget, page_title: str) -> bool:
    """Ask whether a Wikipedia result without a birthplace should become a draft."""
    prompt = QMessageBox(parent)
    prompt.setIcon(QMessageBox.Icon.Information)
    prompt.setWindowTitle("Astrotheme import")
    prompt.setText(
        f"{page_title} found on Wikipedia, but no birth place info is available.\n\n"
        "Import available info anyway and fill in blank fields manually? Or just forget it?"
    )
    cancel_button = prompt.addButton(
        "Cancel import",
        QMessageBox.ButtonRole.RejectRole,
    )
    finish_button = prompt.addButton(
        "Finish manually",
        QMessageBox.ButtonRole.AcceptRole,
    )
    prompt.setDefaultButton(cancel_button)
    prompt.setEscapeButton(cancel_button)
    prompt.exec()
    return prompt.clickedButton() is finish_button
