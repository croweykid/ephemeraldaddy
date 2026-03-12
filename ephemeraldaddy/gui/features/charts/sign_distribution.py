"""Sign distribution view options."""

from __future__ import annotations

SIGN_DISTRIBUTION_DROPDOWN_OPTIONS: list[tuple[str, str]] = [
    ("Sun Sign", "Sun"),
    ("Moon Sign", "Moon"),
    ("Mercury Sign", "Mercury"),
    ("Venus Sign", "Venus"),
    ("Mars Sign", "Mars"),
    ("Jupiter Sign", "Jupiter"),
    ("Saturn Sign", "Saturn"),
    ("Uranus Sign", "Uranus"),
    ("Neptune Sign", "Neptune"),
    ("Pluto Sign", "Pluto"),
    ("Rising Sign (Asc/1st)", "AS"),
    ("MC (10th)", "MC"),
]

SIGN_DISTRIBUTION_MODE_LABELS: dict[str, str] = {
    mode_value: mode_label for mode_label, mode_value in SIGN_DISTRIBUTION_DROPDOWN_OPTIONS
}
