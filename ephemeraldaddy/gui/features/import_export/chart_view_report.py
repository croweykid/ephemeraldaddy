"""Chart View's analytics and prediction data for the single-chart Markdown export.

Values come from the same calculators as the right-hand panels. Explanations
reuse their Chart Info reference models; this report does not read the currently
selected right-hand tab or implicitly recalculate database norm snapshots.
"""
from __future__ import annotations

import html
import math
import re
from collections.abc import Mapping
from statistics import median
from typing import Any

from ephemeraldaddy.core.chart import chart_uses_houses


def _plain(value: object) -> str:
    text = str(value or "")
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.I)
    text = re.sub(r"</\s*(?:p|div|li|h[1-6])\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<\s*li(?:\s[^>]*)?>", "• ", text, flags=re.I)
    return html.unescape(re.sub(r"<[^>]*>", "", text)).strip()


def _nonempty(value: object) -> str:
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(x).strip() for x in value if str(x).strip())
    return str(value or "").strip()


def above_chart_median(values: Mapping[object, object]) -> list[tuple[object, float]]:
    """Strictly above the median of this chart's *whole* factor distribution.

    Zeros stay in the distribution. Missing/non-finite scores are excluded,
    and ties exactly at the median do not qualify.
    """
    scores: list[tuple[object, float]] = []
    for label, raw in values.items():
        try:
            score = float(raw)
        except (ValueError, TypeError):
            continue
        if math.isfinite(score):
            scores.append((label, score))
    if not scores:
        return []
    midpoint = median(score for _, score in scores)
    return sorted(
        ((label, score) for label, score in scores if score > midpoint),
        key=lambda item: (-item[1], str(item[0])),
    )


def _factor_explanation(kind: str, label: object, chart: object) -> str:
    from ephemeraldaddy.core.interpretations import NAKSHATRA_DESCRIPTIONS, SIGN_KEYWORDS
    from ephemeraldaddy.gui.features.chart_information.keyword_models import (
        build_element_definition_lines,
        build_house_keyword_text,
        build_mode_keyword_model,
        build_planet_keyword_text,
    )

    name = str(label).strip()
    if kind == "sign":
        keywords = SIGN_KEYWORDS.get(name, {}) or SIGN_KEYWORDS.get(name.lower(), {})
        best = _nonempty(keywords.get("best", []))
        worst = _nonempty(keywords.get("worst", []))
        return "; ".join(filter(None, (f"At best: {best}" if best else "", f"At worst: {worst}" if worst else "")))
    if kind == "body":
        return build_planet_keyword_text(name, display_body=name)
    if kind == "house":
        return build_house_keyword_text(int(label))
    if kind == "element":
        return "\n".join(build_element_definition_lines(name))
    if kind == "mode":
        model = build_mode_keyword_model(name)
        return f"Keywords: {', '.join(model.keywords)}; Signs: {', '.join(model.signs)}"
    if kind == "nakshatra":
        data = NAKSHATRA_DESCRIPTIONS.get(name, {})
        return "; ".join(
            f"{key.title().replace('_', ' ')}: {_nonempty(data[key])}"
            for key in ("essence", "shakti", "quality", "symbol")
            if _nonempty(data.get(key))
        )
    if kind == "quadrant":
        from ephemeraldaddy.gui.features.charts.quadrants import build_quadrant_info_html
        return _plain(build_quadrant_info_html(name))
    return ""


def build_chart_analytics_report(chart: object) -> str:
    """Report both dropdown modes of each Chart Analytics group, not just the visible one."""
    from ephemeraldaddy.gui.features.charts import metrics
    from ephemeraldaddy.gui.features.charts.quadrants import (
        calculate_dominant_quadrant_weights,
        calculate_quadrant_prevalence_counts,
    )
    from ephemeraldaddy.analysis.chart_type_identifier import chart_type_summary
    from ephemeraldaddy.core.interpretations import ASPECT_PATTERN_DEFS

    use_houses = bool(chart_uses_houses(chart))
    groups = [
        ("Dominant Signs", "sign", metrics.calculate_dominant_sign_weights),
        ("Sign Prevalence", "sign", metrics.calculate_sign_prevalence_counts),
        ("Dominant Bodies", "body", metrics.calculate_dominant_planet_weights),
        ("Bodies by Nakshatra Ruler", "body", metrics.calculate_sidereal_planet_prevalence_counts),
        ("Dominant Elements", "element", metrics.calculate_dominant_element_weights),
        ("Element Prevalence", "element", metrics.calculate_element_prevalence_counts),
        ("Dominant Nakshatras", "nakshatra", metrics.calculate_dominant_nakshatra_weights),
        ("Nakshatra Prevalence", "nakshatra", metrics.calculate_nakshatra_prevalence_counts),
        ("Dominant Modes", "mode", metrics.calculate_mode_weights),
        ("Modal Prevalence", "mode", metrics.calculate_modal_prevalence_counts),
    ]
    if use_houses:
        groups[4:4] = [
            ("Dominant Houses", "house", metrics.calculate_dominant_house_weights),
            ("House Prevalence", "house", metrics.calculate_house_prevalence_counts),
            ("Dominant Quadrants", "quadrant", calculate_dominant_quadrant_weights),
            ("Quadrant Prevalence", "quadrant", calculate_quadrant_prevalence_counts),
        ]
    output = [
        "## Chart Analytics",
        "",
        "Factors strictly above the median of their own chart distribution are listed below. "
        "This is a within-chart comparison, not a comparison to database norms.",
    ]
    for title, kind, calculate in groups:
        output.extend(["", f"### {title}", ""])
        try:
            values = calculate(chart)
            qualifying = above_chart_median(values)
            if not qualifying:
                output.append("No factors exceed the chart median.")
                continue
            for name, score in qualifying:
                factor = f"House {name}" if kind == "house" else f"Quadrant {name}" if kind == "quadrant" else str(name)
                output.append(f"**{factor}** — {score:.2f}")
                explanation = _factor_explanation(kind, name, chart)
                if explanation:
                    output.extend(["", explanation, ""])
        except Exception as exc:
            output.append(f"Not available: {exc}")

    output.extend(["", "### Body Dynamics", ""])
    try:
        dynamics = metrics.calculate_planet_dynamics_scores(chart)
        for axis in ("antagonizing", "enabling", "escalating"):
            scores = {
                name: float(row.get(axis, 0.0))
                for name, row in dynamics.items() if isinstance(row, Mapping)
            }
            output.extend(["", f"**{axis.title()} (above chart median)**"])
            for name, score in above_chart_median(scores):
                output.append(f"- {name}: {score:.2f} — {_factor_explanation('body', name, chart).replace(chr(10), '; ')}")
            if not above_chart_median(scores):
                output.append("- None")
    except Exception as exc:
        output.append(f"Body dynamics unavailable: {exc}")

    output.extend(["", "### Chart Type", ""])
    try:
        chart_type = chart_type_summary(chart)
        shape = str(chart_type.get("shape", "unknown")).replace("_", " ").title()
        output.append(f"Shape: {shape}")
        for pattern in chart_type.get("patterns", []) or []:
            definition = ASPECT_PATTERN_DEFS.get(pattern, {})
            output.append(
                f"- {definition.get('name', str(pattern).replace('_', ' ').title())}: "
                f"{definition.get('meaning_brief', 'No reference description.')}"
            )
    except Exception as exc:
        output.append(f"Chart type unavailable: {exc}")

    if not use_houses:
        output.extend(["", "Houses and quadrants omitted: reliable birth-time/house data unavailable."])
    return "\n".join(output)


def _trait_rows_report(chart: object, metadata: Mapping[str, Any] | None) -> list[str]:
    lines = ["### Traits — Database Norms", ""]
    if not isinstance(metadata, Mapping):
        return lines + [
            "Above DB norms: unavailable — no cached, chart-specific prediction results.",
            "",
            "Below DB norms: unavailable — no cached, chart-specific prediction results.",
            "",
            "Calculate Traits in the Predictions tab to populate these lists.",
        ]
    try:
        from ephemeraldaddy.analysis.traits import list_traits
        from ephemeraldaddy.gui.features.charts.trait_predictions_core import (
            _trait_info_html,
            _trait_prediction_rows_from_metadata,
        )

        traits = list_traits(active_only=True)
        rows = _trait_prediction_rows_from_metadata(traits, dict(metadata))
        lookup = {str(item.get("name", "")): item for item in traits}
        for direction, heading in (("above", "Above DB norms"), ("below", "Below DB norms")):
            lines.extend([f"**{heading}**", ""])
            selected = sorted(
                (row for row in rows if row.get("direction") == direction),
                key=lambda item: -abs(float(item.get("deviation", 0.0))),
            )
            if not selected:
                lines.append("No traits meet the 5 percentage-point deviation threshold.")
            for row in selected:
                name = str(row.get("name", ""))
                label = str(row.get("display_name") or name)
                lines.append(
                    f"- **{label}** — predicted {float(row['likelihood']):.1f}%; "
                    f"DB norm {float(row['database_average']):.1f}%; "
                    f"deviation {float(row['deviation']):+.1f} percentage points"
                )
                trait = lookup.get(name)
                if trait:
                    description = _plain(_trait_info_html(trait, chart, antithetical=bool(row.get("antithetical"))))
                    if description:
                        lines.append(f"  {description.replace(chr(10), ' ')}")
            lines.append("")
        if metadata.get("stale"):
            lines.extend(["Cached Traits predictions are stale; recalculate before relying on these values.", ""])
    except Exception as exc:
        lines.append(f"Trait descriptions unavailable: {exc}")
    return lines


def build_chart_predictions_report(
    chart: object,
    *,
    trait_metadata: Mapping[str, Any] | None = None,
    enneagram_scores: Mapping[int, float] | None = None,
) -> str:
    """Describe chart-specific Predictions, including both Traits norm directions."""
    output = ["## Predictions", ""]
    if trait_metadata is None:
        cache = getattr(chart, "_trait_prediction_metadata_cache", None)
        if isinstance(cache, dict):
            trait_metadata = cache.get("metadata")
    output.extend(_trait_rows_report(chart, trait_metadata))

    # These are chart-specific computations; they need no database-population scan.
    output.extend(["", "### OCEAN Personality", ""])
    try:
        from ephemeraldaddy.gui.features.predictions.ocean import (
            calculate_ocean_scores, build_ocean_trait_popout_info,
            ocean_scores_to_mbti_with_neuroticism_prefix,
        )
        scores = calculate_ocean_scores(chart)
        output.append(f"MBTI translation: {ocean_scores_to_mbti_with_neuroticism_prefix(scores)}")
        output.append("OCEAN signed scores: " + ", ".join(f"{k}={v:+.2f}" for k, v in scores.items()))
        strength = {k: abs(float(v)) for k, v in scores.items()}
        for key, _ in above_chart_median(strength):
            output.extend(["", _plain(build_ocean_trait_popout_info(chart, str(key))), ""])
    except Exception as exc:
        output.append(f"OCEAN unavailable: {exc}")

    output.extend(["", "### Enneagram", ""])
    if enneagram_scores is None:
        enneagram_scores = getattr(chart, "enneagram_type_weights", None)
    if isinstance(enneagram_scores, Mapping) and enneagram_scores:
        try:
            from ephemeraldaddy.analysis.enneagram import ENNEAGRAM
            from ephemeraldaddy.gui.features.charts.enneagram_predictions import (
                tritype_text_for_scores, enneagram_realm_summary_html,
            )
            scores = {int(k): float(v) for k, v in enneagram_scores.items()}
            output.append(f"Tritype: {tritype_text_for_scores(scores)}")
            output.append(_plain(enneagram_realm_summary_html(scores)))
            for key, score in above_chart_median(scores):
                definition = ENNEAGRAM.get(int(key), {})
                output.append(
                    f"- Type {key}: {score:.2f} — "
                    f"{_nonempty(definition.get('motivation', ''))} "
                    f"{_nonempty(definition.get('description', ''))}".strip()
                )
        except Exception as exc:
            output.append(f"Enneagram descriptions unavailable: {exc}")
    else:
        output.append("No calculated Enneagram scores available for this chart.")

    output.extend(["", "### Fantasy RPG", ""])
    try:
        from ephemeraldaddy.analysis.dnd.dnd_class_axes_v2 import score_dnd_statblock
        from ephemeraldaddy.analysis.dnd.dnd_definitions import DND_STAT_EXPLANATIONS
        from ephemeraldaddy.gui.features.charts.dnd_predictions_core import (
            _collect_ranked_class_payloads, _collect_ranked_species_payloads,
            format_dnd_class_info_text, format_dnd_species_info_text,
        )

        statblock = score_dnd_statblock(chart)
        stat_scores = {key: float(value) for key, value in statblock.scores.items()}
        output.append("Statblock: " + ", ".join(
            f"{key}={int(value)}" for key, value in stat_scores.items()
        ))
        for key, value in above_chart_median(stat_scores):
            definition = next(
                (item for item in DND_STAT_EXPLANATIONS.values()
                 if str(item.get("abbrev", "")).upper() == str(key).upper()), {}
            )
            output.append(
                f"- {key} {value:.0f} (modifier {int(statblock.modifiers.get(key, 0)):+d}): "
                f"{_nonempty(definition.get('description') or definition.get('definition'))}"
            )
        axis_scores, classes = _collect_ranked_class_payloads(chart)
        species = _collect_ranked_species_payloads(chart)
        output.extend(["", "**Class predictions above chart median**", ""])
        for name, score in above_chart_median({str(item["class_key"]): item["score"] for item in classes}):
            item = next(item for item in classes if str(item["class_key"]) == name)
            output.append(f"- {_plain(format_dnd_class_info_text(str(item['name']), name, axis_scores))}")
        output.extend(["", "**Species predictions above chart median**", ""])
        for index, score in above_chart_median({index: item["score"] for index, item in enumerate(species)}):
            item = species[index]
            output.append(
                f"- {_plain(format_dnd_species_info_text(str(item['family']), str(item['subtype']), score, list(item['evidence'])))}"
            )
    except Exception as exc:
        output.append(f"Fantasy RPG predictions unavailable: {exc}")

    output.extend(["", "### Gender Guesser", ""])
    try:
        from ephemeraldaddy.gui.features.charts.algorithmic_transparency import build_gender_guesser_breakdown_text
        output.append(_plain(build_gender_guesser_breakdown_text(chart)))
    except Exception as exc:
        output.append(f"Gender Guesser unavailable: {exc}")

    output.extend(["", "### Predicted Synastry", "",
                   "This comparison requires a selected database cohort and prediction mode; "
                   "it is not intrinsic to a single chart and has not been recalculated for this export."])
    return "\n".join(output)


def build_chart_view_report(
    chart: object,
    *,
    trait_metadata: Mapping[str, Any] | None = None,
    enneagram_scores: Mapping[int, float] | None = None,
) -> str:
    return "\n\n".join((
        build_chart_analytics_report(chart),
        build_chart_predictions_report(
            chart, trait_metadata=trait_metadata, enneagram_scores=enneagram_scores,
        ),
    ))


def collect_chart_export_prediction_context(owner: object, chart: object) -> dict[str, Any]:
    """Read prediction data for the *requested chart*, not the selected GUI tab.

    Traits uses the same cached-only metadata retrieval as the Predictions tab.
    It must not initiate a database-wide norm recomputation just to export.
    Enneagram uses the owner's configured scorer, not static default weights.
    """
    result: dict[str, Any] = {"trait_metadata": None, "enneagram_scores": None}
    try:
        from ephemeraldaddy.gui.features.charts.provenance import chart_is_non_aggregable
        if chart_is_non_aggregable(chart):
            return result
    except (AttributeError, TypeError):
        pass

    try:
        from ephemeraldaddy.gui.features.charts.trait_predictions import trait_metadata_for_chart
        metadata = trait_metadata_for_chart(owner, chart, cached_only=True)
        if isinstance(metadata, dict):
            result["trait_metadata"] = metadata
    except Exception:
        # The report renders an explicit unavailable state instead of leaking
        # another chart's Traits table or fabricating a DB norm.
        pass

    calculate_enneagram = getattr(owner, "_calculate_enneagram_type_weights", None)
    if callable(calculate_enneagram):
        try:
            scores = calculate_enneagram(chart)
            if isinstance(scores, Mapping):
                result["enneagram_scores"] = dict(scores)
        except Exception:
            pass
    return result
