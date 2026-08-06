"""Shared helpers for semantic language formatting."""

from __future__ import annotations

from typing import Any, NamedTuple


class PronounSet(NamedTuple):
    """A chart subject's common English pronoun forms."""

    subject: str
    object: str
    possessive: str
    reflexive: str

    @property
    def slash_form(self) -> str:
        """Return pronouns in compact slash-delimited display form."""
        return "/".join(self)

    @property
    def possessive_determiner(self) -> str:
        """Return the attributive possessive used before a noun."""
        return {
            "she": "her",
            "he": "his",
            "they": "their",
        }.get(self.subject, self.possessive)


SHE_HER_HERS = PronounSet("she", "her", "hers", "herself")
HE_HIM_HIS = PronounSet("he", "him", "his", "himself")
THEY_THEM_THEIR = PronounSet("they", "them", "their", "themself")

_GENDER_PRONOUNS = {
    "F": SHE_HER_HERS,
    "AMAB-F": SHE_HER_HERS,
    "M": HE_HIM_HIS,
    "AFAB-M": HE_HIM_HIS,
    "AFAB-NB": THEY_THEM_THEIR,
    "AMAB-NB": THEY_THEM_THEIR,
}


def ordinal_suffix(number: int) -> str:
    """Return the English ordinal suffix for an integer."""
    absolute_number = abs(number)
    if 10 <= absolute_number % 100 <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(absolute_number % 10, "th")


def format_ordinal(number: int) -> str:
    """Return an integer with its English ordinal suffix, without punctuation."""
    return f"{number}{ordinal_suffix(number)}"


def normalize_gender_code(gender: object) -> str:
    """Return a normalized chart gender code for semantic helpers."""
    return str(gender or "").strip().upper().replace("_", "-")


def pronouns_for_gender(gender: object, *, default: PronounSet | None = None) -> PronounSet | None:
    """Translate a chart gender value into the configured pronoun set."""
    return _GENDER_PRONOUNS.get(normalize_gender_code(gender), default)


def pronouns_for_chart(chart: Any, *, default: PronounSet | None = None) -> PronounSet | None:
    """Translate a chart object's ``gender`` attribute into the configured pronoun set."""
    return pronouns_for_gender(getattr(chart, "gender", None), default=default)
