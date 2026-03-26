HOUSE_PROPERTIES_EXPLAINED = {
    "domain_layers": {
        "core_domains": "irreducible function",
        "derived_domains": "contemporary extensions",
        "traditional_domains": "inherited historical assignments",
        "esoteric_domains": "symbolic and mythic register",
    },
    "axes": {
        "visibility": "how exposed the house is to social perception",
        "relationality": "how dependent the house is on interaction with others",
        "materiality": "how tied it is to body, matter, resources, or land",
        "institutionality": "how much it depends on formal roles, rules, or social structures",
        "immediacy": "how present-tense, proximal, and situational the house's operations are vs ancestry, legacy, duration, decline, or long arcs of time",
        "agency": "how much direct volition operates there",
        "publicness": "how socially externalized the house is",
        "symbolic_density": "how naturally the house attracts mythic, psychic, or interpretive meaning",
    }
}

HOUSE_DEFINITIONS = { #Areas of Life
    1: {
        "name": "First House",
        "archetypal_title": "The Visible Incarnation Point",

        "core_domains": [ #irreducible function
            "self",
            "body",
            "appearance",
            "physical presence",
            "identity",
            "name",
            "embodiment",
            "temperament",
            "approach",
            "self-presentation",
            "first impression",
            "surface vitality",
        ],

        "derived_domains": [ #contemporary extensions
            "personal style",
            "attitude",
            "confidence",
            "social legibility",
            "physical manner",
            "posture",
            "gait",
            "facial expression",
            "signature",
            "immediate impact",
            "visible health",
            "visible mood",
            "voice",
        ],

        "traditional_domains": [ #inherited historical assignments
            "the native",
            "constitution",
            "complexion",
            "stature",
            "manners",
            "bodily form",
            "disposition",
            "vital force",
        ],

        "esoteric_domains": [ #symbolic and mythic register
            "the threshold self",
            "daylight identity",
            "face turned toward the world",
            "body's declaration",
            "locus of arrival",
            "visible seal of being",
            "animating presence",
        ],

        "axes": {
            "visibility": 1.00, #how exposed the house is to social perception
            "relationality": 0.20, #how dependent the house is on interaction with others
            "materiality": 0.82, #how tied it is to body, matter, resources, land
            "institutionality": 0.08, #how much it depends on formal social structures
            "agency": 0.88, #how much direct volition operates there
            "publicness": 0.42, #how socially externalized it is
            "immediacy": 0.96, #how immediate
            "symbolic_density": 0.62, #how naturally mythic/psychic/interpretive it is
        },

        "logic": {
            "entry_mode": "arrival",
            "resource_mode": "presence",
            "failure_mode": "fragile embodiment, depleted vitality, incoherent self-presentation",
            "distortion_mode": "overidentification with appearance, persona, or immediate impact",
        },
        "notes": [
        ],
    },
    2: {
        "name": "Second House",
        "archetypal_title": "The House of Possession",

        "core_domains": [
            "money",
            "income",
            "possessions",
            "resources",
            "savings",
            "reserves",
            "food",
            "appetite",
            "security",
            "continuity",
            "holdings",
            "material support",
        ],

        "derived_domains": [
            "budget",
            "spending",
            "comfort",
            "hoard",
            "stored goods",
            "provisions",
            "livelihood",
            "revenue-generating skills", #"employable skills",
            "self-worth",
            "personal values",
            "taste",
            "resource management",
            "what-can-be-relied-upon",
            "supplies",
            "stockpiles",
        ],

        "traditional_domains": [
            "movable goods",
            "wealth",
            "substance",
            "livelihood",
            "gain",
            "loss of substance",
            "treasury",
            "stores",
            "acquisition",
        ],

        "esoteric_domains": [
            "storehouse of being",
            "mouth and purse",
            "kept substance",
            "private reserve",
            "what feeds continuity",
            "counted and the carried",
            "what-keeps-the-organism-going",
            "right to retain",
            "grammar of possession",
            "earthly retention",
            "body's claim on matter",
        ],

        "axes": {
            "visibility": 0.28,
            "relationality": 0.18,
            "materiality": 0.96,
            "institutionality": 0.18,
            "agency": 0.72,
            "publicness": 0.20,
            "immediacy":0.51,
            "symbolic_density": 0.58,
        },

        "logic": {
            "entry_mode": "acquisition",
            "resource_mode": "retention",
            "failure_mode": "depletion, instability, waste, unreliable support",
            "distortion_mode": "hoarding, overidentification with possessions, reducing worth to measurable assets",
        },
        "notes": [
        ],
    },
    3: {
        "name": "Third House",
        "archetypal_title": "The Immediate Signal Ecology",

        "core_domains": [
            "siblings",
            "cousins",
            "kindred",
            "neighbors",
            "messages",
            "conversation",
            "communication",
            "correspondence",
            "information exchange",
            "local travel",
            "errands",
            "routes",
            "crossings",
            "nearby environment",
        ],

        "derived_domains": [
            "texts",
            "emails",
            "calls",
            "notes",
            "calendar",
            "dialogue",
            "dialects",
            "code-switching",
            "semiotic maneuvering",
            "symbolic fluency", #fluency with cultural symbols
            "iconographic literacy", #understanding of cultural iconograph
            "language of the local milieu",
            "gossip",
            "news",
            "data",
            "databases",
            "intelligence",
            "relay systems",
            "commuting",
            "domestic travel",
            "research",
            "study",
            "analysis",
            "investigation",
            "pattern recognition",
        ],

        "traditional_domains": [
            "brethren",
            "kindred",
            "letters",
            "missives",
            "messengers",
            "rumors",
            "short journeys",
            "visitations",
            "local roads",
        ],

        "esoteric_domains": [
            "casual omens",
            "passing sign",
            "street-level intelligence",
            "crossroads knowledge",
            "local symbolic currency",
            "signal traffic",
            "nearby web of exchange",
            "small repetitions with meaning",
            "ambient murmurs",
        ],

        "axes": {
            "visibility": 0.52,
            "relationality": 0.74,
            "materiality": 0.42,
            "institutionality": 0.24,
            "immediacy":0.90,
            "agency": 0.66,
            "publicness": 0.46,
            "symbolic_density": 0.64,
        },

        "logic": {
            "entry_mode": "contact",
            "resource_mode": "exchange",
            "failure_mode": "noise, miscommunication, trivial distraction, scattered attention, local friction",
            "distortion_mode": "overstimulation, gossip addiction, compulsive signaling, mistaking information flow for depth",
        },
        "notes": [
        ],
    },
    4: {
        "name": "Fourth House",
        "archetypal_title": "The Origin Chamber",

        "core_domains": [
            "home",
            "family",
            "dwelling",
            "private life",
            "roots",
            "ancestry",
            "land",
            "property",
            "real estate",
            "childhood",
            "origin",
            "foundation",
            "belonging",
        ],

        "derived_domains": [
            "home base",
            "domestic security",
            "abode",
            "household",
            "gardens",
            "cultivated land",
            "ancestral legacy",
            "parental roots",
            "domestic situation",
            "lineage",
            "kitchen",
            "bedroom",
            "buried history",
            "cellar",
            "nesting instinct",
            "family estate",
            "domestic sovereignty",
            "family name",
            "protective enclosure",
            "past",
        ],

        "traditional_domains": [
            "ancestral land",
            "end of matters",
            "hidden foundations",
            #"father (within patrilineal systems)",
            #"mother (within natural systems)",
        ],

        "esoteric_domains": [
            "foundation stones",
            "gestation",
            "the underground chamber",
            "the buried base",
            "maternal continuity",
            "hearth memory",
            "pre-public formation of self",
            "the enclosed kingdom",
            "the inherited ground",
            "the root system of identity",
            "what shelters the self from public view",
        ],

        "axes": {
            "visibility": 0.10,
            "relationality": 0.62,
            "materiality": 0.78,
            "institutionality": 0.32,
            "immediacy": 0.52,
            "agency": 0.34,
            "publicness": 0.06,
            "symbolic_density": 0.80,
        },

        "logic": {
            "entry_mode": "inheritance",
            "resource_mode": "containment",
            "failure_mode": "dislocation, instability of home, severed continuity, private insecurity",
            "distortion_mode": "overattachment to origins, enclosure, familial stagnation, living inside the past",
        },
        "notes": [
            "Some traditional systems assign the 4th house to the father and patrimony; this likely reflects historical property and lineage structures rather than a universally valid symbolic rule."
        ],
    },
    5: {
        "name": "Fifth House",
        "archetypal_title": "The Theatre of Pleasure",

        "core_domains": [
            "children",
            "romance",
            "courtship",
            "flirtation",
            "pleasure",
            "play",
            "creativity",
            "art",
            "performance",
            "games",
            "delight",
            "self-display",
        ],

        "derived_domains": [
            "dating",
            "seduction",
            "theatre",
            "showmanship",
            "applause",
            "hobbies",
            "party",
            "amusement",
            "festive excess",
            "festivity",
            "risk for pleasure",
            "creative output",
            "favored offspring",
            "charisma",
            "adornment",
            "being admired",
        ],

        "traditional_domains": [
            "children",
            "pleasure",
            "lovers",
            "festivals",
            "banquets",
            "games of chance",
            "merriment",
            "conception",
        ],

        "esoteric_domains": [
            "the staged self",
            "the radiant performance impulse",
            "creation under witness",
            "the desire to delight",
            "the theater of attraction",
            "the gamble of visibility",
            "the favored creation",
            "the spark that wants applause",
        ],

        "axes": {
            "visibility": 0.86,
            "relationality": 0.58,
            "materiality": 0.42,
            "institutionality": 0.18,
            "mortality": 0.16,
            "agency": 0.84,
            "subjectivity": 0.74,
            "publicness": 0.64,
            "immediacy": 0.78,
            "symbolic_density": 0.72,
        },

        "logic": {
            "entry_mode": "attraction",
            "resource_mode": "expression",
            "failure_mode": "vanity, sterile performance, hollow pleasure, neglected creations, attention-seeking without substance",
            "distortion_mode": "living for applause, confusing admiration with love, turning play into self-importance",
        },
        "notes": []
    },
    6: {
        "name": "Sixth House",
        "archetypal_title": "The Discipline of Daily Function",

        "core_domains": [
            "labor",
            "service",
            "duty",
            "routine",
            "habits",
            "maintenance",
            "upkeep",
            "correction",
            "health",
            "diet",
            "repetition",
            "useful competence",
        ],

        "derived_domains": [
            "daily obligations",
            "daily tasks",
            "daily grind",
            "maintenance tasks",
            "mundane tasks",
            "schedule",
            "practical work",
            "coworkers",
            "repetitive duties",
            "quiet competence",
            "discipline",
            "regimen",
            "hygiene",
            "repair",
            "troubleshooting",
        ],

        "traditional_domains": [
            "servants",
            "toil",
            "illness",
            "infirmity",
            "labor",
            "service",
            "drudgery",
            "subordinate work",
        ],

        "esoteric_domains": [
            "the maintenance corridor",
            "the burden of continuation",
            "the discipline of upkeep",
            "what must be corrected",
            "work that keeps things running",
            "the invisible labor of continuity",
            "competence without spectacle",
            "the rituals of functioning",
            "the price of operational life",
        ],

        "axes": {
            "visibility": 0.22,
            "relationality": 0.48,
            "materiality": 0.72,
            "institutionality": 0.52,
            "mortality": 0.34,
            "agency": 0.58,
            "subjectivity": 0.34,
            "publicness": 0.24,
            "immediacy": 0.88,
            "symbolic_density": 0.46,
        },

        "logic": {
            "entry_mode": "obligation",
            "resource_mode": "maintenance",
            "failure_mode": "disorder, neglect, inefficiency, burnout, declining function",
            "distortion_mode": "living as a servant to routine, overidentifying with usefulness, reducing life to upkeep",
        },

        "notes": [
        "H6 vs H10: The 6th house is doing the work that needs done. The 10th house is getting RECOGNIZED for & publicly defined by the work.",
        "H6 vs H1: Both can relate to health; 1st house is vitality, embodiment & visible constitution. H6 is maintenance of function, regimen, symptoms, health management.",
        "H6 vs H12: 6th house manages disorder. 12th house is being overtaken by what escaped management."
        ]
    },
    7: {
        "name": "Seventh House",
        "archetypal_title": "The Formal Other", #The Other Party

        "core_domains": [
            "marriage",
            "partnership",
            "spouse",
            "counterpart",
            "union",
            "agreement",
            "contracts",
            "reciprocity",
            "witness",
            "rival",
            "open enemies",
            "one-to-one commitments",
        ],

        "derived_domains": [
            "partner",
            "relationships",
            "binding contracts",
            "alliances",
            "clients",
            "collaboration",
            "negotiation",
            "interpersonal commitments",
            "legal contracts",
            "diplomacy",
            "litigation",
            "devotion",
        ],

        "traditional_domains": [
            "marriage",
            "spouse",
            "contracts",
            "open enemies",
            "lawsuits",
            "partnerships",
            "declared opposition",
        ],

        "esoteric_domains": [
            "the recognized other",
            "the face across the threshold",
            "binding encounter",
            "the lawful counterpart",
            "the witness who answers back",
            "union under recognition",
            "the adversary in full view",
            "the other party",
        ],

        "axes": {
            "visibility": 0.68,
            "relationality": 0.98,
            "materiality": 0.26,
            "institutionality": 0.74,
            "mortality": 0.22,
            "agency": 0.52,
            "subjectivity": 0.30,
            "publicness": 0.72,
            "immediacy": 0.70,
            "symbolic_density": 0.62,
        },

        "logic": {
            "entry_mode": "encounter",
            "resource_mode": "reciprocity",
            "failure_mode": "conflict, imbalance, bad bargains, adversarial fixation, unstable commitments",
            "distortion_mode": "defining the self through the other, compulsive pair-bonding, surrendering judgment for relational recognition",
        },

        "notes": [
        "7th vs 5th house: 5th = romance, flirtation, attraction, seduction, courtship. (The courtship phase.) 7th = union, contract, marriage, mutual obligation, formal pair-bond. (The act of formalizing the union.)",
        "7th vs 8th house: 7th = the agreement (formalizing a union - like getting married). 8th = the consequence after the agreement (consequences of the formalization - the outcome of the marriage itself).",
        "7th vs 11th house: 7th = one-to-one alliance or opposition; partnerships & individual nemeses. 11th = group belonging, networks, collective affiliation, team rivalries.",
        "7th (DS) vs 1st house (AS): 1st = self as emergence. 7th = other as recognized counterpart.",
        "House 7 is not 'love', nor 'romance'. It is the juridical and reciprocal structure of human encounter."
        ]
    },
    8: {
        "name": "Eighth House",
        "archetypal_title": "Consequences of Entanglement",

        "core_domains": [
            "death",
            "mortality",
            "debt",
            "taxes",
            "inheritance",
            "other people's money",
            "shared resources",
            "loans",
            "intimacy",
            "insurance",
            "high-stakes bonds",
            "dependency",
            "irreversible exchange",
        ],

        "derived_domains": [
            "mergers",
            "transactional consequences",
            "fear",
            "taboos",
            "sexuality",
            "crises",
            "asymmetrical access",
            "desire indistinguishable from need",
            "power through entanglement",
            "tested boundaries",
            "leverage through dependency",
            "forfeiture",
            "shared liabilities",
            "consequence-bearing control",
            "control through shared stakes",
            "extraction",
            "ancestral debt",
        ],

        "traditional_domains": [
            "death",
            "fear",
            "inheritance",
            "dowry",
            "other people's assets",
            "loss",
            "estate matters",
        ],

        "esoteric_domains": [
            "forbidden archives",
            "occult initiation",
            "bondage of consequence",
            "energetic residue",
            "threshold events",
            "blood price",
            "the cost hidden inside the bond",
            "stakes that override consent",
            "custody over what others need",
            "the chamber of irreversible exchange",
        ],

        "axes": {
            "visibility": 0.24,
            "relationality": 0.88,
            "materiality": 0.72,
            "institutionality": 0.62,
            "mortality": 0.96,
            "agency": 0.38,
            "subjectivity": 0.70,
            "publicness": 0.26,
            "immediacy": 0.40,
            "symbolic_density": 0.92,
        },

        "logic": {
            "entry_mode": "entanglement",
            "resource_mode": "merger",
            "failure_mode": "depletion, coercion, panic, exposure, irreversible loss, inherited burden",
            "distortion_mode": "confusing intensity with truth, eroticizing damage, seeking control through dependency",
        },

        "notes": [
            "Some distinctions: 10th house power = rank, status, office, visible authority. 7th house power = contractual parity or adversarial opposition. 12th house power = hidden undermining, obscured systems, silent attrition. 8th house power = leverage arising from merger, debt, taboo, exposure, inheritance, sexuality, fear, or irreversible consequence.",
            "The 8th house says, “I can affect your survival, your losses, your exposure, your dependency, your access, or the cost of your choices.” Then if you have it in Gemini, it probably adds 'teehee' and throws confetti in your face."
        ]
    },
    9: {
        "name": "Ninth House",
        "archetypal_title": "Meaning Found at Distance",

        "core_domains": [
            "long-distance travel",
            "foreign lands",
            "pilgrimage",
            "higher education",
            "philosophy",
            "religion",
            "law",
            "doctrine",
            "worldview",
            "belief systems",
            "organized value systems",
            "cultural distance",
        ],

        "derived_domains": [
            "travel abroad",
            "international journeys",
            "foreign cultures",
            "advanced study",
            "scholarship",
            "canonical texts",
            "sanctioned truth",
            "dogma",
            "gurus",
            "teachers",
            "theology",
            "jurisprudence",
            "ideology",
            "paradigms",
            "worldview architecture",
            "publishing",
            "translation across cultures",
        ],

        "traditional_domains": [
            "long journeys",
            "religion",
            "philosophy",
            "law",
            "priests",
            "sacred learning",
            "prophecy",
            "foreign lands",
        ],

        "esoteric_domains": [
            "meaning beyond the horizon",
            "initiation by distance",
            "the doctrine of elsewhere",
            "truth carried across borders",
            "the pilgrimage mind",
            "the architecture of sanctioned meaning",
            "the distant order that reshapes belief",
        ],

        "axes": {
            "visibility": 0.46,
            "relationality": 0.40,
            "materiality": 0.22,
            "institutionality": 0.72,
            "mortality": 0.20,
            "agency": 0.68,
            "subjectivity": 0.54,
            "publicness": 0.52,
            "immediacy": 0.22,
            "symbolic_density": 0.88,
        },

        "logic": {
            "entry_mode": "departure",
            "resource_mode": "orientation",
            "failure_mode": "dogmatism, abstraction without grounding, borrowed certainty, empty cosmopolitanism",
            "distortion_mode": "indiscriminate xenophilia, mistaking distance for wisdom, confusing ideology with truth, using belief as escape from reality",
        },

        "notes": [
            "H3 vs H9: 3rd house is local exchange, nearby signals, practical information, speech shaped by proximity. 9th = distance, doctrine, canon, worldview, travel beyond the local field. 3rd is information. 9th is meaning. 3rd is adjunct. 9th is tenured.",
            "H9 vs H10: 9th = truth systems, law, philosophy, doctrine. 10th = rank, office, legitimacy, public authority. The judge's reasoning is 9th. The judicial office itself is 10th.",
            "H9 vs H12: both get conflated with 'spirituality', but that's sloppy. 10th = rank, office, legitimacy, public authority. 12th = withdrawal, dissolution, confinement, obscured suffering. Either one can be ascetic at a monestary.",
            "The 9th house's affiliation with 'long journeys' means travel beyond one’s operative local sphere. Its scale changes with the transportation and cultural horizon of the era."
        ]
    },

}