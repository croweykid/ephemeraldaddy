from ephemeraldaddy.core.composite import (
    AspectHit,
    AspectRuleSet,
    AspectType,
    BodyPosition,
    compute_aspects,
)
from ephemeraldaddy.gui.features.charts.personal_transit_popout import (
    OUT_OF_SIGN_TOOLTIP,
    append_out_of_sign_warning,
    decorate_personal_transit_output_text,
    is_out_of_sign_personal_transit_aspect,
)


TIGHT_MAJOR_RULES = AspectRuleSet(
    aspect_types=(
        AspectType("square", 90.0, 3.0),
        AspectType("trine", 120.0, 3.0),
    ),
    skip_same_body_name=False,
    context="transit_to_natal",
)


def _hit(left: float, right: float, aspect: str, orb: float = 0.0) -> AspectHit:
    return AspectHit(
        a=BodyPosition(name="Transit Sun", lon_deg=left),
        b=BodyPosition(name="Natal Mars", lon_deg=right),
        aspect=aspect,
        exactness=1.0,
        orb_deg=orb,
        applying_separating=None,
        weight=1.0,
    )


def test_boundary_aries_capricorn_trine_is_valid_but_flagged_out_of_sign():
    hits = compute_aspects(
        [BodyPosition(name="Transit Sun", lon_deg=29.0)],
        [BodyPosition(name="Natal Mars", lon_deg=270.0)],
        TIGHT_MAJOR_RULES,
    )

    assert len(hits) == 1
    assert hits[0].aspect == "trine"
    assert hits[0].orb_deg == 1.0
    assert is_out_of_sign_personal_transit_aspect(hits[0]) is True

    line, tooltip_span = append_out_of_sign_warning("Sun trine Mars", hits[0])
    assert line == "Sun trine Mars ⚠️"
    assert tooltip_span is not None
    assert tooltip_span["tooltip"] == OUT_OF_SIGN_TOOLTIP
    assert tooltip_span["span_start"] == len("Sun trine Mars ")
    assert tooltip_span["span_end"] == len(line)


def test_mid_sign_aries_capricorn_resolves_to_square_without_warning():
    hits = compute_aspects(
        [BodyPosition(name="Transit Sun", lon_deg=10.0)],
        [BodyPosition(name="Natal Mars", lon_deg=280.0)],
        TIGHT_MAJOR_RULES,
    )

    assert len(hits) == 1
    assert hits[0].aspect == "square"
    assert hits[0].orb_deg == 0.0
    assert is_out_of_sign_personal_transit_aspect(hits[0]) is False

    line, tooltip_span = append_out_of_sign_warning("Sun square Mars", hits[0])
    assert line == "Sun square Mars"
    assert tooltip_span is None


def test_personal_transit_output_appends_warning_only_to_out_of_sign_row():
    text = "\n".join(
        [
            "Personal Transit (Transit → Natal)",
            "",
            "Transit Sun (Aries H1) Trine Natal Mars (Capricorn H10) | orb 1.00°",
            "Transit Sun (Aries H1) Square Natal Mars (Capricorn H10) | orb 0.00°",
        ]
    )

    decorated = decorate_personal_transit_output_text(text)
    lines = decorated.splitlines()

    assert lines[2].endswith("⚠️")
    assert not lines[3].endswith("⚠️")
    assert decorate_personal_transit_output_text(decorated) == decorated


def test_non_sign_based_harmonics_are_not_labeled_out_of_sign():
    assert is_out_of_sign_personal_transit_aspect(
        _hit(0.0, 72.0, "quintile")
    ) is False
