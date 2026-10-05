from ephemeraldaddy.gui.features.charts import trait_predictions_core as core


def _trait(profile_overrides=None):
    profile = {
        "name": "Agreeable",
        "description": "Standard description",
        "antisigns": {"Aries": 8},
        "antithetical_trait": "Combative",
        "antitrait_description": "Inclined toward confrontation rather than accommodation.",
    }
    if profile_overrides:
        profile.update(profile_overrides)
    return {
        "name": "Agreeable",
        "color": "#cc99ff",
        "description": "Standard description",
        "profile": profile,
        "samples": [50, 0],
    }


def _metadata(deviation=-12.0):
    return {
        "likelihoods": {"Agreeable": 38.0},
        "database_averages": {"Agreeable": 50.0},
        "deviations": {"Agreeable": deviation},
    }


def test_negative_deviation_becomes_above_average_antithetical_row():
    rows = core._trait_prediction_rows_from_metadata([_trait()], _metadata())

    assert len(rows) == 1
    row = rows[0]
    assert row["name"] == "Agreeable"
    assert row["display_name"] == "Combative"
    assert row["likelihood"] == 62.0
    assert row["database_average"] == 50.0
    assert row["deviation"] == 12.0
    assert row["direction"] == "above"
    assert row["antithetical"] is True


def test_antithetical_conversion_requires_nonempty_anti_factors():
    rows = core._trait_prediction_rows_from_metadata(
        [_trait({"antisigns": {}})],
        _metadata(),
    )

    assert len(rows) == 1
    assert rows[0]["name"] == "Agreeable"
    assert "display_name" not in rows[0]
    assert rows[0]["deviation"] == -12.0
    assert rows[0]["direction"] == "below"
    assert rows[0]["antithetical"] is False


def test_antithetical_conversion_requires_explicit_non_null_property():
    missing = _trait()
    missing["profile"].pop("antithetical_trait")
    null_value = _trait({"antithetical_trait": None})

    missing_row = core._trait_prediction_rows_from_metadata([missing], _metadata())[0]
    null_row = core._trait_prediction_rows_from_metadata([null_value], _metadata())[0]

    assert missing_row["direction"] == "below"
    assert missing_row["antithetical"] is False
    assert null_row["direction"] == "below"
    assert null_row["antithetical"] is False


def test_antithetical_info_uses_antitrait_description_not_standard_description():
    rendered = core._trait_info_html(_trait(), antithetical=True)

    assert "Combative" in rendered
    assert "Inclined toward confrontation rather than accommodation." in rendered
    assert "Standard description" not in rendered


def test_missing_antitrait_description_never_falls_back_to_standard_description():
    rendered = core._trait_info_html(
        _trait({"antitrait_description": None}),
        antithetical=True,
    )

    assert "no antitrait description provided" in rendered
    assert "Standard description" not in rendered
