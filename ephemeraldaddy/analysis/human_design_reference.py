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


def format_gate_line_info(gate: int, line: int | None = None) -> str:
    gate_num = int(gate)
    header = f"Gate {gate_num}"
    body_lines = [
        f"• Gate {gate_num} is active in this Human Design chart.",
        "• Gate activations are calculated from tropical geocentric longitudes and mapped onto the Rave Mandala.",
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
