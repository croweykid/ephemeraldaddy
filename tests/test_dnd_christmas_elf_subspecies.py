from ephemeraldaddy.analysis.dnd.dnd_definitions import FAMILY_SUBTYPES, SPECIES_DESCRIPTIONS
from ephemeraldaddy.analysis.dnd.species_assigner_v2 import SpeciesAssigner


def _base_feats():
    return {
        "element_ratios": {"Fire": 0.0, "Earth": 0.30, "Air": 0.30, "Water": 0.0},
        "sign_ratios": {"Sagittarius": 0.30, "Capricorn": 0.30},
        "house_ratios": {5: 0.30, 6: 0.30, 10: 0.30, 11: 0.30},
        "chart_uses_houses": True,
        "prominence": {"Mercury": 0.30, "Saturn": 0.30},
        "mode_ratios": {"cardinal": 0.0},
        "spikiness": 0.0,
    }


def test_christmas_elf_is_available_to_elf_and_gnome_families():
    assert "Christmas Elf" in FAMILY_SUBTYPES["Elf"]
    assert "Christmas Elf" in FAMILY_SUBTYPES["Gnome"]
    assert SPECIES_DESCRIPTIONS["Elf::Christmas Elf"]
    assert SPECIES_DESCRIPTIONS["Gnome::Christmas Elf"]


def test_christmas_elf_filter_can_select_from_elf_or_gnome_family():
    assigner = SpeciesAssigner()
    feats = _base_feats()

    for family in ("Elf", "Gnome"):
        subtype, evidence = assigner._pick_subtype(family, {}, [], feats)
        assert subtype == "Christmas Elf"
        assert any("Craft, festivity, and factory" in item for item in evidence)


def test_christmas_elf_ignores_house_markers_when_chart_does_not_use_houses():
    assigner = SpeciesAssigner()
    feats = {
        "element_ratios": {"Fire": 0.0, "Earth": 0.0, "Air": 0.0, "Water": 0.0},
        "sign_ratios": {},
        "house_ratios": {5: 0.60, 6: 0.60, 10: 0.60, 11: 0.60},
        "chart_uses_houses": False,
        "prominence": {},
        "mode_ratios": {"cardinal": 0.0},
        "spikiness": 0.0,
    }

    elf_subtype, _ = assigner._pick_subtype("Elf", {}, [], feats)
    gnome_subtype, _ = assigner._pick_subtype("Gnome", {}, [], feats)

    assert elf_subtype != "Christmas Elf"
    assert gnome_subtype != "Christmas Elf"
