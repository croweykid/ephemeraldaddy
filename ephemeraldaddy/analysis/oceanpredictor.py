#OCEAN Type Predictor
#The 4 (eventual) models:
#"Dominance by Theory" (guesses by weights of signs, bodies and houses - theoretically based on astro lore)
#"Context by Theory" (guesses based on positions of signs & houses in a chart)
#"Dominance by Observation" (like 'Dominance by Theory' except it's based on data/direct observation of people & their charts in real life, as independent from astrological theory as possible)
#"Context by Observation" (you get the gist).

OCEAN_SIGNS_THEORY = {
    "Aries": {
        "O": -5, "C": 0, "E": 10, "A":-5, "N": -10, #hesitant on assigning Aries less openness, because they ARE often receptive to factual explanations, if presented in terms they respect. "WHY ARE YOU LIKE THAT?!" they might demand, seeming conservative. But then, if you actually explain in terms they respect, they'll usually accept it and respect your frankness, then take you as you are.
        "description": "pioneering, direct, competitive, courageous, impatient",
    },
    "Taurus": {
        "O":-10, "C": 5, "E": -5, "A": 0, "N": -5, #not sure about Taurus' conscientiousness score. Possibly should be higher.
        "description": "steady, practical, sensual, patient, resistant to change",
    },
    "Gemini": {
        "O": 10, "C":-5, "E": 5, "A": 5, "N": 10, #conscientiousness is bumped from -10 to -5 due to hyperfixations & obsessions.
        "description": "curious, verbal, adaptable, sociable, restless",
    },
    "Cancer": {
        "O": -5, "C": 5, "E":-10, "A": 5, "N": 10,
        "description": "protective, receptive, cautious, attached, changeable",
    },
    "Leo": {
        "O": 0, "C": 5, "E": 10, "A": 5, "N": -5, #wants/needs to be liked, so moderately high Agreeable, but also (unless mitigated by other elements) bossy af, so not TOO agreeable.
        "description": "expressive, confident, proud, generous, theatrical",
    },
    "Virgo": {
        "O": 0, "C": 10, "E":-10, "A": 5, "N": 10, #not sure about agreeableness for Virgo. They DO want to be useful. They ARE persnicketty.
        "description": "analytical, discriminating, methodical, helpful, worried",
    },
    "Libra": {
        "O": 5, "C": -5, "E": 10, "A": 10, "N": 5,#?, #female libras tend to be "A":10, male libras tend to be "A":-5. But even negging and contrarianism are possibly affected for social capital. >_>
        "description": "social, diplomatic, aesthetic, cooperative, indecisive",
    },
    "Scorpio": {
        "O": 0, "C": 5, "E":-10, "A":-10, "N": 0, #Lots of scorpios are super S not N. Re: "Agreeableness". Most Scorpios aren't aggro, they just want sovereignty. But I looked at the list of Scorpio dom & those are NOT agreeable people.
        "description": "probing, private, persistent, controlling, intense",
    },
    "Sagittarius": {
        "O": -5, "C":-10, "E": 5, "A": -10, "N": -10, #Most Sag are S not N. But while their intelligence is rarely abstract, they ARE often pretty tolerant / open minded.
        "description": "exploratory, philosophical, candid, exuberant, unrestrained",
    },
    "Capricorn": {
        "O":-10, "C": 10, "E":-5, "A": -5, "N": -10, #NOT inherently agreeable. STILL charming within their boundaries, when rules are observed. Mad charisma.
        "description": "disciplined, reserved, ambitious, pragmatic, cautious",
    },
    "Aquarius": {
        "O": 10, "C": -10, "E": 5, "A": -10, "N": -5, 
        "description": "inventive, independent, principled, contrarian, detached",
    },
    "Pisces": {
        "O": 10, "C":-10, "E":-5, "A": 10, "N": 10, #Pisces are not always that agreeable. Feeling everything & being psychologically porous doesn't entail "agreeable"; sometimes you become reactive to the excess of inputs. But maybe that's just an Agreeable Person problem.
        "description": "imaginative, compassionate, yielding, impressionable, escapist",
    },
}

OCEAN_BODIES_THEORY = {
    "Sun": {
        "O": 5, "C": 0, "E": 10, "A": 0, "N": 0,
        "description": "vital, confident, creative, expressive, self-directed",
    },
    "Moon": {
        "O": 0, "C": -5, "E":-10, "A": 5, "N": 10,
        "description": "receptive, instinctive, nurturing, private, changeable",
    },
    "Mercury": {
        "O": 10, "C": 0, "E": 5, "A": 0, "N": 5,
        "description": "curious, analytical, communicative, adaptable, mentally active",
    },
    "Venus": {
        "O": 5, "C": -5, "E": 5, "A": 10, "N": -5, 
        "description": "affectionate, sociable, aesthetic, conciliatory, pleasure-seeking",
    },
    "Mars": {
        "O": -5, "C": 0, "E": 10, "A":-10, "N": 5,
        "description": "assertive, active, competitive, forceful, reactive",
    },
    "Jupiter": {
        "O": 10, "C": -5, "E": 10, "A": 5, "N": 0,
        "description": "expansive, optimistic, generous, exploratory, excessive",
    },
    "Saturn": {
        "O":-10, "C": 10, "E":-10, "A": -5, "N": 10,
        "description": "disciplined, restrained, dutiful, cautious, apprehensive",
    },
    "Uranus": {
        "O": 10, "C":-10, "E": 0, "A":-10, "N": 5,
        "description": "original, rebellious, disruptive, independent, erratic",
    },
    "Neptune": {
        "O": 10, "C":-10, "E":-10, "A": 10, "N": 10,
        "description": "imaginative, compassionate, impressionable, elusive, unbounded",
    },
    "Pluto": {
        "O": 5, "C": 5, "E": -5, "A":-10, "N": 10,
        "description": "intense, private, compulsive, penetrating, controlling",
    },
    "Rahu": {
        "O": 5, "C": 0, "E": 5, "A":-10, "N": 5,
        "description": "ambitious, hungry, experimental, worldly, dissatisfied",
    },
    "Ketu": {
        "O": 5, "C": -5, "E":-10, "A": 0, "N": 5,
        "description": "detached, inward, instinctive, renunciatory, discontented",
    },
    "Chiron": {
        "O": 5, "C": 0, "E":-10, "A": 10, "N": 10,
        "description": "sensitive, instructive, compassionate, vulnerable, restorative",
    },
    "Ceres": {
        "O": -5, "C": 5, "E": -5, "A": 10, "N": 5,
        "description": "nurturing, protective, practical, attached, bereavement-conscious",
    },
    "Lilith": {
        "O": 10, "C":-10, "E": -5, "A":-10, "N": 5,
        "description": "autonomous, uncompromising, taboo-seeking, defiant, reactive",
    },
    "Juno": {
        "O": -5, "C": 10, "E": -5, "A": 5, "N": 5,
        "description": "committed, contractual, loyal, relational, equality-conscious",
    },
    "Vesta": {
        "O": 0, "C": 10, "E":-10, "A": 0, "N": -5, 
        "description": "focused, devoted, self-contained, disciplined, purposeful",
    },
    "Pallas": {
        "O": 10, "C": 5, "E": -5, "A": 0, "N": -5, 
        "description": "strategic, perceptive, inventive, pattern-oriented, composed",
    },
}

OCEAN_HOUSES_THEORY = {
    1: {
        "O": 0, "C": -5, "E": 10, "A":-10, "N": -5, 
        "description": "identity, embodiment, initiative, presentation, self-direction",
    },
    2: {
        "O":-10, "C": 5, "E": -5, "A": -5, "N": 5,
        "description": "possessions, security, values, sustenance, self-reliance",
    },
    3: {
        "O": 5, "C": 0, "E": 5, "A": 0, "N": 5,
        "description": "communication, learning, movement, siblings, immediate environment",
    },
    4: {
        "O": -5, "C": 0, "E":-10, "A": 5, "N": 5,
        "description": "home, family, ancestry, privacy, emotional foundations",
    },
    5: {
        "O": 10, "C":-10, "E": 10, "A": 0, "N": 0,
        "description": "creativity, pleasure, romance, play, self-expression",
    },
    6: {
        "O":-10, "C": 10, "E":-10, "A": 5, "N": 5,
        "description": "work, routine, service, maintenance, health",
    },
    7: {
        "O": 0, "C": 0, "E": 5, "A": 10, "N": 5,
        "description": "partnership, negotiation, contracts, cooperation, open conflict",
    },
    8: {
        "O": 5, "C": 0, "E":-10, "A": -5, "N": 10,
        "description": "intimacy, shared resources, mortality, secrecy, crisis",
    },
    9: {
        "O": 10, "C": -5, "E": 5, "A": 0, "N": 0,
        "description": "philosophy, higher learning, travel, law, belief",
    },
    10: {
        "O": -5, "C": 10, "E": 5, "A": -5, "N": 5,
        "description": "vocation, reputation, authority, achievement, public responsibility",
    },
    11: {
        "O": 10, "C": 0, "E": 10, "A": 5, "N": 0,
        "description": "friendship, groups, alliances, aspirations, collective interests",
    },
    12: {
        "O": 5, "C":-10, "E":-10, "A": 5, "N": 10,
        "description": "seclusion, surrender, hidden matters, imagination, vulnerability",
    },
}

OCEAN_ELEMENTS_THEORY = { #by dominance weights
    "air": { #NT
        "O": 10,
        "C": 5,
        "E": 5,
        "A": -5, 
        "N": 0, #I think. Some Libras & Geminis, mad neurotic. Aquarians...shockingly chill.
        "description": "intellectual, curious, theoretical, abstract, detached",
    },
    "fire": { #SP
        "O": -5, 
        "C": -5, 
        "E": 5,
        "A": 0,
        "N": 0, #I think. Not sure.
        "description": "bold, dynamic, charismatic, impulsive, reactive",
    },
    "water": { #NF
        "O": 5,
        "C": -5, 
        "E": 0,
        "A": 10,
        "N": 10,
        "description": "adaptive, empathic, perceptive, sensitive, emotionally responsive",
    },
    "earth": { #SJ
        "O": 0,
        "C": 10,
        "E": -5, 
        "A": 5,
        "N": 0,
        "description": "grounded, stabilizing, practical, patient, dependable",
    },
}
# Nakshatra scoring factors follow the traditional Vimshottari planetary lord
# cycle, borrowing each lord's OCEAN body profile for dominance-by-theory scoring.
OCEAN_NAKSHATRAS_THEORY = {
    "Ashwini": OCEAN_BODIES_THEORY["Ketu"],
    "Bharani": OCEAN_BODIES_THEORY["Venus"],
    "Krittika": OCEAN_BODIES_THEORY["Sun"],
    "Rohini": OCEAN_BODIES_THEORY["Moon"],
    "Mrigashira": OCEAN_BODIES_THEORY["Mars"],
    "Ardra": OCEAN_BODIES_THEORY["Rahu"],
    "Punarvasu": OCEAN_BODIES_THEORY["Jupiter"],
    "Pushya": OCEAN_BODIES_THEORY["Saturn"],
    "Ashlesha": OCEAN_BODIES_THEORY["Mercury"],
    "Magha": OCEAN_BODIES_THEORY["Ketu"],
    "Purva Phalguni": OCEAN_BODIES_THEORY["Venus"],
    "Uttara Phalguni": OCEAN_BODIES_THEORY["Sun"],
    "Hasta": OCEAN_BODIES_THEORY["Moon"],
    "Chitra": OCEAN_BODIES_THEORY["Mars"],
    "Swati": OCEAN_BODIES_THEORY["Rahu"],
    "Vishakha": OCEAN_BODIES_THEORY["Jupiter"],
    "Anuradha": OCEAN_BODIES_THEORY["Saturn"],
    "Jyestha": OCEAN_BODIES_THEORY["Mercury"],
    "Mula": OCEAN_BODIES_THEORY["Ketu"],
    "Purva Ashadha": OCEAN_BODIES_THEORY["Venus"],
    "Uttara Ashadha": OCEAN_BODIES_THEORY["Sun"],
    "Shravana": OCEAN_BODIES_THEORY["Moon"],
    "Dhanishta": OCEAN_BODIES_THEORY["Mars"],
    "Shatabhisha": OCEAN_BODIES_THEORY["Rahu"],
    "Purva Bhadrapada": OCEAN_BODIES_THEORY["Jupiter"],
    "Uttara Bhadrapada": OCEAN_BODIES_THEORY["Saturn"],
    "Revati": OCEAN_BODIES_THEORY["Mercury"],
}

OCEAN_NAKSHATRAS_THEORY2 = {
	"Ashwini": {
        "O": 5, "C": -5, "E": 10, "A": 5, "N": -5, 
        "description": "swift, pioneering, restorative, youthful, impatient",
    },
    "Bharani": {
        "O": 0, "C": 5, "E": -5, "A": -5, "N": 5,
        "description": "enduring, restrained, sensual, intense, burden-bearing",
    },
    "Krittika": {
        "O": -5, "C": 10, "E": 0, "A": -5, "N": 5,
        "description": "sharp, decisive, purifying, critical, protective",
    },
    "Rohini": {
        "O": 5, "C": 0, "E": 5, "A": 5, "N": 5,
        "description": "creative, sensual, attractive, fertile, possessive",
    },
    "Mrigashira": {
        "O": 10, "C": -5, "E": 0, "A": 5, "N": 5,
        "description": "curious, searching, gentle, elusive, restless",
    },
    "Ardra": {
        "O": 10, "C": 0, "E": 0, "A":-10, "N": 10,
        "description": "intellectual, fierce, turbulent, effortful, cathartic",
    },
    "Punarvasu": {
        "O": 5, "C": 0, "E": 0, "A": 10, "N": 0,
        "description": "renewing, optimistic, generous, principled, resilient",
    },
    "Pushya": {
        "O": -5, "C": 10, "E": -5, "A": 10, "N": -5, 
        "description": "nourishing, dutiful, traditional, devotional, dependable",
    },
    "Ashlesha": {
        "O": 5, "C": 5, "E":-10, "A":-10, "N": 10,
        "description": "perceptive, strategic, secretive, binding, suspicious",
    },
    "Magha": {
        "O": -5, "C": 5, "E": 10, "A": -5, "N": 5,
        "description": "regal, ancestral, authoritative, proud, ceremonial",
    },
    "Purva Phalguni": {
        "O": 5, "C":-10, "E": 10, "A": 5, "N": -5, 
        "description": "pleasure-seeking, romantic, sociable, creative, indulgent",
    },
    "Uttara Phalguni": {
        "O": 0, "C": 10, "E": 5, "A": 10, "N": 0,
        "description": "generous, reliable, contractual, helpful, patronizing",
    },
    "Hasta": {
        "O": 5, "C": 10, "E": 0, "A": 0, "N": 5,
        "description": "dexterous, clever, practical, skillful, controlling",
    },
    "Chitra": {
        "O": 10, "C": 5, "E": 5, "A": -5, "N": 5,
        "description": "artistic, architectural, glamorous, exacting, individualistic",
    },
    "Swati": {
        "O": 10, "C": -5, "E": 0, "A": 0, "N": 5,
        "description": "independent, adaptable, intellectual, mobile, restless",
    },
    "Vishakha": {
        "O": 0, "C": 10, "E": 5, "A":-10, "N": 5,
        "description": "goal-driven, competitive, determined, ambitious, consuming",
    },
    "Anuradha": {
        "O": 5, "C": 5, "E": 5, "A": 10, "N": 5,
        "description": "devoted, friendly, organized, persevering, relational",
    },
    "Jyestha": {
        "O": 5, "C": 10, "E": 5, "A":-10, "N": 10,
        "description": "authoritative, protective, strategic, proud, vigilant",
    },
    "Mula": {
        "O": 10, "C": -5, "E": -5, "A":-10, "N": 10,
        "description": "radical, investigative, uncompromising, uprooting, truth-seeking",
    },
    "Purva Ashadha": {
        "O": 5, "C": 0, "E": 10, "A": -5, "N": -5, 
        "description": "persuasive, confident, idealistic, expressive, unconquered",
    },
    "Uttara Ashadha": {
        "O": 0, "C": 10, "E": 5, "A": 5, "N": 0,
        "description": "principled, responsible, enduring, honorable, victorious",
    },
    "Shravana": {
        "O": 10, "C": 5, "E": 0, "A": 5, "N": -5, 
        "description": "receptive, learned, observant, connective, tradition-conscious",
    },
    "Dhanishta": {
        "O": 5, "C": 5, "E": 10, "A": 0, "N": -5, 
        "description": "rhythmic, ambitious, social, prosperous, performance-oriented",
    },
    "Shatabhisha": {
        "O": 10, "C": 5, "E":-10, "A": -5, "N": 5,
        "description": "investigative, restorative, private, unconventional, guarded",
    },
    "Purva Bhadrapada": {
        "O": 10, "C": 5, "E": -5, "A":-10, "N": 10,
        "description": "fervent, austere, visionary, severe, polarizing",
    },
    "Uttara Bhadrapada": {
        "O": 10, "C": 10, "E":-10, "A": 10, "N": -5, 
        "description": "contemplative, restrained, compassionate, enduring, composed",
    },
    "Revati": {
        "O": 10, "C": 0, "E": -5, "A": 10, "N": 5,
        "description": "gentle, imaginative, protective, guiding, sensitive",
    },
}
