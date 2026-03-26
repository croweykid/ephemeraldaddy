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
            ""
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
            ""
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
            "millieu", #language of the local
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
            ""
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
            "past",
        ],

        "traditional_domains": [
            "ancestral land",
            "gestation",
            "protective enclosure",
            "maternal continuity",
            "end of matters",
            "hidden foundations",
            #"father (within patrilineal systems)",
            #"mother (within natural systems)",
        ],

        "esoteric_domains": [
            "foundation stones",
            "the underground chamber",
            "the buried base",
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
    
}