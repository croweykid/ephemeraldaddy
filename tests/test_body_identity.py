from ephemeraldaddy.core.body_identity import (
    CANONICAL_LILITH_BODIES,
    MEAN_LILITH,
    NATURAL_LILITH,
    OSCULATING_LILITH,
    canonicalize_semantic_body_name,
    is_canonical_lilith_body,
)


def test_plain_legacy_lilith_means_osculating_lilith() -> None:
    assert canonicalize_semantic_body_name("Lilith") == OSCULATING_LILITH
    assert canonicalize_semantic_body_name("lilith") == OSCULATING_LILITH
    assert canonicalize_semantic_body_name("  LILITH  ") == OSCULATING_LILITH


def test_historical_true_lilith_means_osculating_lilith() -> None:
    assert canonicalize_semantic_body_name("True Lilith") == OSCULATING_LILITH
    assert canonicalize_semantic_body_name("true lilith") == OSCULATING_LILITH
    assert canonicalize_semantic_body_name("Lilith (true)") == OSCULATING_LILITH
    assert canonicalize_semantic_body_name("Lilith (osculating)") == OSCULATING_LILITH
    assert canonicalize_semantic_body_name("Lilith (mean)") == MEAN_LILITH


def test_three_canonical_lilith_identities_never_collapse() -> None:
    assert CANONICAL_LILITH_BODIES == {
        MEAN_LILITH,
        OSCULATING_LILITH,
        NATURAL_LILITH,
    }
    assert canonicalize_semantic_body_name(MEAN_LILITH) == MEAN_LILITH
    assert canonicalize_semantic_body_name(OSCULATING_LILITH) == OSCULATING_LILITH
    assert canonicalize_semantic_body_name(NATURAL_LILITH) == NATURAL_LILITH


def test_generic_black_moon_lilith_is_not_guessed() -> None:
    # Historically ambiguous: provenance or recalculation is required.
    assert canonicalize_semantic_body_name("Black Moon Lilith") == "Black Moon Lilith"


def test_unknown_body_names_pass_through() -> None:
    assert canonicalize_semantic_body_name("  Chiron  ") == "Chiron"
    assert canonicalize_semantic_body_name("") == ""


def test_canonical_lilith_predicate_requires_canonical_name() -> None:
    assert is_canonical_lilith_body(MEAN_LILITH)
    assert is_canonical_lilith_body(OSCULATING_LILITH)
    assert is_canonical_lilith_body(NATURAL_LILITH)
    assert not is_canonical_lilith_body("Lilith")
    assert not is_canonical_lilith_body("True Lilith")
