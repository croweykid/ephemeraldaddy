"""Shared explanatory text builders for dominance panels."""

from __future__ import annotations

from typing import Callable

from ephemeraldaddy.core.chart import Chart, chart_uses_houses
from ephemeraldaddy.core.interpretations import (
    ASPECT_SCORE_MULTIPLIERS,
    DETRIMENT_WEIGHT,
    EXALTATION_WEIGHT,
    FALL_WEIGHT,
    HOUSE_WEIGHTS,
    NATAL_WEIGHT,
    NATURAL_HOUSE_PLANETS,
    NATURAL_HOUSE_SIGNS,
    PLANET_DETRIMENT,
    PLANET_EXALTATION,
    PLANET_FALL,
    PLANET_RULERSHIP,
    RULERSHIP_WEIGHT,
    aspect_orb_allowance,
    normalize_body_name,
)
from ephemeraldaddy.gui.features.charts.metrics import (
    CHART_RULER_BONUS,
    DISPOSITOR_PLANET_ATTENUATION,
    TIGHT_ASPECT_INTENSITY_MAX,
    TIGHT_ASPECT_INTENSITY_MIN,
    TIGHT_ASPECT_ORB_DEGREES,
    dominant_planet_keys,
    house_for_longitude,
    house_membership_weights,
    planet_weight,
)
from ephemeraldaddy.gui.features.charts.presentation import sign_for_longitude


def build_body_dominance_explanation_bullets(
    chart: Chart,
    body_name: str,
    display_body_name: Callable[[str], str],
) -> list[str]:
    lon = chart.positions.get(body_name)
    if lon is None:
        return []

    use_houses = chart_uses_houses(chart)
    houses = getattr(chart, "houses", None) if use_houses else None
    sign = sign_for_longitude(lon)
    house_num = house_for_longitude(houses, lon)
    canonical_body = normalize_body_name(body_name)
    display_name = str(display_body_name(body_name))
    natal_base_weight = float(NATAL_WEIGHT.get(canonical_body, 1.0))
    house_weight = float(HOUSE_WEIGHTS.get(house_num, 0.0)) if house_num else 0.0
    natural_sign_bonus = 6.0 if house_num and NATURAL_HOUSE_SIGNS.get(house_num) == sign else 0.0
    natural_planet_bonus = (
        6.0 if house_num and NATURAL_HOUSE_PLANETS.get(house_num) == canonical_body else 0.0
    )
    rulerships = PLANET_RULERSHIP.get(body_name) or ()
    rulership_bonus = float(RULERSHIP_WEIGHT) if sign in rulerships else 0.0
    exaltation = PLANET_EXALTATION.get(body_name)
    exaltation_bonus = float(EXALTATION_WEIGHT) if exaltation and sign == exaltation.get("sign") else 0.0
    detriments = PLANET_DETRIMENT.get(body_name) or ()
    detriment_penalty = float(DETRIMENT_WEIGHT) if sign in detriments else 0.0
    fall = PLANET_FALL.get(body_name)
    fall_penalty = float(FALL_WEIGHT) if fall and sign == fall.get("sign") else 0.0

    sign_weight = (
        natal_base_weight
        + house_weight
        + natural_sign_bonus
        + rulership_bonus
        + exaltation_bonus
        + detriment_penalty
        + fall_penalty
    )
    total_weight = sign_weight + natural_planet_bonus

    bullets = [f"{display_name} in {sign}" + (f", House {house_num}" if house_num else "") + "."]
    bullets.append(f"Natal base weight of {display_name} ({natal_base_weight:g} pts).")
    if sign in rulerships:
        sign_note = f"{sign} is native to {display_name} (+{rulership_bonus:g} pts)."
    else:
        sign_note = f"{sign} is not native to {display_name} (no sign-rulership bonus)."
    if house_num:
        house_native_sign = NATURAL_HOUSE_SIGNS.get(house_num)
        if natural_sign_bonus > 0:
            sign_note += f" House {house_num} is native to {sign} (+{natural_sign_bonus:g} pts)."
        else:
            sign_note += f" House {house_num} is native to {house_native_sign} (no house-sign bonus for {sign})."
    bullets.append(sign_note)
    if house_num and house_weight:
        bullets.append(f"House {house_num} placement weight (+{house_weight:g} pts).")

    if house_num and houses:
        membership = house_membership_weights(houses, lon)
        blended = [f"House {h}: {share * 100:.1f}%" for h, share in sorted(membership.items())]
        if blended:
            bullets.append("House blend (cusp proximity split for house charts): " + ", ".join(blended) + ".")

    if exaltation_bonus:
        bullets.append(f"Exalted in {sign} (+{exaltation_bonus:g} pts).")
    if detriment_penalty:
        bullets.append(f"In detriment in {sign} ({detriment_penalty:g} pts).")
    if fall_penalty:
        bullets.append(f"In fall in {sign} ({fall_penalty:g} pts).")
    if natural_planet_bonus:
        bullets.append(f"Natural house/body bonus in House {house_num} (+{natural_planet_bonus:g} pts).")
    bullets.append(
        "Placement subtotal before dispositor/aspect bonuses: "
        f"{sign_weight:g} pts"
        + (f"; after natural house/body additions: {total_weight:g} pts." if natural_planet_bonus else ".")
    )

    base_subtotals = {key: 0.0 for key in dominant_planet_keys(chart)}
    for key in base_subtotals:
        key_lon = chart.positions.get(key)
        if key_lon is None:
            continue
        key_house = house_for_longitude(houses, key_lon)
        base_subtotals[key] = float(planet_weight(key, key_lon, houses, key_house))

    asc_sign = sign_for_longitude(houses[0]) if houses and len(houses) >= 1 else None
    if asc_sign:
        for ruler, ruled_signs in PLANET_RULERSHIP.items():
            if asc_sign in ruled_signs and ruler in base_subtotals:
                base_subtotals[ruler] += CHART_RULER_BONUS

    snapshot_weights = dict(base_subtotals)
    for key, key_weight in snapshot_weights.items():
        key_lon = chart.positions.get(key)
        if key_lon is None:
            continue
        key_sign = sign_for_longitude(key_lon)
        rulers = [
            ruler
            for ruler, ruled_signs in PLANET_RULERSHIP.items()
            if key_sign in ruled_signs and ruler in base_subtotals
        ]
        if not rulers:
            continue
        transfer = key_weight * (DISPOSITOR_PLANET_ATTENUATION / len(rulers))
        for ruler in rulers:
            base_subtotals[ruler] += transfer

    aspect_bullets: list[str] = []
    for aspect in getattr(chart, "aspects", []) or []:
        p1 = str(aspect.get("p1", ""))
        p2 = str(aspect.get("p2", ""))
        if body_name not in {p1, p2}:
            continue
        np1 = normalize_body_name(p1)
        np2 = normalize_body_name(p2)
        if np1 not in base_subtotals or np2 not in base_subtotals:
            continue
        other = p2 if p1 == body_name else p1
        aspect_type = str(aspect.get("type", "")).strip() or "aspect"
        normalized_type = aspect_type.replace(" ", "_").lower()
        multiplier = float(ASPECT_SCORE_MULTIPLIERS.get(normalized_type, 0.0))
        if multiplier <= 0:
            continue
        allowance = aspect_orb_allowance(aspect_type, np1, np2)
        if allowance <= 0:
            continue
        orb = abs(float(aspect.get("delta", 0.0)))
        orb_factor = max(0.0, 1.0 - ((orb / allowance) ** 2))
        if orb_factor <= 0:
            continue
        intensity_bonus = 1.0
        if orb < TIGHT_ASPECT_ORB_DEGREES:
            tight_ratio = 1.0 - (orb / TIGHT_ASPECT_ORB_DEGREES)
            intensity_bonus = TIGHT_ASPECT_INTENSITY_MIN + (
                tight_ratio * (TIGHT_ASPECT_INTENSITY_MAX - TIGHT_ASPECT_INTENSITY_MIN)
            )
        aspect_gain = (base_subtotals[np1] + base_subtotals[np2]) * multiplier * orb_factor * intensity_bonus
        aspect_bullets.append(
            f"{display_name} {aspect_type} {display_body_name(other)} (+{aspect_gain:.2f} pts)."
        )

    bullets.extend(aspect_bullets[:10])
    return bullets
