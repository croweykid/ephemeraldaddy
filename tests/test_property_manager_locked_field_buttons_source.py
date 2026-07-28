from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEV_TOOLS_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/dev_tools.py").read_text(encoding="utf-8")


def test_locked_property_manager_does_not_construct_selector_tabs():
    constructor_body = DEV_TOOLS_SOURCE.split("def __init__", 1)[1].split(
        "header_row = QHBoxLayout()", 1
    )[0]
    locked_guard_index = constructor_body.index("if not lock_field:")
    tab_bar_index = constructor_body.index("self._field_tabs = QTabBar(self)")
    add_widget_index = constructor_body.index("layout.addWidget(self._field_tabs)")
    assert locked_guard_index < tab_bar_index < add_widget_index
