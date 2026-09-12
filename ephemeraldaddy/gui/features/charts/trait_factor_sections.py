"""Install signed Trait Prediction evidence sections in Chart Info."""

from __future__ import annotations

import html
from types import ModuleType
from typing import Any, Mapping

from ephemeraldaddy.gui.features.predictions.trait_factor_explanations import (
    build_trait_factor_evidence,
    missing_factor_html,
)


def install_trait_factor_sections(core: ModuleType) -> None:
    """Replace the legacy three-bucket Trait evidence block with six signed buckets."""
    if bool(getattr(core, "_ephemeraldaddy_trait_factor_sections_installed", False)):
        return

    original_trait_info_html = core._trait_info_html

    def trait_info_html_with_signed_sections(
        trait: dict[str, Any],
        chart: Any | None = None,
    ) -> str:
        base_html = original_trait_info_html(trait, None)
        if chart is None:
            return base_html

        name = str(trait.get("name", "")).strip() or "Trait"
        chart_name = str(getattr(chart, "name", "") or "").strip()
        matching_factors_header = (
            f"Matching factors in {html.escape(chart_name)}'s chart:"
            if chart_name
            else "Matching factors in this chart:"
        )
        raw_profile = trait.get("profile", {})
        profile: Mapping[str, Any] = raw_profile if isinstance(raw_profile, Mapping) else {}
        matches = core.matched_weighted_criteria(chart, profile)
        evidence = build_trait_factor_evidence(chart, profile, matches=matches)

        def dominance_labels(prefix: str = "") -> set[str]:
            labels = {
                str(value)
                for category in ("signs", "bodies", "nakshatras")
                for value, weight in core.weighted_string_entries(
                    profile.get(f"{prefix}{category}", {})
                ).items()
                if float(weight) != 0.0
            }
            labels.update(
                f"House {value}"
                for value, weight in core.weighted_house_entries(
                    profile.get(f"{prefix}houses", {})
                ).items()
                if float(weight) != 0.0
            )
            return labels

        normal_dominance = dominance_labels()
        anti_dominance = dominance_labels("anti")

        def factor_list(
            values: tuple[str, ...],
            color: str,
            *,
            dominance: set[str],
        ) -> str:
            return "".join(
                f"<li style='margin:2px 0; color:{color};'>"
                f"{html.escape(value)}"
                f"{' above baseline in chart' if value in dominance else ''}</li>"
                for value in values
            )

        def missing_list(values: tuple[str, ...], color: str) -> str:
            return "".join(
                f"<li style='margin:2px 0; color:{color};'>"
                f"{missing_factor_html(value)}</li>"
                for value in values
            )

        def section(
            title: str,
            rows: str,
            *,
            heading_color: str,
            top_margin: int = 5,
        ) -> str:
            if not rows:
                return ""
            return (
                f"<div style='margin-top:{top_margin}px; font-size:12px; "
                f"font-weight:700; color:{heading_color};'>{html.escape(title)}</div>"
                f"<ul style='margin:3px 0 5px 18px; padding:0;'>{rows}</ul>"
            )

        evidence_html = (
            "<div style='height:12px;'></div>"
            f"<div style='font-size:12px; font-weight:700; color:{core.CHART_DATA_HIGHLIGHT_COLOR};'>"
            f"{matching_factors_header}</div>"
            "<div style='height:12px;'></div>"
        )
        evidence_html += section(
            "Positive Supporting Indicators",
            factor_list(evidence.supporting, "#d9f2de", dominance=normal_dominance),
            heading_color="#9fd6aa",
            top_margin=0,
        )
        evidence_html += section(
            "Missing Positive Indicators",
            missing_list(evidence.missing, "#eadfb4"),
            heading_color="#d8c27a",
        )
        evidence_html += section(
            "Inverse Correlations Present",
            factor_list(evidence.inverse_present, "#f0d3d3", dominance=normal_dominance),
            heading_color="#e1a1a1",
        )
        evidence_html += section(
            "Inverse Correlations Missing",
            missing_list(evidence.inverse_missing, "#c8c8c8"),
            heading_color="#b8b8b8",
        )

        has_negative_indicators = bool(
            evidence.negative_indicators_present
            or evidence.negative_indicators_missing
        )
        if has_negative_indicators:
            evidence_html += section(
                "Negative Indicators Present",
                factor_list(
                    evidence.negative_indicators_present,
                    "#f0d3d3",
                    dominance=anti_dominance,
                ),
                heading_color="#e1a1a1",
            )
            evidence_html += section(
                "Missing Negative Indicators",
                missing_list(evidence.negative_indicators_missing, "#c8c8c8"),
                heading_color="#b8b8b8",
            )
        else:
            evidence_html += (
                "<div style='margin-top:5px; font-size:10px; color:#b8b8b8;'>"
                f"No negative indicators are defined for '{html.escape(name)}' trait."
                "</div>"
            )

        return base_html + evidence_html

    core._trait_info_html = trait_info_html_with_signed_sections
    core._ephemeraldaddy_trait_factor_sections_installed = True
