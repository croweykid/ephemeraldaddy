from ephemeraldaddy.analysis.dnd.species_assigner_v2 import SpeciesAssigner
from ephemeraldaddy.core.dominance import (
    dominant_element_labels_from_weights,
    dominant_mode_labels_from_weights,
)


def test_dominant_element_labels_require_above_quarter_share_not_top_three():
    weights = {"Fire": 0.21, "Earth": 0.36, "Air": 0.13, "Water": 0.30}

    assert dominant_element_labels_from_weights(weights) == ["Earth", "Water"]


def test_dominant_mode_labels_require_top_mode_above_third_share():
    weights = {"cardinal": 0.34, "fixed": 0.43, "mutable": 0.22}

    assert dominant_mode_labels_from_weights(weights) == ["fixed"]


def test_plasmoid_water_air_and_mutable_evidence_require_dominance():
    assigner = SpeciesAssigner()
    feats = {
        "element_ratios": {"Fire": 0.21, "Earth": 0.36, "Air": 0.13, "Water": 0.30},
        "mode_ratios": {"cardinal": 0.34, "fixed": 0.43, "mutable": 0.22},
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
        "prominence": {"Neptune": 1.0, "Uranus": 1.0},
        "balance_score": 0.8,
        "spikiness": 0.5,
        "dominant_ratio": 0.36,
        "taurus_stellium_count": 0,
        "taurus_dominance_weight": 0.0,
        "tight_outer_to_identity": [],
        "dominant_elements": dominant_element_labels_from_weights(
            {"Fire": 0.21, "Earth": 0.36, "Air": 0.13, "Water": 0.30}
        ),
        "dominant_modes": dominant_mode_labels_from_weights(
            {"cardinal": 0.34, "fixed": 0.43, "mutable": 0.22}
        ),
    }
    cards = assigner._score_families(
        {"Neptune": {"sign": "Pisces", "lon": 0.0}, "Uranus": {"sign": "Aquarius", "lon": 0.0}},
        [{"p1": "Neptune", "p2": "Uranus", "aspect": "conjunction", "orb": 0.0}],
        feats,
    )

    plasmoid_reasons = cards["Plasmoid"].reasons
    assert "Neptune gives fluidity." in plasmoid_reasons
    assert "Uranus gives weird embodiment." in plasmoid_reasons
    assert "Water/Air is the main lane." not in plasmoid_reasons
    assert "Mutable emphasis helps." not in plasmoid_reasons
