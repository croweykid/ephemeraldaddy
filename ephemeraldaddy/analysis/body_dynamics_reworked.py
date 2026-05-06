from ephemeraldaddy.core.interpretations import (ASPECT_FRICTION,PLANET_ORDER)

BODY_INDEX = {body: i for i, body in enumerate(PLANET_ORDER)}

def normalize_body_pair(a: str, b: str) -> tuple[str, str]:
    """
    Canonicalize pair order for tuple-key lookup.
    """
    return tuple(sorted((a, b), key=BODY_INDEX.__getitem__))

# Pair-tone prior:
# - enabling_pair: conjunction / semisextile are treated as enabling
# - antagonizing_pair: conjunction / semisextile are treated as antagonizing
# - volatile_pair: conjunction / semisextile remain escalating
#
# This is an opinionated prior, not sacred scripture. It is meant to drive scoring.
BODY_PAIR_DYNAMICS = {
    # Sun
    ("Sun", "Moon"): "enabling_pair",
    ("Sun", "Mercury"): "enabling_pair",
    ("Sun", "Venus"): "enabling_pair",
    ("Sun", "Mars"): "volatile_pair",
    ("Sun", "Jupiter"): "enabling_pair",
    ("Sun", "Saturn"): "antagonizing_pair",
    ("Sun", "Uranus"): "volatile_pair",
    ("Sun", "Neptune"): "volatile_pair",
    ("Sun", "Pluto"): "volatile_pair",

    # Moon
    ("Moon", "Mercury"): "enabling_pair",
    ("Moon", "Venus"): "enabling_pair",
    ("Moon", "Mars"): "antagonizing_pair",
    ("Moon", "Jupiter"): "enabling_pair",
    ("Moon", "Saturn"): "antagonizing_pair",
    ("Moon", "Uranus"): "antagonizing_pair",
    ("Moon", "Neptune"): "volatile_pair",
    ("Moon", "Pluto"): "antagonizing_pair",

    # Mercury
    ("Mercury", "Venus"): "enabling_pair",
    ("Mercury", "Mars"): "antagonizing_pair",
    ("Mercury", "Jupiter"): "enabling_pair",
    ("Mercury", "Saturn"): "volatile_pair",
    ("Mercury", "Uranus"): "enabling_pair",
    ("Mercury", "Neptune"): "volatile_pair",
    ("Mercury", "Pluto"): "volatile_pair",

    # Venus
    ("Venus", "Mars"): "volatile_pair",
    ("Venus", "Jupiter"): "enabling_pair",
    ("Venus", "Saturn"): "antagonizing_pair",
    ("Venus", "Uranus"): "antagonizing_pair",
    ("Venus", "Neptune"): "volatile_pair",
    ("Venus", "Pluto"): "antagonizing_pair", #maybe volatile.

    # Mars
    ("Mars", "Jupiter"): "enabling_pair",
    ("Mars", "Saturn"): "antagonizing_pair",
    ("Mars", "Uranus"): "antagonizing_pair",
    ("Mars", "Neptune"): "antagonizing_pair",
    ("Mars", "Pluto"): "volatile_pair",

    # Jupiter
    ("Jupiter", "Saturn"): "volatile_pair",
    ("Jupiter", "Uranus"): "enabling_pair",
    ("Jupiter", "Neptune"): "volatile_pair",
    ("Jupiter", "Pluto"): "volatile_pair",

    # Saturn
    ("Saturn", "Uranus"): "antagonizing_pair",
    ("Saturn", "Neptune"): "antagonizing_pair",
    ("Saturn", "Pluto"): "antagonizing_pair",

    # Uranus
    ("Uranus", "Neptune"): "volatile_pair",
    ("Uranus", "Pluto"): "volatile_pair",

    # Neptune
    ("Neptune", "Pluto"): "volatile_pair",
}


EXPECTED_UNORDERED_PAIR_COUNT = len(PLANET_ORDER) * (len(PLANET_ORDER) - 1) // 2
assert len(BODY_PAIR_DYNAMICS) == EXPECTED_UNORDERED_PAIR_COUNT == 45

PAIR_TONE_DISTRIBUTION = {
    "enabling_pair": {
        "enabling_aspect":     {"Enabling": 0.85, "Antagonizing": 0.00, "Escalating": 0.15},
        "antagonizing_aspect": {"Enabling": 0.10, "Antagonizing": 0.65, "Escalating": 0.25},
        "escalating_aspect":   {"Enabling": 0.60, "Antagonizing": 0.00, "Escalating": 0.40},
    },
    "antagonizing_pair": {
        "enabling_aspect":     {"Enabling": 0.55, "Antagonizing": 0.20, "Escalating": 0.25},
        "antagonizing_aspect": {"Enabling": 0.00, "Antagonizing": 0.80, "Escalating": 0.20},
        "escalating_aspect":   {"Enabling": 0.10, "Antagonizing": 0.45, "Escalating": 0.45},
    },
    "volatile_pair": {
        "enabling_aspect":     {"Enabling": 0.65, "Antagonizing": 0.00, "Escalating": 0.35},
        "antagonizing_aspect": {"Enabling": 0.00, "Antagonizing": 0.55, "Escalating": 0.45},
        "escalating_aspect":   {"Enabling": 0.25, "Antagonizing": 0.25, "Escalating": 0.50},
    },
}
ASPECT_BUCKET_KEYS = {
    "harmonious": "enabling_aspect",
    "conflicted": "antagonizing_aspect",
    "neutral/variable": "escalating_aspect",
}


PAIR_TYPE_DISTRIBUTION = {
    pair: {
        aspect_name: PAIR_TONE_DISTRIBUTION[tone][ASPECT_BUCKET_KEYS[bucket_name]]
        for bucket_name, bucket_data in ASPECT_FRICTION.items()
        for aspect_name in bucket_data.get("aspects", frozenset())
    }
    for pair, tone in BODY_PAIR_DYNAMICS.items()
}

#to add:
#the scoring gist is something like: aspect_score = pair_polarity_sign * orb_weight * aspect_base_weight * sqrt(dom_a * dom_b)
