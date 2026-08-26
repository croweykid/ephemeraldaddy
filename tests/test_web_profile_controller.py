from ephemeraldaddy.gui.features.import_export.web_profile_controller import (
    missing_wikipedia_birth_fields,
)


def test_missing_wikipedia_birth_fields_reports_only_unavailable_values():
    assert missing_wikipedia_birth_fields(
        {
            "birth_year": 1980,
            "birth_month": 3,
            "birth_day": 4,
            "birth_place": "",
        }
    ) == ("birth place",)


def test_missing_wikipedia_birth_fields_supports_fully_partial_profile():
    assert missing_wikipedia_birth_fields({"birth_place": "Exampleville"}) == (
        "birth date",
    )
