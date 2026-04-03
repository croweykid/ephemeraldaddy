"""Reference text helpers for Human Design gates/lines."""

from __future__ import annotations

LINE_ARCHETYPES: dict[int, str] = {
    1: "Investigator/Foundation: learns by building solid fundamentals.",
    2: "Natural/Hermit: gifts emerge through natural talent and retreat.",
    3: "Martyr/Experimenter: grows through trial, error, and adaptation.",
    4: "Opportunist/Networker: influence and opportunities come through relationships.",
    5: "Heretic/Universalizer: practical leadership and projection field dynamics.",
    6: "Role Model/Visionary: perspective matures over time into exemplar wisdom.",
}

GATE_REFERENCE: dict[int, dict[str, str]] = {
    1: {"name": "The Creative", "meaning": "Unique creative self-expression and direction through originality."},
    2: {"name": "The Receptive", "meaning": "Inner receptivity that guides life direction when surrendered."},
    3: {"name": "Ordering", "meaning": "Mutation through beginning in chaos and structuring new patterns."},
    4: {"name": "Formulization", "meaning": "Mental answers and conceptual solutions driven by doubt."},
    5: {"name": "Fixed Rhythms", "meaning": "Natural timing, routines, and dependable energetic rhythms."},
    6: {"name": "Friction", "meaning": "Emotional boundaries, intimacy, and conflict that creates clarity."},
    7: {"name": "The Role of the Self", "meaning": "Leadership through guidance of collective direction."},
    8: {"name": "Contribution", "meaning": "Individual style and contribution that influences the group."},
    9: {"name": "Focus", "meaning": "Concentration, detail mastery, and sustained attention."},
    10: {"name": "Behavior of the Self", "meaning": "Authentic self-love and correct behavior of the self."},
    11: {"name": "Ideas", "meaning": "Conceptual imagery and idea generation for sharing."},
    12: {"name": "Caution", "meaning": "Careful emotional expression and social refinement."},
    13: {"name": "The Listener", "meaning": "Witnessing stories of the past and holding collective memory."},
    14: {"name": "Power Skills", "meaning": "Resources, capability, and empowered direction of energy."},
    15: {"name": "Extremes", "meaning": "Love of humanity expressed through natural extremes and tolerance."},
    16: {"name": "Skills", "meaning": "Enthusiasm, practice, and talent development."},
    17: {"name": "Opinions", "meaning": "Logical patterning and structured viewpoints."},
    18: {"name": "Correction", "meaning": "Judgment to improve, refine, and fix patterns."},
    19: {"name": "Sensitivity", "meaning": "Need-based sensitivity to people and resources."},
    20: {"name": "The Now", "meaning": "Present-moment awareness and direct expression."},
    21: {"name": "Control", "meaning": "Management of material resources and willful oversight."},
    22: {"name": "Grace", "meaning": "Emotional openness, charm, and social mood."},
    23: {"name": "Assimilation", "meaning": "Explaining and simplifying individual insights."},
    24: {"name": "Rationalization", "meaning": "Mental return to contemplate and integrate knowing."},
    25: {"name": "Innocence", "meaning": "Universal love, spirit, and purity of heart."},
    26: {"name": "The Egoist", "meaning": "Persuasion, memory, and strategic willpower."},
    27: {"name": "Caring", "meaning": "Nourishment, preservation, and protective support."},
    28: {"name": "The Game Player", "meaning": "Struggle to find purpose and meaningful risk."},
    29: {"name": "Perseverance", "meaning": "Commitment and the power of saying yes correctly."},
    30: {"name": "Desire", "meaning": "Emotional intensity, longing, and experiential passion."},
    31: {"name": "Influence", "meaning": "Democratic leadership and recognized influence."},
    32: {"name": "Continuity", "meaning": "Instinct for what can endure and succeed over time."},
    33: {"name": "Privacy", "meaning": "Retreat, reflection, and proper timing for sharing history."},
    34: {"name": "Power", "meaning": "Raw sacral power and pure life-force response."},
    35: {"name": "Progress", "meaning": "Change through experience and emotional evolution."},
    36: {"name": "Crisis", "meaning": "Emotional turbulence that matures into wisdom."},
    37: {"name": "Friendship", "meaning": "Community, loyalty, and tribal agreements."},
    38: {"name": "The Fighter", "meaning": "Struggle for purpose and meaningful opposition."},
    39: {"name": "Provocation", "meaning": "Provoking spirit and emotional truth."},
    40: {"name": "Deliverance", "meaning": "Work, service, and the need for rest after effort."},
    41: {"name": "Contraction", "meaning": "Imagination and pressure to begin new experiences."},
    42: {"name": "Growth", "meaning": "Completion cycles and developmental expansion."},
    43: {"name": "Insight", "meaning": "Breakthrough knowing and individual inner clarity."},
    44: {"name": "Alertness", "meaning": "Pattern memory, instinct, and recognition of opportunities."},
    45: {"name": "Gatherer", "meaning": "Stewardship, rulership, and material direction of the tribe."},
    46: {"name": "Determination of the Self", "meaning": "Love of the body and right place/right time."},
    47: {"name": "Realization", "meaning": "Mental pressure transforming confusion into meaning."},
    48: {"name": "Depth", "meaning": "Depth of solutions and fear of inadequacy transformed through mastery."},
    49: {"name": "Principles", "meaning": "Tribal values, revolution, and emotional boundaries."},
    50: {"name": "Values", "meaning": "Responsibility, ethics, and preservation of community."},
    51: {"name": "Shock", "meaning": "Initiation, courage, and competitive awakening."},
    52: {"name": "Stillness", "meaning": "Concentration through stillness and restraint."},
    53: {"name": "Beginnings", "meaning": "Pressure to start new cycles and developments."},
    54: {"name": "Ambition", "meaning": "Drive, aspiration, and material transformation."},
    55: {"name": "Spirit", "meaning": "Emotional abundance and mood-based spirit."},
    56: {"name": "Stimulation", "meaning": "Storytelling, curiosity, and mental wandering."},
    57: {"name": "Intuitive Clarity", "meaning": "Penetrating intuition and survival awareness in the now."},
    58: {"name": "Joy", "meaning": "Vital joy and pressure to improve life."},
    59: {"name": "Sexuality", "meaning": "Bonding, intimacy, and dissolving barriers."},
    60: {"name": "Limitation", "meaning": "Acceptance of limits that enables mutation."},
    61: {"name": "Inner Truth", "meaning": "Pressure to know mysteries and inner truth."},
    62: {"name": "Details", "meaning": "Precision, naming, and logical specifics."},
    63: {"name": "Doubt", "meaning": "Questioning, testing patterns, and logical verification."},
    64: {"name": "Confusion", "meaning": "Mental pressure from past imagery seeking clarity."},
}

AWARENESS_STREAMS = [
{"name":"sensing","type":"ajna","gates":[64,47,11,56]},
{"name":"knowing","type":"ajna","gates":[61,24,43,23]},
{"name":"understanding","type":"ajna","gates":[63,4,17,62]},

{"name":"instinct","type":"spleen","gates":[54,32,44,26]},
{"name":"intuition","type":"spleen","gates":[38,28,57,20]},
{"name":"taste","type":"spleen","gates":[58,18,48,16]},

{"name":"sensitivity","type":"solar plexus","gates":[19,49,37,40]},
{"name":"emoting","type":"solar plexus","gates":[39,55,22,12]},
{"name":"feeling","type":"solar plexus","gates":[41,30,36,35]},
]

HD_CHANNELS = {
    # =========================
    # INDIVIDUAL CIRCUITRY
    # =========================

    "2-14": {
        "name": "Channel of the Beat",
        "gates": (2, 14),
        "centers": ("G / Identity", "Sacral"),
        "circuit": "Individual / Knowing",
        "explanation": (
            "A directional life-force channel that combines inner guidance with the energy and resources to move things forward. "
            "It often shows up as a strong sense of where energy should go, with power for work, contribution, and movement when aligned with the correct direction."
        ),
    },

    "61-24": {
        "name": "Channel of Awareness",
        "gates": (61, 24),
        "centers": ("Head", "Ajna"),
        "circuit": "Individual / Knowing",
        "explanation": (
            "A pressure to understand inner truths and mentally process mystery. "
            "Often shows up as recurring contemplation, insight, and a need to make sense of the unknowable."
        ),
    },

    "43-23": {
        "name": "Channel of Structuring",
        "gates": (43, 23),
        "centers": ("Ajna", "Throat"),
        "circuit": "Individual / Knowing",
        "explanation": (
            "The capacity to translate unusual insight into language. "
            "This is the classic 'genius to freak' channel: brilliant when timing and audience are right, baffling when they are not."
        ),
    },

    "8-1": {
        "name": "Channel of Inspiration",
        "gates": (8, 1),
        "centers": ("Throat", "G / Identity"),
        "circuit": "Individual / Knowing",
        "explanation": (
            "Creative self-expression that influences others by example rather than command. "
            "Its power lies in originality, contribution, and style with substance."
        ),
    },

    "57-20": {
        "name": "Channel of the Brainwave",
        "gates": (57, 20),
        "centers": ("Spleen", "Throat"),
        "circuit": "Individual / Knowing",
        "explanation": (
            "Immediate intuitive awareness expressed in the now. "
            "This channel can speak or act from spontaneous clarity before the rational mind catches up."
        ),
    },

    "34-20": {
        "name": "Channel of Charisma",
        "gates": (34, 20),
        "centers": ("Sacral", "Throat"),
        "circuit": "Individual / Integration",
        "explanation": (
            "Powerful life-force energy available for direct action in the present moment. "
            "This is highly self-directed, efficient energy that wants to do rather than discuss."
        ),
    },

    "10-20": {
        "name": "Channel of Awakening",
        "gates": (10, 20),
        "centers": ("G / Identity", "Throat"),
        "circuit": "Individual / Integration",
        "explanation": (
            "Authentic self-expression rooted in being true to oneself. "
            "It often appears as a visible, lived example of self-alignment rather than a theory about it."
        ),
    },

    "10-57": {
        "name": "Channel of Perfected Form",
        "gates": (10, 57),
        "centers": ("G / Identity", "Spleen"),
        "circuit": "Individual / Integration",
        "explanation": (
            "An instinctive sense for correct behavior and survival through embodied intelligence. "
            "This channel often 'just knows' how to move or respond in ways that preserve integrity and well-being."
        ),
    },

    "34-57": {
        "name": "Channel of Power",
        "gates": (34, 57),
        "centers": ("Sacral", "Spleen"),
        "circuit": "Individual / Integration",
        "explanation": (
            "Instinctive, responsive life-force energy. "
            "Fast, capable, and often physically potent, this channel tends to act from immediate inner knowing."
        ),
    },

    "28-38": {
        "name": "Channel of Struggle",
        "gates": (28, 38),
        "centers": ("Spleen", "Root"),
        "circuit": "Individual / Knowing",
        "explanation": (
            "A drive to fight for what has real meaning. "
            "Its challenge is not struggle itself, but choosing battles worthy of one’s life-force."
        ),
    },

    "39-55": {
        "name": "Channel of Emoting",
        "gates": (39, 55),
        "centers": ("Root", "Solar Plexus"),
        "circuit": "Individual / Knowing",
        "explanation": (
            "An emotionally creative and moody current that can provoke feeling and spirit. "
            "This channel often moves in waves and seeks emotional depth, authenticity, and inspiration."
        ),
    },

    "3-60": {
        "name": "Channel of Mutation",
        "gates": (3, 60),
        "centers": ("Sacral", "Root"),
        "circuit": "Individual / Knowing",
        "explanation": (
            "Transformational energy that brings new forms out of limitation and chaos. "
            "It often works in pulses rather than steady output, initiating deep change over time."
        ),
    },

    "12-22": {
        "name": "Channel of Openness",
        "gates": (12, 22),
        "centers": ("Throat", "Solar Plexus"),
        "circuit": "Individual / Knowing",
        "explanation": (
            "Emotional expression with social and artistic sensitivity. "
            "Its impact depends heavily on mood and timing; when correct, it can be elegant, intimate, and influential."
        ),
    },

    # =========================
    # COLLECTIVE CIRCUITRY
    # LOGIC / UNDERSTANDING
    # =========================

    "63-4": {
        "name": "Channel of Logic",
        "gates": (63, 4),
        "centers": ("Head", "Ajna"),
        "circuit": "Collective / Logic",
        "explanation": (
            "A mental pressure to doubt, test, and resolve uncertainty through patterns and answers. "
            "This channel is excellent for analysis, hypothesis, and structured reasoning."
        ),
    },

    "17-62": {
        "name": "Channel of Acceptance",
        "gates": (17, 62),
        "centers": ("Ajna", "Throat"),
        "circuit": "Collective / Logic",
        "explanation": (
            "The ability to organize opinions and articulate details clearly. "
            "It excels at naming, categorizing, and explaining patterns in precise terms."
        ),
    },

    "7-31": {
        "name": "Channel of the Alpha",
        "gates": (7, 31),
        "centers": ("G / Identity", "Throat"),
        "circuit": "Collective / Logic",
        "explanation": (
            "Leadership through direction and recognized influence. "
            "This channel is less about domination and more about being entrusted to guide the group."
        ),
    },

    "15-5": {
        "name": "Channel of Rhythm",
        "gates": (15, 5),
        "centers": ("G / Identity", "Sacral"),
        "circuit": "Collective / Logic",
        "explanation": (
            "A deep attunement to natural timing, routines, and life rhythms. "
            "It can appear as either extreme consistency or a broad tolerance for irregularity."
        ),
    },

    "16-48": { #not showing up
        "name": "Channel of Talent",
        "gates": (16, 48),
        "centers": ("Throat", "Spleen"),
        "circuit": "Collective / Logic",
        "explanation": (
            "Skill developed through repetition, depth, and refinement. "
            "This is less 'instant genius' and more mastery through immersion and practice."
        ),
    },

    "18-58": {
        "name": "Channel of Judgment",
        "gates": (18, 58),
        "centers": ("Spleen", "Root"),
        "circuit": "Collective / Logic",
        "explanation": (
            "A drive to improve systems by identifying flaws and correcting them. "
            "Healthy expression becomes constructive refinement rather than chronic dissatisfaction."
        ),
    },

    "9-52": {
        "name": "Channel of Concentration",
        "gates": (9, 52),
        "centers": ("Sacral", "Root"),
        "circuit": "Collective / Logic",
        "explanation": (
            "Sustained focus and the ability to hold attention on details over time. "
            "Excellent for deep work, precision, and methodical effort."
        ),
    },

    "42-53": {
        "name": "Channel of Maturation",
        "gates": (42, 53),
        "centers": ("Sacral", "Root"),
        "circuit": "Collective / Logic",
        "explanation": (
            "Energy for growth through cycles: beginning, developing, and completing processes. "
            "It learns by moving things through stages rather than leaving them perpetually half-born."
        ),
    },

    # =========================
    # COLLECTIVE CIRCUITRY
    # ABSTRACT / SENSING
    # =========================

    "48-16"

    "64-47": {
        "name": "Channel of Abstraction",
        "gates": (64, 47),
        "centers": ("Head", "Ajna"),
        "circuit": "Collective / Abstract",
        "explanation": (
            "A pressure to make sense of past experience through reflection and mental synthesis. "
            "Clarity often comes after confusion, not before it."
        ),
    },

    "29-46": {
        "name": "Channel of Discovery",
        "gates": (29, 46),
        "centers": ("Sacral", "G / Identity"),
        "circuit": "Collective / Sensing",
        "explanation": (
            "Commitment to life through embodied experience and perseverance. "
            "Its wisdom comes from saying yes to the right experiences and discovering meaning through participation."
        ),
    },

    "11-56": {
        "name": "Channel of Curiosity",
        "gates": (11, 56),
        "centers": ("Ajna", "Throat"),
        "circuit": "Collective / Abstract",
        "explanation": (
            "A love of ideas, stories, and stimulation through exploration. "
            "This channel often communicates meaning through narrative, imagery, and lived impressions."
        ),
    },

    "13-33": {
        "name": "Channel of the Prodigal",
        "gates": (13, 33),
        "centers": ("G / Identity", "Throat"),
        "circuit": "Collective / Abstract",
        "explanation": (
            "A capacity to listen to collective stories and later distill wisdom from the past. "
            "It often needs retreat and privacy before speaking with authority about experience."
        ),
    },

    "35-36": {
        "name": "Channel of Transitoriness",
        "gates": (35, 36),
        "centers": ("Throat", "Solar Plexus"),
        "circuit": "Collective / Abstract",
        "explanation": (
            "A drive for new experiences, change, and emotional learning through life events. "
            "It often matures by discovering that novelty alone is not the same as fulfillment."
        ),
    },

    "41-30": {
        "name": "Channel of Recognition",
        "gates": (41, 30),
        "centers": ("Root", "Solar Plexus"),
        "circuit": "Collective / Abstract",
        "explanation": (
            "Desire-fueled imagination and emotional anticipation for new experiences. "
            "This channel often initiates experiential journeys through longing, fantasy, and appetite for life."
        ),
    },

    # =========================
    # TRIBAL CIRCUITRY
    # DEFENSE / EGO / SUPPORT
    # =========================

    "27-50": {
        "name": "Channel of Preservation",
        "gates": (27, 50),
        "centers": ("Sacral", "Spleen"),
        "circuit": "Tribal / Defense",
        "explanation": (
            "A protective, sustaining energy concerned with care, nourishment, and responsibility. "
            "Its central question is often: what and whom am I responsible for maintaining?"
        ),
    },

    "32-54": {
        "name": "Channel of Transformation",
        "gates": (32, 54),
        "centers": ("Spleen", "Root"),
        "circuit": "Tribal / Ego",
        "explanation": (
            "Drive for ambition, advancement, and material evolution through alliances and persistence. "
            "It seeks progress that can endure, not merely flashy ascent."
        ),
    },

    "44-26": {
        "name": "Channel of Surrender",
        "gates": (44, 26),
        "centers": ("Spleen", "Ego / Will"),
        "circuit": "Tribal / Ego",
        "explanation": (
            "The instinct to recognize patterns from the past and strategically influence others. "
            "Strong for persuasion, memory, sales, and knowing what will or won’t work."
        ),
    },

    "21-45": {
        "name": "Channel of Money",
        "gates": (21, 45),
        "centers": ("Ego / Will", "Throat"),
        "circuit": "Tribal / Ego",
        "explanation": (
            "Management energy concerned with control, resources, and stewardship. "
            "At its best, it governs material affairs responsibly rather than hoarding authority like a nervous duke."
        ),
    },

    "37-40": {
        "name": "Channel of Community",
        "gates": (37, 40),
        "centers": ("Solar Plexus", "Ego / Will"),
        "circuit": "Tribal / Defense",
        "explanation": (
            "A bond-building channel centered on agreements, loyalty, reciprocity, and belonging. "
            "It supports families, teams, and communities through emotional contracts and mutual support."
        ),
    },

    "19-49": {
        "name": "Channel of Synthesis",
        "gates": (19, 49),
        "centers": ("Root", "Solar Plexus"),
        "circuit": "Tribal / Defense",
        "explanation": (
            "Sensitivity to needs, closeness, principles, and social belonging. "
            "It often drives change in relationships or group norms when emotional needs are no longer met."
        ),
    },

    "59-6": {
        "name": "Channel of Mating",
        "gates": (59, 6),
        "centers": ("Sacral", "Solar Plexus"),
        "circuit": "Tribal / Defense",
        "explanation": (
            "A potent bonding and intimacy channel that dissolves barriers between people. "
            "It can manifest as sexual chemistry, emotional merging, or powerful interpersonal closeness."
        ),
    },

    # =========================
    # CENTERING / INTEGRATION / INDIVIDUAL-ADJACENT
    # (Commonly listed separately, but part of the canonical 36)
    # =========================

    "10-34": {
        "name": "Channel of Exploration",
        "gates": (10, 34),
        "centers": ("G / Identity", "Sacral"),
        "circuit": "Individual / Integration",
        "explanation": (
            "Self-empowered life-force expressed through authentic behavior and personal conviction. "
            "This channel pushes a person to live according to what is true for them, often with a strong "
            "drive toward independence, embodied self-direction, and exploration through direct experience."
        ),
    },

    "25-51": {
        "name": "Channel of Initiation",
        "gates": (25, 51),
        "centers": ("G / Identity", "Ego / Will"),
        "circuit": "Individual / Centering",
        "explanation": (
            "A catalytic energy that initiates through shock, courage, and spiritual testing. "
            "It often disrupts complacency and pushes growth through bold encounters."
        ),
    },

}

HD_CIRCUIT_GROUPS = {
    "Individual": {
        "subcircuits": {
            "Integration": {
                "channels": ["10-20", "20-34", "10-57", "34-57"],
                "gates": (10, 20, 34, 57),
            },
            "Knowing": {
                "channels": ["1-8", "2-14", "3-60", "28-38", "20-57", "39-55", "12-22", "43-23", "61-24"],
                "gates": (1, 2, 3, 8, 12, 14, 20, 22, 23, 24, 28, 38, 39, 43, 55, 57, 60, 61),
            },
            "Centering": {
                "channels": ["25-51", "10-34"],
                "gates": (10, 25, 34, 51),
            },
        },
    },
    "Collective": {
        "subcircuits": {
            "Logic": {
                "channels": ["63-4", "17-62", "16-48", "18-58", "52-9", "15-5", "31-7"],
                "gates": (4, 5, 7, 9, 15, 16, 17, 18, 31, 48, 52, 58, 62, 63),
            },
            "Abstract": {
                "channels": ["64-47", "11-56", "35-36", "41-30", "42-53", "46-29", "33-13"],
                "gates": (11, 13, 29, 30, 33, 35, 36, 41, 42, 46, 47, 53, 56, 64),
            },
        },
    },
    "Tribal": {
        "subcircuits": {
            "Ego": {
                "channels": ["32-54", "44-26", "19-49", "40-37", "21-45"],
                "gates": (19, 21, 26, 32, 37, 40, 44, 45, 49, 54),
            },
            "Defense": {
                "channels": ["50-27", "59-6"],
                "gates": (6, 27, 50, 59),
            },
        },
    },
}

def format_gate_line_info(gate: int, line: int | None = None) -> str:
    gate_num = int(gate)
    gate_info = GATE_REFERENCE.get(gate_num, {"name": "Unknown Gate", "meaning": "No gate reference available."})
    header = f"Gate {gate_num} • {gate_info['name']}"
    body_lines = [
        f"• Core meaning: {gate_info['meaning']}",
        "• Reference: Human Design gate keynotes (Rave Mandala / I’Ching gate framework).",
    ]
    if line is not None:
        line_num = int(line)
        line_text = LINE_ARCHETYPES.get(line_num, "No line archetype available.")
        body_lines.extend(
            [
                f"• Line {line_num} archetype: {line_text}",
                "• Color/Tone/Base values for this activation are shown directly in the Human Design chart panel.",
            ]
        )
        header = f"Gate {gate_num} • Line {line_num}"
    return "\n".join([header, "", *body_lines])
