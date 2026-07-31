#OCEAN Type Predictor
#The 4 (eventual) models:
#"Dominance by Theory" (guesses by weights of signs, bodies and houses - theoretically based on astro lore)
#"Context by Theory" (guesses based on positions of signs & houses in a chart)
#"Dominance by Observation" (like 'Dominance by Theory' except it's based on data/direct observation of people & their charts in real life, as independent from astrological theory as possible)
#"Context by Observation" (you get the gist).

OCEAN_ELEMENTS = {
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