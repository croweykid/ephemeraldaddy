from types import SimpleNamespace
import sqlite3

import pytest

from ephemeraldaddy.core.chart_data_fields import (
    ASTRO_DATA,
    ASTRO_DATA_DERIVED_FIELDS,
    ASTRO_DATA_INPUT_FIELDS,
    NONASTRAL_DATA,
    astro_data_recalculation_token,
    require_nonastral_data_fields,
)


def _chart(**overrides):
    values = {
        "dt": None,
        "birth_place": "London",
        "lat": 51.5,
        "lon": -0.12,
        "birthtime_unknown": False,
        "retcon_time_used": False,
        "retcon_hour": None,
        "retcon_minute": None,
        "rectification_range_used": False,
        "rectification_range_start_minute": None,
        "rectification_range_end_minute": None,
        "use_birth_time_data": True,
        "name": "Before",
        "alias": "Alias",
        "from_whence": "Somewhere",
        "chart_type": "personal",
        "data_rating": "AA",
        "tags": ["tag"],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_master_field_categories_are_disjoint_and_explicit():
    assert not ASTRO_DATA.intersection(NONASTRAL_DATA)
    assert ASTRO_DATA == ASTRO_DATA_INPUT_FIELDS | ASTRO_DATA_DERIVED_FIELDS
    assert {"dt", "birth_place", "lat", "lon", "birthtime_unknown"} <= ASTRO_DATA_INPUT_FIELDS
    assert {"human_design_type", "bazi_day_pillar", "positions"} <= ASTRO_DATA_DERIVED_FIELDS
    assert {"name", "alias", "from_whence", "chart_type", "data_rating"} <= NONASTRAL_DATA
    assert {
        "derived_positions",
        "enneagram_type_weights",
        "weirdness_score",
    } <= ASTRO_DATA_DERIVED_FIELDS
    assert {"profile_pic", "created_at", "is_current"} <= NONASTRAL_DATA


def test_every_persisted_chart_column_has_one_master_classification():
    from ephemeraldaddy.core import db

    connection = sqlite3.connect(":memory:")
    try:
        db._create_charts_table(connection)
        persisted_fields = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(charts)")
        }
    finally:
        connection.close()
    assert persisted_fields <= ASTRO_DATA | NONASTRAL_DATA


def test_nonastral_edits_do_not_change_astro_recalculation_token():
    before = _chart()
    after = _chart(
        name="After",
        alias="Other alias",
        from_whence="Elsewhere",
        chart_type="public_db",
        data_rating="DD",
        tags=["different"],
    )
    assert astro_data_recalculation_token(before) == astro_data_recalculation_token(after)


def test_astro_input_edit_changes_recalculation_token():
    assert astro_data_recalculation_token(_chart()) != astro_data_recalculation_token(
        _chart(lat=40.7)
    )


def test_narrow_nonastral_guard_rejects_astro_and_unclassified_fields(caplog):
    require_nonastral_data_fields({"tags", "sentiments"})
    with pytest.raises(ValueError), caplog.at_level("ERROR"):
        require_nonastral_data_fields("birth_place")
    with pytest.raises(ValueError):
        require_nonastral_data_fields("made_up_field")
    assert "Classify new persisted fields in chart_data_fields.py" in caplog.text
    assert "route ASTRO_DATA inputs through the Chart View calculation path" in caplog.text
