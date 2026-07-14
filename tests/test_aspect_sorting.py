from ephemeraldaddy.gui.features.charts.aspect_sorting import sort_natal_aspects


def _aspect(p1: str, p2: str, aspect_type: str = "trine", delta: float = 1.0) -> dict:
    return {"p1": p1, "p2": p2, "type": aspect_type, "angle": 120.0, "delta": delta}


def test_position_sort_groups_by_primary_body_even_when_body_started_in_second_column():
    aspects = [
        _aspect("Saturn", "Moon", "square", 0.8),
        _aspect("Venus", "Sun", "trine", 1.2),
        _aspect("Mars", "Mercury", "sextile", 0.3),
        _aspect("Jupiter", "Moon", "opposition", 0.5),
        _aspect("Saturn", "Sun", "conjunction", 0.2),
    ]

    sorted_aspects = sort_natal_aspects(aspects, "Position")

    assert [(asp["p1"], asp["p2"]) for asp in sorted_aspects] == [
        ("Sun", "Venus"),
        ("Sun", "Saturn"),
        ("Moon", "Jupiter"),
        ("Moon", "Saturn"),
        ("Mercury", "Mars"),
    ]
