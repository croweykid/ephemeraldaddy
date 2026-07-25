"""Shared tag-category names and prefix normalization."""

from __future__ import annotations


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
    prefix: display_name for display_name, prefix in TAG_CATEGORY_OPTIONS
}
TAG_CATEGORY_PREFIXES = frozenset(TAG_CATEGORY_DISPLAY_NAMES)

# Historical spellings resolve to the same canonical prefix and display name.
TAG_CATEGORY_PREFIX_ALIASES: dict[str, str] = {
    "life events": "life_events",
    "life-events": "life_events",
    "characters": "character",
    "hobby": "hobbies",
    "personality": "personality_types",
    "genre": "genres",
    "places": "place",
}


def tag_category_display_name(prefix: str) -> str:
    """Return the shared display name for a tag-category prefix."""
    clean_prefix = str(prefix or "").strip()
    if not clean_prefix:
        return ""
    normalized_prefix = clean_prefix.casefold()
    canonical_prefix = TAG_CATEGORY_PREFIX_ALIASES.get(normalized_prefix, normalized_prefix)
    return TAG_CATEGORY_DISPLAY_NAMES.get(
        canonical_prefix,
        clean_prefix.replace("_", " ").replace("-", " ").title(),
    )
