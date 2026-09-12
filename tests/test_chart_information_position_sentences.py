import random

from ephemeraldaddy.core.interpretations import HOUSE_COLORS, PLANET_COLORS, SIGN_COLORS
from ephemeraldaddy.gui.features.chart_information.position_sentences import (
    build_position_sentence_model,
)


def test_untimed_position_model_omits_house_tokens():
    model = build_position_sentence_model(
        "Sun",
        "Aries",
        None,
        choose=random.Random(1).choice,
    )

    assert model is not None
    assert model.header == "Sun in Aries"
    assert len(model.lines) == 6
    assert all(
        color in {None, PLANET_COLORS["Sun"], SIGN_COLORS["Aries"]}
        for line in model.lines
        for _text, color in line
    )


def test_timed_position_model_contains_body_sign_and_house_colors():
    model = build_position_sentence_model(
        "Moon",
        "Cancer",
        4,
        choose=random.Random(2).choice,
    )

    assert model is not None
    assert model.header == "Moon in Cancer • House 4"
    assert len(model.lines) == 6
    colors = {color for line in model.lines for _text, color in line}
    assert PLANET_COLORS["Moon"] in colors
    assert SIGN_COLORS["Cancer"] in colors
    assert HOUSE_COLORS["4"] in colors


def test_position_model_reports_missing_reference_data():
    assert build_position_sentence_model("Unknown", "Nowhere", None) is None
