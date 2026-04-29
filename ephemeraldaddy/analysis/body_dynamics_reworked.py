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
MAJOR_BODY_PAIR_TONE = {
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
assert len(MAJOR_BODY_PAIR_TONE) == EXPECTED_UNORDERED_PAIR_COUNT == 45


MAJOR_BODY_PAIR_ASPECT_POLARITY = {
    pair: {
        "enabling": (
            ASPECT_FRICTION["harmonious"]["aspects"]
            | (ASPECT_FRICTION["neutral/variable"]["aspects"] if tone == "enabling_pair" else frozenset())
        ),
        "antagonizing": (
            ASPECT_FRICTION["conflicted"]["aspects"]
            | (ASPECT_FRICTION["neutral/variable"]["aspects"] if tone == "antagonizing_pair" else frozenset())
        ),
        "escalating": (
            ASPECT_FRICTION["neutral/variable"]["aspects"] if tone == "volatile_pair" else frozenset()
        ),
    }
    for pair, tone in MAJOR_BODY_PAIR_TONE.items()
}

#the scoring gist is something like: aspect_score = pair_polarity_sign * orb_weight * aspect_base_weight * sqrt(dom_a * dom_b)