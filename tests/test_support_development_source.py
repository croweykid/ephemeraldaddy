from pathlib import Path

from ephemeraldaddy.gui.support_content import (
    SUPPORT_ACTION_LABEL,
    SUPPORT_DIALOG_TEXT,
    SUPPORT_URL,
)

ROOT = Path(__file__).resolve().parents[1]


def test_support_flow_uses_existing_repository_funding_destination():
    funding = (ROOT / ".github" / "FUNDING.yml").read_text(encoding="utf-8")
    assert "patreon: croweykid" in funding
    assert SUPPORT_URL == "https://www.patreon.com/croweykid"


def test_support_copy_is_optional_and_explains_external_privacy_boundary():
    assert SUPPORT_ACTION_LABEL == "Support this app's ongoing development"
    assert "entirely optional" in SUPPORT_DIALOG_TEXT
    assert "does not unlock features" in SUPPORT_DIALOG_TEXT
    assert "does not collect payment or identity information" in SUPPORT_DIALOG_TEXT
    assert "default browser" in SUPPORT_DIALOG_TEXT
    assert "cannot promise anonymity" in SUPPORT_DIALOG_TEXT


def test_both_window_chrome_application_menus_include_support_action():
    source = (ROOT / "ephemeraldaddy" / "gui" / "window_chrome.py").read_text(
        encoding="utf-8"
    )
    assert source.count("app_menu.addAction(\n            SUPPORT_ACTION_LABEL") == 2


def test_support_flow_requires_confirmation_before_opening_browser():
    source = (ROOT / "ephemeraldaddy" / "gui" / "support_development.py").read_text(
        encoding="utf-8"
    )
    assert "if dialog.exec() == QDialog.Accepted:" in source
    assert "QDesktopServices.openUrl(QUrl(SUPPORT_URL))" in source
    assert source.index("if dialog.exec()") < source.index("QDesktopServices.openUrl")
