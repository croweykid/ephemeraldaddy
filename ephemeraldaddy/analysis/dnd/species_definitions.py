from __future__ import annotations

from typing import Dict, List

from ephemeraldaddy.analysis.dnd.dnd_definitions import SPECIES_SUBVARIANT_EXPLAINER_TEMPLATE

SPECIES_FAMILIES: List[str] = [
    "Aasimar",
    "Birdfolk",
    "Canids",
    "Cosmids",
    "Cyborgs",
    "Cyclops",
    "Dragons",
    "Dwarf",
    "Elf",
    "Fey",
    "Genasi",
    "Spirits",
    "Gnome",
    "Half-orcs",
    "Halfling",
    "Human",
    "Tabaxi",
    "Lizardfolk (Reptilians)",
    "Merfolk",
    "Minotaur",
    "Nymph",
    "Ogres",
    "Orcs",
    "Plasmoid",
    "Robots",
    "Rodentfolk",
    "Shapeshifter",
    "Skeleton",
    "Stone People (Golems)",
    "Succubi/Incubi",
    "Tiefling",
    "Triton",
    "Vampire",
    "Yuan-Ti (Serpentine)",
]

FAMILY_SUBTYPES: Dict[str, List[str]] = {
    "Aasimar": ["Protector", "Scourge", "Fallen"],
    "Birdfolk": ["Kenku", "Owlin", "Aarakocra", "Other (non-owl, non-kenku, non-aarakocra)"],
    "Canids": ["Shepherd Dogs", "Wolfkin", "Gnolls", "Houndfolk"],
    "Cosmids": ["Chronomancers", "Abysswalkers", "Starspawned", "Cometkin", "Eclipsians"],
    "Cyborgs": ["Advanced AI", "Combat-Oriented", "Light Augmented"],
    "Dwarf": ["Duergar (Underdark)", "Mark of Warding (Eberron)", "Mountain", "Hill"],
    "Elf": ["Drow (Dark Elf)", "Shadar-Kai", "Sea Elf", "High Elf", "Wood Elf", "Eladrin (Seasonal)", "Avariel"],
    "Fey": ["Hobgoblins", "Fairies", "Firbolgs", "Satyr/Fawn", "Trolls", "Leprechauns"],
    "Genasi": ["Fire", "Air", "Earth", "Water", "Electric", "Mud", "Ice"],
    "Spirits": ["Poltergeist", "Wraith", "Ghoul", "Vagrant Spirit"],
    "Halfling": ["Ghostwise", "Stout", "Mark of Hospitality (Eberron)", "Mark of Healing (Eberron)", "Lightfoot"],
    "Human": ["Variant", "Standard"],
    "Tabaxi": ["Pantherkin", "Tigerfolk", "Other (non-panther, non-tiger, non-lion, non-cat)"],
    "Lizardfolk (Reptilians)": ["Dinoboiz", "Other"],
    "Robots": ["Autognome", "Alternative Construct"],
    "Rodentfolk": ["Squirrelfolk", "Ratfolk", "Other (non-rat, non-squirrel)"],
    "Shapeshifter": ["Changelings", "Doppelgangers", "Lycanthropes"],
    "Skeleton": ["Lich", "Skeletal Mage", "Bone Warrior"],
    "Stone People (Golems)": ["Crystalborn", "Earth-Forged Golems", "Stoneborn"],
    "Succubi/Incubi": ["Dreamweaver Succubi", "Abyssal Succubi"],
    "Tiefling": ["Feral", "Bloodlines (e.g., Asmodeus)", "Bloodlines (e.g., Zariel)", "Bloodlines (e.g., Levistus)", "Standard"],
    "Vampire": ["True Vampire", "Nosferatu", "Dhampir"],
    "Yuan-Ti (Serpentine)": ["Pureblood", "Malison"],
}

__all__ = [
    "FAMILY_SUBTYPES",
    "SPECIES_FAMILIES",
    "SPECIES_SUBVARIANT_EXPLAINER_TEMPLATE",
]
