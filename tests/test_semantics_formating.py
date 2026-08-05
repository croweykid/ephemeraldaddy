from types import SimpleNamespace

from ephemeraldaddy.semantics_formating import pronouns_for_chart, pronouns_for_gender


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
