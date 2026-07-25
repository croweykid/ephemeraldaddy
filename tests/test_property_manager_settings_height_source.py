from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()


def test_property_manager_tab_fills_the_available_settings_height() -> None:
    property_manager_setup = APP_SOURCE.split(
        '"Property Manager",', 1
    )[1].split(
        "self._populate_settings_property_manager_section", 1
    )[0]
    section_builder = APP_SOURCE.split(
        "def _add_settings_collapsible_section(", 1
    )[1].split(
        "def _add_settings_action_section(", 1
    )[0]

    assert "fill_available_height=True" in property_manager_setup
    assert "QSizePolicy.Expanding if fill_available_height else QSizePolicy.Preferred" in section_builder
    assert "page_layout.addWidget(section_content, 1 if fill_available_height else 0)" in section_builder
    assert "if not fill_available_height:" in section_builder
