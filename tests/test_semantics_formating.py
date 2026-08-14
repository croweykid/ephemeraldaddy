from types import SimpleNamespace

import pytest

from ephemeraldaddy.semantics_formatting import (
    format_ordinal,
    ordinal_suffix,
    pronouns_for_chart,
    pronouns_for_gender,
)


def test_pronouns_for_gender_supported_chart_codes():
    assert pronouns_for_gender("F").slash_form == "she/her/hers/herself"
    assert pronouns_for_gender("AMAB-F").slash_form == "she/her/hers/herself"
    assert pronouns_for_gender("M").slash_form == "he/him/his/himself"
    assert pronouns_for_gender("AFAB-M").slash_form == "he/him/his/himself"
    assert pronouns_for_gender("AFAB-NB").slash_form == "they/them/their/themself"
    assert pronouns_for_gender("AMAB-NB").slash_form == "they/them/their/themself"


def test_pronouns_for_chart_reads_gender_attribute():
    chart = SimpleNamespace(gender="afab_nb")

    assert pronouns_for_chart(chart).slash_form == "they/them/their/themself"


def test_pronouns_for_gender_unknown_uses_default():
    default = pronouns_for_gender("F")

    assert pronouns_for_gender("", default=default) is default


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (1, "1st"),
        (2, "2nd"),
        (3, "3rd"),
        (4, "4th"),
        (11, "11th"),
        (12, "12th"),
        (13, "13th"),
        (21, "21st"),
        (102, "102nd"),
    ],
)
def test_format_ordinal_applies_english_numeric_suffix_rules(number, expected):
    assert ordinal_suffix(number) == expected.removeprefix(str(number))
    assert format_ordinal(number) == expected


def test_historical_semantics_module_remains_compatible():
    from ephemeraldaddy.semantics_formating import format_ordinal as legacy_format_ordinal

    assert legacy_format_ordinal(8) == "8th"
