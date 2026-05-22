"""Reference mapping from in-app emoji glyphs to PNG icon assets.

This map is the first step in replacing direct emoji rendering with
bundled PNG artwork under ``ephemeraldaddy/graphics/emoji``.
"""

from __future__ import annotations

from pathlib import Path

EMOJI_DIR = Path(__file__).resolve().parent / "emoji"

VARIATION_SELECTOR_15 = "︎"
VARIATION_SELECTOR_16 = "️"

# Primary mapping for emojis already used across the UI.
EMOJI_TO_PNG: dict[str, str] = {
    "🏠": "house-openmoji-512.png",
    "🪐": "ringed-planet-noto-512.png",
    "🔘": "bullseye-fluentflat-512.png",
    "🐉": "dragon-noto-512.png",
    "🏷": "label-twemoji-512.png",
    "⚔": "crossed-swords-twemoji-512.png",
    "🪷": "lotus-openmoji-512.png",
    "🌍": "globe-showing-europe-africa-blobmoji-512.png",
    "🐣": "hatching-chick-fluentflat-512.png",
    "🚫": "prohibited-twemoji-512.png",
    "💭": "thought-balloon-noto-512.png",
    "⚙": "gear-blobmoji-512.png",
    "🌀": "counterclockwise-arrows-button-blobmoji-512.png",
    "🌟": "glowing-star-noto-512.png",
    "🧓": "older-person-twemoji-512.png",
    "🧩": "puzzle-piece-noto-512.png",
    "💎": "gem-stone-blobmoji-512.png",
    "📊": "bar-chart-twemoji-512.png",
    "🗄": "card-file-box-twemoji-512.png",
    "💔": "broken-heart-twemoji-512.png",
    "📚": "books-noto-512.png",
    "📐": "triangular-ruler-noto-512.png",
    "💖": "sparkling-heart-fluentflat-512.png",
    "💬": "speech-balloon-blobmoji-512.png",
    "🌞": "sun-with-face-blobmoji-512.png",
    "🧬": "dna-noto-512.png",
    "🕖": "seven-oclock-blobmoji-512.png",
    "❌": "cross-mark-blobmoji-512.png",
    "👥": "busts-in-silhouette-blobmoji-512.png",
    "♻": "recycling-symbol-fluentflat-512.png",
    "📝": "memo-blobmoji-512.png",
    "🔮": "crystal-ball-noto-512.png",
    "🔎": "magnifying-glass-tilted-right-blobmoji-512.png",
    "🫂": "people-holding-hands-twemoji-512.png",
}

# Compatibility aliases for variants currently used in some UI strings.
EMOJI_ALIASES: dict[str, str] = {
    "🌎": "🌍",
    "🌐": "🌍",
    "🗂": "🗄",
    "👯": "👥",
    "👬": "👥",
    "✗": "❌",
    "✕": "❌",
    "✓": "✅",  # currently no PNG equivalent available yet
    "🕗": "🕖",
}


def _normalize_emoji_lookup_key(emoji: str) -> str:
    """Normalize variation-selector emoji forms before map lookup."""
    return emoji.replace(VARIATION_SELECTOR_15, "").replace(VARIATION_SELECTOR_16, "")


def emoji_png_path(emoji: str) -> Path | None:
    """Return the PNG path for an emoji (or alias), if mapped."""
    normalized = _normalize_emoji_lookup_key(emoji)
    key = EMOJI_ALIASES.get(normalized, normalized)
    filename = EMOJI_TO_PNG.get(key)
    if not filename:
        return None
    return EMOJI_DIR / filename
