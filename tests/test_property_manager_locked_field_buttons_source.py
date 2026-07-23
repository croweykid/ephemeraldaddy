from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEV_TOOLS_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/dev_tools.py").read_text(encoding="utf-8")


def test_locked_property_manager_does_not_construct_selector_buttons():
    constructor_body = DEV_TOOLS_SOURCE.split("def __init__", 1)[1].split(
        "header_row = QHBoxLayout()", 1
    )[0]
    locked_guard_index = constructor_body.index("if not lock_field:")
    button_group_index = constructor_body.index("self._field_button_group = QButtonGroup(self)")
    add_layout_index = constructor_body.index("layout.addLayout(field_button_row)")
    assert locked_guard_index < button_group_index < add_layout_index
