"""Canonical astrological body identities and legacy semantic aliases.

This module deliberately separates *semantic identity normalization* from
stored-coordinate migration.  It is safe to use when interpreting trait
criteria, interpretation keys, aspect criteria, filters, user-entered body
names, and other references whose meaning is a body identity.

It MUST NOT be used to assert that a historical coordinate stored under the
plain key ``"Lilith"`` was calculated with a particular Swiss Ephemeris
algorithm.  Historical position/cache records with ambiguous Lilith provenance
must be recalculated from the chart's astronomical inputs during the three-
Lilith migration.
"""

from __future__ import annotations


MEAN_LILITH = "Mean Lilith"
OSCULATING_LILITH = "Osculating Lilith"
NATURAL_LILITH = "Natural Lilith"

CANONICAL_LILITH_BODIES = frozenset(
    {
        MEAN_LILITH,
        OSCULATING_LILITH,
        NATURAL_LILITH,
    }
)

# Permanent semantic compatibility contract.
#
# Product decision: a legacy *identity reference* to plain ``Lilith`` means
# Osculating Lilith.  ``True Lilith`` was the historical UI/trait label for the
# same osculating-apogee interpretation, so it resolves identically.
#
# Do NOT add ``Black Moon Lilith`` here without provenance.  That label has
# historically been used generically and, in EphemeralDaddy, has also been
# produced by the old mode-switching implementation.  Ambiguous stored chart
# coordinates must be regenerated instead of guessed.
LEGACY_SEMANTIC_BODY_ALIASES: dict[str, str] = {
    "Lilith": OSCULATING_LILITH,
    "True Lilith": OSCULATING_LILITH,
}

_LEGACY_SEMANTIC_BODY_ALIASES_CASEFOLD = {
    alias.casefold(): canonical
    for alias, canonical in LEGACY_SEMANTIC_BODY_ALIASES.items()
}


def canonicalize_semantic_body_name(value: object) -> str:
    """Return the canonical body identity for a semantic body-name reference.

    Canonical names remain distinct.  Legacy plain ``Lilith`` and historical
    ``True Lilith`` references permanently resolve to ``Osculating Lilith``.
    Unknown names pass through after surrounding whitespace is removed.

    This function is intentionally *not* a stored-position migration helper.
    Never use it to relabel an old ``positions["Lilith"]`` longitude as an
    osculating longitude; recalculate all three Lilith positions instead.
    """

    token = str(value or "").strip()
    if not token:
        return ""
    return _LEGACY_SEMANTIC_BODY_ALIASES_CASEFOLD.get(token.casefold(), token)


def is_canonical_lilith_body(value: object) -> bool:
    """Return whether ``value`` is already one of the three canonical Liliths."""

    return str(value or "").strip() in CANONICAL_LILITH_BODIES
