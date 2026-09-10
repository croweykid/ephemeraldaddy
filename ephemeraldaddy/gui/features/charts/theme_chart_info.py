"""Transitional Theme Chart Info integration facade.

Presentation lives in :mod:`ephemeraldaddy.gui.features.chart_information`.
This staging-module adapter is the only code that knows the legacy window-owner
attributes until the predictions panel itself moves to its approved package.
"""

from __future__ import annotations

from typing import Any, Mapping

from ephemeraldaddy.core.theme_reference import THEME_FAMILIES, themes_in_family
from ephemeraldaddy.gui.features.chart_information.theme_family_presenter import (
    present_theme_family_chart_info,
)


def show_theme_family_chart_info(owner: Any, family_key: str) -> None:
    """Adapt legacy owner state to the narrow Chart Information presenter API."""
    chart = getattr(owner, "_themes_prediction_chart", None)
    if chart is None or family_key not in THEME_FAMILIES:
        return
    scores = getattr(owner, "_theme_prediction_subtheme_scores", None)
    if not isinstance(scores, Mapping):
        scores = None
    context = getattr(owner, "_theme_prediction_activation_context", None)
    if not isinstance(context, Mapping):
        context = None

    cache = getattr(owner, "_theme_prediction_evidence_by_family", None)
    if not isinstance(cache, dict):
        cache = {}
        owner._theme_prediction_evidence_by_family = cache
    evidence = cache.get(family_key)
    if not isinstance(evidence, Mapping) and context is not None:
        from ephemeraldaddy.analysis.theme_evidence import (
            calculate_theme_factor_evidence_from_context,
        )

        evidence = calculate_theme_factor_evidence_from_context(
            context, tuple(themes_in_family(family_key))
        )
        cache[family_key] = evidence
    if not isinstance(evidence, Mapping):
        evidence = None

    present_theme_family_chart_info(
        chart=chart,
        family_key=family_key,
        output=getattr(owner, "chart_info_output", None),
        set_panel_mode=getattr(owner, "_set_chart_info_panel_mode", None),
        subtheme_scores=scores,
        activation_context=context,
        evidence_by_theme=evidence,
    )


def _handle_theme_prediction_row_clicked(owner: Any, index: Any, theme_predictions: Any) -> None:
    """Handle only clicks on the Theme-name column, not numeric cells."""
    if not getattr(index, "isValid", lambda: False)() or int(index.column()) != 0:
        return
    family_key = index.data(theme_predictions.THEME_ROW_KEY_ROLE)
    if family_key:
        show_theme_family_chart_info(owner, str(family_key))


def install_theme_chart_info(theme_predictions: Any) -> None:
    """Attach the transitional click adapter without modifying ``app.py``."""
    if getattr(theme_predictions, "_ephemeraldaddy_theme_chart_info_installed", False):
        return
    original_configure = theme_predictions.configure_theme_prediction_table

    def configure_theme_prediction_table(owner: Any, table: Any) -> None:
        original_configure(owner, table)
        if getattr(table, "_ephemeraldaddy_theme_chart_info_connected", False):
            return
        table.clicked.connect(
            lambda index: _handle_theme_prediction_row_clicked(owner, index, theme_predictions)
        )
        table._ephemeraldaddy_theme_chart_info_connected = True

    theme_predictions.configure_theme_prediction_table = configure_theme_prediction_table
    theme_predictions._ephemeraldaddy_theme_chart_info_installed = True
