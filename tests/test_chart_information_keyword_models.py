from ephemeraldaddy.core.interpretations import PLANETARY_JOYS
from ephemeraldaddy.gui.features.chart_information.keyword_models import (
    build_aspect_keyword_text,
    build_decan_information,
    build_element_definition_lines,
    build_house_keyword_text,
    build_mode_keyword_model,
    build_planet_keyword_text,
)


def test_decan_information_normalizes_longitude_and_reference_data():
    decan = build_decan_information(" aries ", 375.0)

    assert decan is not None
    assert decan.sign_name == "Aries"
    assert decan.decan_number == 2
    assert decan.ordinal_label == "2nd"
    assert decan.subsign_ruler != "Unknown"
    assert decan.description
    assert decan.keywords


def test_decan_information_rejects_missing_or_invalid_longitudes():
    assert build_decan_information("Aries", None) is None
    assert build_decan_information("Aries", "unknown") is None
    assert build_decan_information("Aries", float("nan")) is None


def test_mode_keyword_model_normalizes_and_freezes_reference_data():
    model = build_mode_keyword_model(" CARDINAL ")

    assert model.key == "cardinal"
    assert model.label == "Cardinal"
    assert model.has_reference_data
    assert model.keywords == tuple(sorted(model.keywords))
    assert model.signs == tuple(sorted(model.signs))
    assert not build_mode_keyword_model("").has_reference_data


def test_element_definition_lines_are_reusable_by_panel_and_popout():
    lines = build_element_definition_lines(" fire ")

    assert lines[0] == "Fire"
    assert any(line.startswith("Qualities: ") for line in lines)
    assert "Strengths:" in lines
    assert any(line.startswith("• ") for line in lines)
    assert build_element_definition_lines("") == [
        "Element",
        "",
        "No element definition data available.",
    ]


def test_planet_keywords_include_dignity_before_house_joy():
    joy_house = next(iter(PLANETARY_JOYS["Sun"]))
    text = build_planet_keyword_text(
        "Sun",
        display_body="Sun",
        sign_name="Leo",
        house_number=joy_house,
        chart_uses_houses=True,
    )

    assert text.startswith("Sun\nRuler of Leo.\n\n• ")
    assert "With joy" not in text


def test_planetary_joy_requires_reliable_house_availability():
    house_number = next(iter(PLANETARY_JOYS["Sun"]))

    with_houses = build_planet_keyword_text(
        "Sun",
        display_body="Sun",
        house_number=house_number,
        chart_uses_houses=True,
    )
    without_houses = build_planet_keyword_text(
        "Sun",
        display_body="Sun",
        house_number=house_number,
        chart_uses_houses=False,
    )

    assert f"With joy in house {house_number}." in with_houses
    assert "With joy" not in without_houses


def test_unknown_planet_has_an_explicit_empty_state():
    assert build_planet_keyword_text("", display_body="Body") == (
        "Body\n\nNo verb keywords available."
    )


def test_aspect_keywords_render_known_names_and_handle_unknown_values():
    known = build_aspect_keyword_text("conjunction")

    assert known.startswith("conjunction keywords\n\n• ")
    assert build_aspect_keyword_text("") == "Aspect keywords\n\nNo keyword data available."


def test_house_keywords_include_optional_planetary_joy_context():
    text = build_house_keyword_text(9, joy_body="  Sun  ")

    assert text.startswith("9th House (planetary joy in Sun)\n\n• ")
    assert build_house_keyword_text(99) == (
        "99th House\n\nNo house keywords available."
    )
