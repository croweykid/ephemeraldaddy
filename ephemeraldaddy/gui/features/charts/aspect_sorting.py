from __future__ import annotations

from ephemeraldaddy.core.interpretations import (
    ASPECT_BODY_ALIASES,
    ASPECT_SCORE_WEIGHTS,
    ASPECT_SORT_OPTIONS,
    NATAL_WEIGHT,
    aspect_score,
)

NATAL_ASPECT_SORT_OPTIONS = tuple(
    option for option in ASPECT_SORT_OPTIONS if option != "Duration"
)

_NATAL_POSITION_SORT_RANK = {
    body: index for index, body in enumerate(NATAL_WEIGHT.keys())
}

_ASPECT_TYPE_SORT_RANK = {
    atype: index for index, atype in enumerate(ASPECT_SCORE_WEIGHTS.keys())
}


def normalize_aspect_body(body: str) -> str:
    return ASPECT_BODY_ALIASES.get(body, body)


def aspect_position_rank(body: str) -> int:
    normalized = normalize_aspect_body(body)
    return _NATAL_POSITION_SORT_RANK.get(normalized, len(_NATAL_POSITION_SORT_RANK))


def aspect_type_rank(atype: str) -> int:
    normalized = str(atype).replace(" ", "_").lower()
    return _ASPECT_TYPE_SORT_RANK.get(normalized, len(_ASPECT_TYPE_SORT_RANK))


def natal_aspect_priority(asp: dict, planet_weights: dict[str, float] | None = None) -> float:
    return float(aspect_score(asp, planet_weights=planet_weights))


def _with_primary_position_endpoint(asp: dict) -> dict:
    """Return an aspect copy with the earlier natal body order in column 1.

    Generated aspect endpoint order can vary by calculation path, but the UI
    Position sort is meant to group by the first displayed body: Sun aspects,
    then Moon aspects, Mercury aspects, and so on.  Normalizing the endpoint
    order before sorting/displaying keeps the popout and Chart View outputs in
    the same body-order format.
    """

    p1_rank = aspect_position_rank(asp["p1"])
    p2_rank = aspect_position_rank(asp["p2"])
    if p2_rank < p1_rank:
        ordered = dict(asp)
        ordered["p1"], ordered["p2"] = asp["p2"], asp["p1"]
        return ordered
    return asp


def sort_natal_aspects(
    filtered_aspects: list[dict],
    sort_mode: str,
    planet_weights: dict[str, float] | None = None,
) -> list[dict]:
    if sort_mode == "Aspect":
        return sorted(
            filtered_aspects,
            key=lambda a: (
                aspect_type_rank(a["type"]),
                aspect_position_rank(a["p1"]),
                aspect_position_rank(a["p2"]),
                abs(float(a["delta"])),
            ),
        )
    if sort_mode == "Position":
        ordered_aspects = [_with_primary_position_endpoint(asp) for asp in filtered_aspects]
        return sorted(
            ordered_aspects,
            key=lambda a: (
                aspect_position_rank(a["p1"]),
                aspect_position_rank(a["p2"]),
                aspect_type_rank(a["type"]),
                abs(float(a["delta"])),
            ),
        )
    return sorted(
        filtered_aspects,
        key=lambda a: (
            natal_aspect_priority(a, planet_weights=planet_weights),
            -abs(float(a["delta"])),
            -aspect_type_rank(a["type"]),
        ),
        reverse=True,
    )
