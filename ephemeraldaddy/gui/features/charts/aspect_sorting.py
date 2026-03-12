from __future__ import annotations

from ephemeraldaddy.core.interpretations import (
    ASPECT_BODY_ALIASES,
    ASPECT_SCORE_WEIGHTS,
    ASPECT_SORT_OPTIONS,
    NATAL_WEIGHT,
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


def natal_aspect_priority(asp: dict) -> float:
    normalized_type = str(asp.get("type", "")).replace(" ", "_").lower()
    aspect_weight = float(ASPECT_SCORE_WEIGHTS.get(normalized_type, 0.0))
    p1_weight = float(NATAL_WEIGHT.get(normalize_aspect_body(asp.get("p1", "")), 1.0))
    p2_weight = float(NATAL_WEIGHT.get(normalize_aspect_body(asp.get("p2", "")), 1.0))
    return aspect_weight + p1_weight + p2_weight


def sort_natal_aspects(filtered_aspects: list[dict], sort_mode: str) -> list[dict]:
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
        return sorted(
            filtered_aspects,
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
            natal_aspect_priority(a),
            -abs(float(a["delta"])),
            -aspect_type_rank(a["type"]),
        ),
        reverse=True,
    )
