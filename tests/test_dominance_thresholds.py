from ephemeraldaddy.analysis.dnd.species_assigner_v2 import SpeciesAssigner
from ephemeraldaddy.core.dominance import (
    dominant_element_labels_from_weights,
    dominant_mode_labels_from_weights,
)

SAMPLE_ELEMENT_RATIOS = {"Fire": 0.21, "Earth": 0.36, "Air": 0.13, "Water": 0.30}
SAMPLE_MODE_RATIOS = {"cardinal": 0.34, "fixed": 0.43, "mutable": 0.22}


def _sample_feats(**overrides):
    feats = {
        "element_ratios": SAMPLE_ELEMENT_RATIOS,
        "mode_ratios": SAMPLE_MODE_RATIOS,
        "sign_ratios": {},
        "trait_ratios": {
            "mute": 0.0,
            "humane": 0.0,
            "bestial": 0.0,
            "feral": 0.0,
            "quadrupedian": 0.0,
            "bicorporeal": 0.0,
        },
        "house_ratios": {},
        "prominence": {},
        "balance_score": 0.8,
        "spikiness": 0.5,
        "dominant_ratio": 0.36,
        "taurus_stellium_count": 0,
        "taurus_dominance_weight": 0.0,
        "tight_outer_to_identity": [],
        "dominant_elements": dominant_element_labels_from_weights(SAMPLE_ELEMENT_RATIOS),
        "dominant_modes": dominant_mode_labels_from_weights(SAMPLE_MODE_RATIOS),
    }
    feats.update(overrides)
    return feats


def test_dominant_element_labels_require_above_quarter_share_not_top_three():
    assert dominant_element_labels_from_weights(SAMPLE_ELEMENT_RATIOS) == ["Earth", "Water"]


def test_dominant_mode_labels_require_top_mode_above_third_share():
    assert dominant_mode_labels_from_weights(SAMPLE_MODE_RATIOS) == ["fixed"]


def test_plasmoid_water_air_and_mutable_evidence_require_dominance():
    assigner = SpeciesAssigner()
    cards = assigner._score_families(
        {"Neptune": {"sign": "Pisces", "lon": 0.0}, "Uranus": {"sign": "Aquarius", "lon": 0.0}},
        [{"p1": "Neptune", "p2": "Uranus", "aspect": "conjunction", "orb": 0.0}],
        _sample_feats(prominence={"Neptune": 1.0, "Uranus": 1.0}),
    )

    plasmoid_reasons = cards["Plasmoid"].reasons
    assert "Neptune gives fluidity." in plasmoid_reasons
    assert "Uranus gives weird embodiment." in plasmoid_reasons
    assert "Water/Air is the main lane." not in plasmoid_reasons
    assert "Mutable emphasis helps." not in plasmoid_reasons


def test_cosmid_air_water_evidence_requires_both_elements_to_be_dominant():
    assigner = SpeciesAssigner()
    cards = assigner._score_families(
        {},
        [],
        _sample_feats(
            prominence={"Uranus": 1.0, "Neptune": 1.0, "Pluto": 1.0},
            house_ratios={8: 0.4, 11: 0.4, 12: 0.4},
            tight_outer_to_identity=[("Uranus", "AS", 1.0)],
        ),
    )

    cosmid_reasons = cards["Cosmids"].reasons
    assert "Outer-planet emphasis (Uranus/Neptune/Pluto) helps Cosmids." in cosmid_reasons
    assert "Dominant Air/Water helps the unearthly register." not in cosmid_reasons
    assert "Liminal houses (8th/11th/12th) reinforce it." in cosmid_reasons
