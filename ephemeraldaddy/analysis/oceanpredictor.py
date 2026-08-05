#OCEAN Type Predictor
#The 4 (eventual) models:
#"Dominance by Theory" (guesses by weights of signs, bodies and houses - theoretically based on astro lore)
#"Context by Theory" (guesses based on positions of signs & houses in a chart)
#"Dominance by Observation" (like 'Dominance by Theory' except it's based on data/direct observation of people & their charts in real life, as independent from astrological theory as possible)
#"Context by Observation" (you get the gist).

OCEAN_SIGNS = {
    "Aries": {
        "O": 5, "C": 2.5, "E": 10, "A": 0, "N": 7.5,
        "description": "pioneering, direct, competitive, courageous, impatient",
    },
    "Taurus": {
        "O": 0, "C": 7.5, "E": 2.5, "A": 5, "N": 2.5,
        "description": "steady, practical, sensual, patient, resistant to change",
    },
    "Gemini": {
        "O": 10, "C": 0, "E": 10, "A": 5, "N": 7.5,
        "description": "curious, verbal, adaptable, sociable, restless",
    },
    "Cancer": {
        "O": 5, "C": 7.5, "E": 0, "A": 10, "N": 10,
        "description": "protective, receptive, cautious, attached, changeable",
    },
    "Leo": {
        "O": 7.5, "C": 5, "E": 10, "A": 5, "N": 5,
        "description": "expressive, confident, proud, generous, theatrical",
    },
    "Virgo": {
        "O": 5, "C": 10, "E": 0, "A": 7.5, "N": 10,
        "description": "analytical, discriminating, methodical, helpful, worried",
    },
    "Libra": {
        "O": 7.5, "C": 2.5, "E": 7.5, "A": 10, "N": 5,
        "description": "social, diplomatic, aesthetic, cooperative, indecisive",
    },
    "Scorpio": {
        "O": 7.5, "C": 7.5, "E": 0, "A": 0, "N": 10,
        "description": "probing, private, persistent, controlling, intense",
    },
    "Sagittarius": {
        "O": 10, "C": 0, "E": 10, "A": 5, "N": 0,
        "description": "exploratory, philosophical, candid, exuberant, unrestrained",
    },
    "Capricorn": {
        "O": 0, "C": 10, "E": 0, "A": 2.5, "N": 7.5,
        "description": "disciplined, reserved, ambitious, pragmatic, cautious",
    },
    "Aquarius": {
        "O": 10, "C": 5, "E": 5, "A": 2.5, "N": 2.5,
        "description": "inventive, independent, principled, contrarian, detached",
    },
    "Pisces": {
        "O": 10, "C": 0, "E": 0, "A": 10, "N": 10,
        "description": "imaginative, compassionate, yielding, impressionable, escapist",
    },
}

OCEAN_BODIES = {
    "Sun": {
        "O": 7.5, "C": 5, "E": 10, "A": 5, "N": 0,
        "description": "vital, confident, creative, expressive, self-directed",
    },
    "Moon": {
        "O": 5, "C": 2.5, "E": 0, "A": 7.5, "N": 10,
        "description": "receptive, instinctive, nurturing, private, changeable",
    },
    "Mercury": {
        "O": 10, "C": 5, "E": 7.5, "A": 5, "N": 5,
        "description": "curious, analytical, communicative, adaptable, mentally active",
    },
    "Venus": {
        "O": 7.5, "C": 2.5, "E": 7.5, "A": 10, "N": 2.5,
        "description": "affectionate, sociable, aesthetic, conciliatory, pleasure-seeking",
    },
    "Mars": {
        "O": 2.5, "C": 5, "E": 10, "A": 0, "N": 7.5,
        "description": "assertive, active, competitive, forceful, reactive",
    },
    "Jupiter": {
        "O": 10, "C": 2.5, "E": 10, "A": 7.5, "N": 0,
        "description": "expansive, optimistic, generous, exploratory, excessive",
    },
    "Saturn": {
        "O": 0, "C": 10, "E": 0, "A": 2.5, "N": 10,
        "description": "disciplined, restrained, dutiful, cautious, apprehensive",
    },
    "Uranus": {
        "O": 10, "C": 0, "E": 5, "A": 0, "N": 7.5,
        "description": "original, rebellious, disruptive, independent, erratic",
    },
    "Neptune": {
        "O": 10, "C": 0, "E": 0, "A": 10, "N": 10,
        "description": "imaginative, compassionate, impressionable, elusive, unbounded",
    },
    "Pluto": {
        "O": 7.5, "C": 7.5, "E": 2.5, "A": 0, "N": 10,
        "description": "intense, private, compulsive, penetrating, controlling",
    },
    "Rahu": {
        "O": 7.5, "C": 5, "E": 7.5, "A": 0, "N": 7.5,
        "description": "ambitious, hungry, experimental, worldly, dissatisfied",
    },
    "Ketu": {
        "O": 7.5, "C": 2.5, "E": 0, "A": 5, "N": 5,
        "description": "detached, inward, instinctive, renunciatory, discontented",
    },
    "Chiron": {
        "O": 7.5, "C": 5, "E": 0, "A": 10, "N": 10,
        "description": "sensitive, instructive, compassionate, vulnerable, restorative",
    },
    "Ceres": {
        "O": 2.5, "C": 7.5, "E": 2.5, "A": 10, "N": 7.5,
        "description": "nurturing, protective, practical, attached, bereavement-conscious",
    },
    "Lilith": {
        "O": 10, "C": 0, "E": 2.5, "A": 0, "N": 7.5,
        "description": "autonomous, uncompromising, taboo-seeking, defiant, reactive",
    },
    "Juno": {
        "O": 2.5, "C": 10, "E": 2.5, "A": 7.5, "N": 5,
        "description": "committed, contractual, loyal, relational, equality-conscious",
    },
    "Vesta": {
        "O": 5, "C": 10, "E": 0, "A": 5, "N": 2.5,
        "description": "focused, devoted, self-contained, disciplined, purposeful",
    },
    "Pallas": {
        "O": 10, "C": 7.5, "E": 2.5, "A": 5, "N": 2.5,
        "description": "strategic, perceptive, inventive, pattern-oriented, composed",
    },
}

OCEAN_HOUSES = {
    1: {
        "O": 5, "C": 2.5, "E": 10, "A": 0, "N": 2.5,
        "description": "identity, embodiment, initiative, presentation, self-direction",
    },
    2: {
        "O": 0, "C": 7.5, "E": 2.5, "A": 2.5, "N": 5,
        "description": "possessions, security, values, sustenance, self-reliance",
    },
    3: {
        "O": 7.5, "C": 5, "E": 7.5, "A": 5, "N": 5,
        "description": "communication, learning, movement, siblings, immediate environment",
    },
    4: {
        "O": 2.5, "C": 5, "E": 0, "A": 7.5, "N": 7.5,
        "description": "home, family, ancestry, privacy, emotional foundations",
    },
    5: {
        "O": 10, "C": 0, "E": 10, "A": 5, "N": 0,
        "description": "creativity, pleasure, romance, play, self-expression",
    },
    6: {
        "O": 0, "C": 10, "E": 0, "A": 7.5, "N": 7.5,
        "description": "work, routine, service, maintenance, health",
    },
    7: {
        "O": 5, "C": 5, "E": 7.5, "A": 10, "N": 5,
        "description": "partnership, negotiation, contracts, cooperation, open conflict",
    },
    8: {
        "O": 7.5, "C": 5, "E": 0, "A": 2.5, "N": 10,
        "description": "intimacy, shared resources, mortality, secrecy, crisis",
    },
    9: {
        "O": 10, "C": 2.5, "E": 7.5, "A": 5, "N": 0,
        "description": "philosophy, higher learning, travel, law, belief",
    },
    10: {
        "O": 2.5, "C": 10, "E": 7.5, "A": 2.5, "N": 5,
        "description": "vocation, reputation, authority, achievement, public responsibility",
    },
    11: {
        "O": 10, "C": 5, "E": 10, "A": 7.5, "N": 0,
        "description": "friendship, groups, alliances, aspirations, collective interests",
    },
    12: {
        "O": 7.5, "C": 0, "E": 0, "A": 7.5, "N": 10,
        "description": "seclusion, surrender, hidden matters, imagination, vulnerability",
    },
}

OCEAN_ELEMENTS = { #by dominance weights
    "air": {
        "O": 10,
        "C": 5,
        "E": 7.5,
        "A": 2.5,
        "N": 5, #I think. Some Libras & Geminis, mad neurotic. Aquarians...shockingly chill.
        "description": "intellectual, curious, theoretical, abstract, detached",
    },
    "fire": {
        "O": 5,
        "C": 2.5,
        "E": 10,
        "A": 0,
        "N": 5, #I think. Not sure.
        "description": "bold, dynamic, charismatic, impulsive, reactive",
    },
    "water": {
        "O": 7.5,
        "C": 2.5,
        "E": 0,
        "A": 10,
        "N": 10,
        "description": "adaptive, empathic, perceptive, sensitive, emotionally responsive",
    },
    "earth": {
        "O": 0,
        "C": 10,
        "E": 2.5,
        "A": 7.5,
        "N": 0,
        "description": "grounded, stabilizing, practical, patient, dependable",
    },
}