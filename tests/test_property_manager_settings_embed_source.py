from pathlib import Path


PROPERTY_MANAGER_SOURCE = Path("ephemeraldaddy/gui/property_manager.py").read_text()
DEV_TOOLS_SOURCE = Path("ephemeraldaddy/gui/dev_tools.py").read_text()


def test_embedded_property_manager_uses_plain_widget_chrome() -> None:
    create_widget_block = PROPERTY_MANAGER_SOURCE.split("def create_widget(", 1)[1].split("def launch(", 1)[0]
    embedded_block = PROPERTY_MANAGER_SOURCE.split("if embedded:", 1)[1].split("return dialog", 1)[0]

    assert "window_flags=Qt.Widget if embedded else Qt.Dialog" in create_widget_block
    assert "dialog.setWindowFlags(Qt.Widget)" not in embedded_block
    assert "dialog.setWindowModality(Qt.NonModal)" in embedded_block
    assert "dialog.setSizeGripEnabled(False)" in embedded_block


def test_embedded_property_manager_does_not_create_legacy_close_button() -> None:
    create_widget_block = PROPERTY_MANAGER_SOURCE.split("def create_widget(", 1)[1].split("def launch(", 1)[0]
    dialog_source = DEV_TOOLS_SOURCE.split("class ManageMetadataLabelsDialog", 1)[1]
    init_signature = dialog_source.split("def __init__(", 1)[1].split(") -> None:", 1)[0]
    button_block = dialog_source.split("button_row = QHBoxLayout()", 1)[1].split(
        "layout.addLayout(button_row)", 1
    )[0]

    assert "show_close_button=not embedded" in create_widget_block
    assert "show_close_button: bool = True" in init_signature
    assert "window_flags: Qt.WindowType = Qt.Dialog" in init_signature
    assert "super().__init__(parent, window_flags)" in dialog_source
    assert "QPushButton(\"Close\") if show_close_button else None" in button_block
    assert "self._close_button" not in DEV_TOOLS_SOURCE
    assert "close_button.hide()" not in PROPERTY_MANAGER_SOURCE
