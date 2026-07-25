"""Shared tag-category names and prefix normalization."""

from __future__ import annotations


# Property Manager options retain their UI-specific labels (including the
# Trait icon).  Other views historically use slightly different wording; those
# definitions also live below rather than being silently collapsed together.
TAG_CATEGORY_OPTIONS: tuple[tuple[str, str], ...] = (
    ("Occupation", "occupation"),
    ("Trait", "trait"),
    ("Reputation", "reputation"),
    ("Affiliation", "affiliation"),
    ("Crime", "crime"),
    ("Life Events", "life_events"),
    ("Characters Played", "character"),
    ("Hobbies", "hobbies"),
    ("Typology", "personality_types"),
    ("Genres", "genres"),
    ("Place", "place"),
)

TAG_CATEGORY_DISPLAY_NAMES: dict[str, str] = {
    "occupation": "Occupation",
    "trait": "Trait",
    "reputation": "Reputation",
    "affiliation": "Affiliation",
    "crime": "Crime",
    "life_events": "Life Events",
    "character": "Characters Played",
    "hobbies": "Hobbies",
    "personality_types": "Typology",
    "genres": "Genres",
    "place": "Place",
}
TAG_CATEGORY_PREFIXES = frozenset(TAG_CATEGORY_DISPLAY_NAMES)

# Database Analytics deliberately retains its established shorter/pluralized
# labels and recognition of explicit uncategorized/unknown prefixes.
TAG_DISTRIBUTION_CATEGORY_ORDER: tuple[str, ...] = (
    "Affiliation",
    "Characters Played",
    "Crime",
    "Genres",
    "Hobbies",
    "Life Events",
    "Occupation",
    "Places",
    "Reputation",
    "Trait",
    "Typology",
    "Uncategorized",
)
TAG_DISTRIBUTION_CATEGORY_ALIASES: dict[str, str] = {
    "occupation": "Occupation",
    "trait": "Trait",
    "reputation": "Reputation",
    "affiliation": "Affiliation",
    "crime": "Crime",
    "life events": "Life Events",
    "life_events": "Life Events",
    "life-events": "Life Events",
    "characters": "Characters",
    "character": "Characters",
    "hobbies": "Hobbies",
    "hobby": "Hobbies",
    "personality_types": "Typology",
    "genres": "Genres",
    "genre": "Genres",
    "places": "Places",
    "place": "Places",
    "uncategorized": "Uncategorized",
    "unknown": "Uncategorized",
}


def tag_category_display_name(prefix: str) -> str:
    """Return the shared display name for a tag-category prefix."""
    clean_prefix = str(prefix or "").strip()
    if not clean_prefix:
        return ""
    return TAG_CATEGORY_DISPLAY_NAMES.get(
        clean_prefix.casefold(),
        clean_prefix.replace("_", " ").replace("-", " ").title(),
    )
