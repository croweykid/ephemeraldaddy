"""Reference text helpers for Human Design gates/lines."""

from __future__ import annotations

import re

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
    {"name":"sensing","type":"ajna","gates":[64,47,11,56],"canonical_name":"abstract","circuit_family":"collective","function":"Processes life by reflecting on experience and turning it into meaning, images, and stories.","description":"This stream tends to understand things in hindsight rather than all at once."},
    {"name":"knowing","type":"ajna","gates":[61,24,43,23],"canonical_name":"knowing","circuit_family":"individual","function":"Works through sudden inner knowing and original insight.","description":"It often knows first and explains later, so its clarity can arrive in flashes."},
    {"name":"understanding","type":"ajna","gates":[63,4,17,62],"canonical_name":"logical","circuit_family":"collective","function":"Seeks patterns, proof, and clear logic. ","description":"This stream wants things to make sense, hold up under scrutiny, and be explained in practical terms."},

    {"name":"instinct","type":"spleen","gates":[54,32,44,26],"canonical_name":"tribal splenic","circuit_family":"tribal","function":"Tracks survival, timing, and what is materially or socially safe. ","description":"This stream reads what can be trusted, what has value, and what will hold up over time."},
    {"name":"intuition","type":"spleen","gates":[38,28,57,20],"canonical_name":"intuition (individual)","circuit_family":"individual","function":"Gives immediate, in-the-moment body awareness.","description":"It is subtle, fast, and spontaneous, often showing up as a quiet sense of what is right or wrong right now."},
    {"name":"taste","type":"spleen","gates":[58,18,48,16],"canonical_name":"judgement","circuit_family":"collective","function":"Evaluates quality, correctness, and what needs improvement.","description":"This stream notices what is off, what has depth, and what can be refined into something better."},

    {"name":"sensitivity","type":"solar plexus","gates":[19,49,37,40],"canonical_name":"need","circuit_family":"tribal","function":"Feels needs, agreements, closeness, and emotional boundaries in relationships.","description":"This stream is tuned to support, reciprocity, and whether a bond feels workable."},
    {"name":"emoting","type":"solar plexus","gates":[39,55,22,12],"canonical_name":"passion","circuit_family":"individual","function":"Expresses feeling in a deeply personal and changeable way.","description":"This stream moves through mood and emotional atmosphere, and its expression depends heavily on timing."},
    {"name":"feeling","type":"solar plexus","gates":[41,30,36,35],"canonical_name":"desire","circuit_family":"collective","function":"Learns through desire, experience, and emotional impact.","description":"This stream is driven to feel life directly and understand it by going through it."},
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

    "48-16": {
        "name": "Channel of the Wavelength",
        "gates": (48, 16),
        "centers": ("Spleen", "Ajna"),
        "circuit": "Collective / Abstract",
        "explanation": (
            "Combined intuitive depth with a capacity for repeittion to develop professional skill."
            "Achieving mastery in any logical process."
        ),
    },

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

HD_CIRCUIT_GROUPS: Dict[str, dict] = {
    'Individual': {'aliases': ['Empowerment', 'Mutation', 'Transformation'], 'subcircuits': {'Integration': {'aliases': ['Integration Channel Group', 'Integration / Unifying'], 'channels': [('10-20', 'Awakening', (10, 20)), ('20-34', 'Charisma', (20, 34)), ('10-57', 'Perfected Form', (10, 57)), ('34-57', 'Power', (34, 57))], 'gates': (10, 20, 34, 57), 'channel_count': 4}, 'Knowing': {'aliases': ['Knowing / Gnostic'], 'channels': [('1-8', 'Inspiration', (1, 8)), ('2-14', 'The Beat', (2, 14)), ('3-60', 'Mutation', (3, 60)), ('28-38', 'Struggle', (28, 38)), ('20-57', 'Brainwave', (20, 57)), ('39-55', 'Emoting', (39, 55)), ('12-22', 'Openness', (12, 22)), ('43-23', 'Structuring', (43, 23)), ('61-24', 'Awareness', (61, 24))], 'gates': (1, 2, 3, 8, 12, 14, 20, 22, 23, 24, 28, 38, 39, 43, 55, 57, 60, 61), 'channel_count': 9}, 'Centering': {'aliases': ['Centring', 'Centering / Calibration'], 'channels': [('25-51', 'Initiation', (25, 51)), ('10-34', 'Exploration', (10, 34))], 'gates': (10, 25, 34, 51), 'channel_count': 2}}, 'gates': (1, 2, 3, 8, 10, 12, 14, 20, 22, 23, 24, 25, 28, 34, 38, 39, 43, 51, 55, 57, 60, 61), 'channel_count': 15}, 
    'Collective': {'aliases': ['Sharing', 'Synergy', 'Change'], 'subcircuits': {'Logic': {'aliases': ['Understanding', 'Logic / Understanding', 'Logic / Pattern'], 'channels': [('63-4', 'Logic', (63, 4)), ('17-62', 'Acceptance', (17, 62)), ('16-48', 'Talent', (16, 48)), ('18-58', 'Judgment', (18, 58)), ('52-9', 'Concentration', (52, 9)), ('15-5', 'Rhythm', (15, 5)), ('31-7', 'The Alpha', (31, 7))], 'gates': (4, 5, 7, 9, 15, 16, 17, 18, 31, 48, 52, 58, 62, 63), 'channel_count': 7}, 'Abstract': {'aliases': ['Sensing', 'Abstract / Sensing', 'Sensing / Miracle'], 'channels': [('64-47', 'Abstraction', (64, 47)), ('11-56', 'Curiosity', (11, 56)), ('35-36', 'Transitoriness', (35, 36)), ('41-30', 'Recognition', (41, 30)), ('42-53', 'Maturation', (42, 53)), ('46-29', 'Discovery', (46, 29)), ('33-13', 'The Prodigal', (33, 13))], 'gates': (11, 13, 29, 30, 33, 35, 36, 41, 42, 46, 47, 53, 56, 64), 'channel_count': 7}}, 'gates': (4, 5, 7, 9, 11, 13, 15, 16, 17, 18, 29, 30, 31, 33, 35, 36, 41, 42, 46, 47, 48, 52, 53, 56, 58, 62, 63, 64), 'channel_count': 14}, 
    'Tribal': {'aliases': ['Support', 'Sustainability', 'Tradition'], 'subcircuits': {'Ego': {'aliases': ['Ego Circuit Group', 'Ego / Economic'], 'channels': [('32-54', 'Transformation', (32, 54)), ('44-26', 'Surrender', (44, 26)), ('19-49', 'Synthesis', (19, 49)), ('40-37', 'Community', (40, 37)), ('21-45', 'Money', (21, 45))], 'gates': (19, 21, 26, 32, 37, 40, 44, 45, 49, 54), 'channel_count': 5}, 'Defense': {'aliases': ['Defense / Nurture'], 'channels': [('50-27', 'Preservation', (50, 27)), ('59-6', 'Mating', (59, 6))], 'gates': (6, 27, 50, 59), 'channel_count': 2}}, 'gates': (6, 19, 21, 26, 27, 32, 37, 40, 44, 45, 49, 50, 54, 59), 'channel_count': 7}
}

HD_AUTHORITIES = {
    "emotional": (
        "Make decisions over time, not in the heat of the moment. "
        "You need emotional clarity, so sleep on big choices and wait until the wave settles."
    ),
    "sacral": (
        "Trust your gut response in the moment. "
        "This authority works through a clear body yes or no, not through overthinking."
    ),
    "splenic": (
        "Trust the first quiet instinct. "
        "This authority is immediate, subtle, and only speaks once, so it is about instant body knowing."
    ),
    "ego": (
        "Decide from real desire and available willpower. "
        "What matters is whether you truly want it and have the energy to back it."
    ),
    "ego_manifested": (
        "Decide from what you truly want, then say it clearly and act on it. "
        "This is desire and will expressed directly."
    ),
    "ego_projected": (
        "Talk it out and listen for whether your desire feels true when you say it. "
        "This is still will-based authority, but clarity comes through your spoken words."
    ),
    "self_projected": (
        "Talk it out and listen to your own voice. "
        "If it sounds like you and feels like your direction, that is your answer."
    ),
    "mental": (
        "Do not force a fast answer. "
        "Clarity comes by talking things through in the right environment with trusted people, "
        "so you can hear yourself clearly."
    ),
    "environmental": (
        "Do not force a fast answer. "
        "Clarity comes by talking things through in the right environment with trusted people, "
        "so you can hear yourself clearly."
    ),
    "sounding_board": (
        "Do not force a fast answer. "
        "Clarity comes by talking things through in the right environment with trusted people, "
        "so you can hear yourself clearly."
    ),
    "lunar": (
        "Give major decisions a full lunar cycle. "
        "You are not meant to decide on the spot; clarity comes over roughly 29 days."
    ),
}

HD_CENTERS: Dict[str, dict[str, str]] = {
    "Head": {
        "center": "Head",
        "color": "#6E5A7E",  # dusty violet
        "description": "The pressure to ask, chase, and crack the big questions. This is where ideas, doubts, and mental pressures start buzzing.",
        "defined": "Your mind generates a steady stream of questions and inspiration. You tend to process mental pressure in a consistent way instead of getting hijacked by every random question in the room.",
        "undefined": "You pick up other people's questions, doubts, and mental pressure fast. The trap is treating every open loop around you like your personal problem to solve.",
    },
    "Ajna": {
        "center": "Ajna",
        "color": "#4F5D75",  # stormy indigo
        "description": "How you turn raw input into a framework. This is the part that categorizes, compares, concludes, and decides what makes sense.",
        "defined": "You have a stable way of thinking. Your opinions and mental process tend to be coherent, recognizable, and hard to bend just because the room changed.",
        "undefined": "You can see many sides and hold multiple frameworks, but you may feel pressure to sound certain when you are not. The trap is performing certainty to avoid looking mentally unsettled.",
    },
    "Throat": {
        "center": "Throat",
        "color": "#4E6B6F",  # muted mineral blue
        "description": "Speech, action, declaration, naming, visibility: this is where inner energy gets expressed into the world.",
        "defined": "Your way of speaking or acting has a repeatable signature. People tend to recognize your delivery, timing, and style because it comes through in a consistent way.",
        "undefined": "Expression is inconsistent and highly affected by context. The trap is forcing speech, posting, or action just to be noticed, included, or taken seriously.",
    },
    "G": {
        "center": "G",
        "color": "#6F7B4D",  # moss green
        "description": "Your inner north star: identity, direction, style of love. Not what you think you should be, but the lane your whole self keeps drifting toward.",
        "defined": "Your sense of self has continuity. Even when life changes, there is usually a durable inner thread of identity, direction, and what feels like your lane.",
        "undefined": "Your identity is more porous and environment-sensitive. The trap is hunting for a fixed label or borrowed purpose, when in practice the right people and places shape everything here.",
    },
    "Ego": {
        "center": "Ego",
        "color": "#A28652",  # worn ochre
        "description": "Willpower, value, promises, ambition, and the material push to get or secure something.  This is what says, 'I can do it, I’ll prove it, I’ll get the deal, and I want the credit.''",
        "defined": "You have reliable access to willpower in the moments that matter. You can genuinely commit, compete, bargain, and follow through when your heart is in it.",
        "undefined": "Willpower is inconsistent, and that is not a defect. The trap is overpromising, overworking, or trying to prove your worth to people who were not qualified to judge it in the first place.",
    },
    "Spleen": {
        "center": "Spleen",
        "color": "#7A8450",  # sage-lime
        "description": "Instinct, survival, health, and immediate body intelligence. Fast, quiet, and practical: what feels off, what feels safe, what to keep, what to drop, before your mind catches up.",
        "defined": "Your instincts tend to fire cleanly in the moment. You have a more reliable feel for timing, risk, and what your body is telling you right now.",
        "undefined": "You amplify fear and survival pressure. The trap is hanging on to people, routines, jobs, or situations because letting go feels scarier than staying, even when staying is clearly not good for you.",
    },
    "Solar Plexus": {
        "center": "Solar Plexus",
        "color": "#B79A4A",  # muted amber
        "description": "Emotion, desire, reaction, sensitivity, and wave-based clarity. This is not a calm spreadsheet; it is the feeling field.",
        "defined": "You run on your own emotional wave. Feelings rise and fall over time, so clarity is something you wait for rather than force on the spot.",
        "undefined": "You take in and amplify other people's emotions strongly. The trap is avoiding confrontation, smoothing over tension, or mistaking the room's emotional weather for your own settled truth.",
    },
    "Sacral": {
        "center": "Sacral",
        "color": "#B56F3A",  # burnt orange
        "description": "Life-force for work, sex, stamina, repetition, and building. This is the deep bodily response that says yes, no, more, enough.",
        "defined": "You have sustainable access to generative energy when something gets a real bodily response from you. When used correctly, this center supports steady work, vitality, and satisfaction.",
        "undefined": "Your stamina is inconsistent, but you can still amplify other people's work energy and keep going too long. The trap is quitting only after exhaustion instead of recognizing earlier that the fuel was borrowed.",
    },
    "Root": {
        "center": "Root",
        "color": "#8A4B3C",  # clay red
        "description": "Stress, adrenaline, urgency, and the pressure to get moving. This is the engine room of deadlines, drive, and survival push.",
        "defined": "You handle pressure in a steadier, more predictable way. Stress still exists, but it is less likely to feel like a constant external emergency siren.",
        "undefined": "You amplify outside pressure and often feel pushed to act fast just to get relief. The trap is rushing, clearing tasks for the sake of discharge, and confusing urgency with correctness.",
    },
}

HD_AUTHORITY_COLORS = {
    "emotional":  HD_CENTERS["Solar Plexus"]["color"],
    "sacral":  HD_CENTERS["Sacral"]["color"],
    "splenic":  HD_CENTERS["Spleen"]["color"],
    "ego":  HD_CENTERS["Ego"]["color"],
    "ego_manifested": HD_CENTERS["Ego"]["color"],
    "ego_projected": HD_CENTERS["Ego"]["color"],
    "self_projected": HD_CENTERS["G"]["color"],
    "mental": HD_CENTERS["Head"]["color"],
    "environmental":  HD_CENTERS["Ajna"]["color"],
    "sounding_board":  HD_CENTERS["Throat"]["color"],
    "lunar": "#00ffff", #'Moon' colored #n=No inner authority
}

HD_AUTHORITY_ALIASES: dict[str, str] = {
    "No Inner Authority": "Lunar",
}

def normalize_hd_authority_key(value: str) -> str:
    """Return a normalized authority key suitable for dictionary lookup."""
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value).strip().casefold()).strip("_")
    alias_key_map = {
        "no_inner_authority": "lunar",
        "mental_environmental_sounding_board": "mental",
    }
    return alias_key_map.get(normalized, normalized)


def authority_key_to_label(key: str) -> str:
    normalized = normalize_hd_authority_key(key)
    if normalized == "self_projected":
        return "Self-Projected"
    return normalized.replace("_", " ").title()


def canonicalize_hd_authority_label(value: str) -> str:
    return authority_key_to_label(normalize_hd_authority_key(value))

HD_DEFINITIONS = {
    "single_definition": (
        "Your defined centers are all connected as one system. "
        "Your processing tends to be self-contained and internally consistent."
    ),
    "split_definition": (
        "Your defined centers are split into two separate groups. "
        "You may feel like you process things in two tracks rather than one continuous flow."
    ),
    "triple_split_definition": (
        "Your defined centers are split into three separate groups. "
        "You often need more movement, variety, or time before everything clicks together."
    ),
    "quadruple_split_definition": (
        "Your defined centers are split into four separate groups. "
        "Your processing is highly compartmentalized, so time and the right setting matter a lot."
    ),
    "no_definition": (
        "No centers are defined. "
        "This is the Reflector setup, where nothing is fixed in the same way as other charts, "
        "so timing and environment matter more."
    ),
}

HD_TYPES = {
    "manifestor": (
        "A starter type. "
        "Manifestors are here to initiate, get things moving, and act independently."
    ),
    "generator": (
        "A sustainable energy type. "
        "Generators are here to build, work, and respond to what life brings them."
    ),
    "manifesting_generator": (
        "A fast-moving Generator subtype. "
        "Manifesting Generators are built to respond first, then move quickly once the body says yes."
    ),
    "projector": (
        "A guidance type. "
        "Projectors are here to understand people and direct energy well, not to run on constant output."
    ),
    "reflector": (
        "A sampling type with no fixed definition. "
        "Reflectors are highly affected by their surroundings and need time before major decisions."
    ),
}

HD_TYPE_COLORS = {
    "manifestor":"",
    "generator": "",
    "manifesting_generator": "",
    "projector": "",
    "reflector": "",
}

HD_STRATEGIES = {
    "to_inform": (
        "Tell the people who will be affected before you act. "
        "This is not asking permission; it is reducing pushback and confusion."
    ),
    "wait_to_respond": (
        "Do not force the first move. "
        "Let life give you something to respond to, then follow the body's response."
    ),
    "respond_then_move": (
        "Respond first, then move. "
        "Your speed works best when it comes after a real body yes."
    ),
    "respond_then_inform": (
        "Respond first, then let people know what you are doing if they will be affected. "
        "The response comes first; the informing keeps things smoother."
    ),
    "wait_for_invitation": (
        "Wait for real recognition and invitation in the big areas of life. "
        "Your guidance works best when it is wanted."
    ),
    "wait_a_lunar_cycle": (
        "For major decisions, give it a full lunar cycle. "
        "Time is part of how you get clarity."
    ),
}

HD_PROFILES = {
    "1/3": (
        "A researcher who learns by testing things in real life. "
        "This profile wants a solid foundation and usually learns what works by direct experience."
    ),
    "1/4": (
        "A researcher whose influence works through relationships. "
        "This profile wants to understand things deeply, then share what it knows through its network."
    ),
    "2/4": (
        "A naturally gifted person who needs both alone time and connection. "
        "This profile often does best when other people recognize its talent and draw it out."
    ),
    "2/5": (
        "A private natural who ends up being seen as a practical problem-solver. "
        "This profile prefers space, but others often expect it to help or fix things."
    ),
    "3/5": (
        "An experimenter with practical impact. "
        "This profile learns through trial and error, then turns those lessons into useful solutions."
    ),
    "3/6": (
        "A long-term experimenter who grows into wisdom. "
        "This profile learns through lived testing early on, then becomes more observant and eventually more exemplary."
    ),
    "4/1": (
        "A fixed, steady profile built on relationships and knowledge. "
        "This profile is less adaptable than most and tends to stay rooted in its own way of seeing things."
    ),
    "4/6": (
        "A relationship-based profile that matures into a role model. "
        "Its life is shaped by community, trust, and eventually leading by example."
    ),
    "5/1": (
        "A practical solver with strong research behind it. "
        "This profile is often looked to for answers and needs a solid knowledge base to support what it offers."
    ),
    "5/2": (
        "A behind-the-scenes natural who gets pulled into helping. "
        "This profile often prefers privacy, but other people project leadership or solutions onto it."
    ),
    "6/2": (
        "A natural talent that matures into a role model over time. "
        "This profile tends to live in stages: early experimentation, a more detached middle phase, and later wisdom."
    ),
    "6/3": (
        "A highly experiential profile that becomes wise through a lot of real-world testing. "
        "This profile can have a bumpy path early on, then grows into grounded perspective."
    ),
}


# Note: COLORS here use the standard Motivation naming convention.
HD_COLORS = [
    {"value": 1, "name": "Fear"},
    {"value": 2, "name": "Hope"},
    {"value": 3, "name": "Desire"},
    {"value": 4, "name": "Need"},
    {"value": 5, "name": "Guilt"},
    {"value": 6, "name": "Innocence"},
]

HD_TONES = [
    {"value": 1, "name": "Security",    "orientation": "Left"},
    {"value": 2, "name": "Uncertainty", "orientation": "Left"},
    {"value": 3, "name": "Action",      "orientation": "Left"},
    {"value": 4, "name": "Meditation",  "orientation": "Right"},
    {"value": 5, "name": "Judgment",    "orientation": "Right"},
    {"value": 6, "name": "Acceptance",  "orientation": "Right"},
]

HD_BASES = [
    {"value": 1, "name": "Reactive"},
    {"value": 2, "name": "Integrative"},
    {"value": 3, "name": "Objective"},
    {"value": 4, "name": "Progressive"},
    {"value": 5, "name": "Subjective"},
]

def format_gate_line_info(gate: int, line: int | None = None) -> str:
    gate_num = int(gate)
    gate_info = GATE_REFERENCE.get(gate_num, {"name": "Unknown Gate", "meaning": "No gate reference available."})
    header = f"Gate {gate_num} • {gate_info['name']}"
    body_lines = [f"Gate {gate_num}: {gate_info['meaning']}"]
    if line is not None:
        line_num = int(line)
        line_text = LINE_ARCHETYPES.get(line_num, "No line archetype available.")
        body_lines.append(f"Line {line_num} Archetype: {line_text}")
        header = f"Gate {gate_num} • Line {line_num}"
    return "\n".join([header, "", *body_lines])
