import pytest

from ephemeraldaddy.core.human_design_system import (
    MANDALA_GATE_ORDER,
    MANDALA_START_DEGREE,
)
from ephemeraldaddy.gui.features.chart_information.token_formatting import (
    format_human_design_zodiac_degree,
    human_design_gate_circuit_group,
    human_design_gate_degree_range_text,
    human_design_gate_header_suffix,
    ordinal_house_header,
)


@pytest.mark.parametrize(
    ("house_number", "expected"),
    [(1, "1st House"), (2, "2nd House"), (3, "3rd House"), (11, "11th House")],
)
def test_ordinal_house_header_uses_english_ordinal_rules(house_number, expected):
    assert ordinal_house_header(house_number) == expected


def test_zodiac_degree_formatting_wraps_and_carries_rounded_minutes():
    assert format_human_design_zodiac_degree(-0.001) == "0°00' Aries"
    assert format_human_design_zodiac_degree(29.999) == "0°00' Taurus"
    assert format_human_design_zodiac_degree(360.0) == "0°00' Aries"


def test_gate_degree_range_uses_the_mandala_order_and_width():
    first_gate = MANDALA_GATE_ORDER[0]
    expected_start = format_human_design_zodiac_degree(MANDALA_START_DEGREE)
    expected_end = format_human_design_zodiac_degree(
        MANDALA_START_DEGREE + (360.0 / 64.0)
    )

    assert human_design_gate_degree_range_text(first_gate) == (
        f"{expected_start}–{expected_end}"
    )
    assert human_design_gate_degree_range_text(999) == "degree range unknown"


def test_gate_circuit_and_header_suffix_use_reference_data():
    circuit = human_design_gate_circuit_group(1)

    assert circuit != "circuit unknown"
    assert human_design_gate_circuit_group(999) == "circuit unknown"
    assert human_design_gate_header_suffix(1).startswith(f"{circuit}, ")
