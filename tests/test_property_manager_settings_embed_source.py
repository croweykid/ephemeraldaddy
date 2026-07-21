from pathlib import Path


PROPERTY_MANAGER_SOURCE = Path("ephemeraldaddy/gui/property_manager.py").read_text()


def test_embedded_property_manager_uses_plain_widget_chrome() -> None:
    embedded_block = PROPERTY_MANAGER_SOURCE.split("if embedded:", 1)[1].split("return dialog", 1)[0]

    assert "dialog.setWindowFlags(Qt.Widget)" in embedded_block
    assert "dialog.setWindowModality(Qt.NonModal)" in embedded_block
    assert "dialog.setSizeGripEnabled(False)" in embedded_block


def test_embedded_property_manager_hides_legacy_close_button() -> None:
    embedded_block = PROPERTY_MANAGER_SOURCE.split("if embedded:", 1)[1].split("return dialog", 1)[0]

    assert "if close_button is not None:" in embedded_block
    assert "close_button.hide()" in embedded_block
