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
    26: {"name": "The Cross of Rulership", "meaning": "Persuasion, memory, and strategic willpower."},
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
