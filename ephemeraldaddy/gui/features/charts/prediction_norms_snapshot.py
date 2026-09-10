# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.
"""Static Predictions norm snapshot facade.

The implementation core remains stable while this facade owns population sections
that must be regenerated only by the explicit Recalculate DB Norms action.
"""

from __future__ import annotations

import math
import time
from typing import Any, Callable, Mapping

from ephemeraldaddy.analysis.theme_prominence import (
    calculate_database_theme_family_averages,
    theme_definition_signature,
)
from ephemeraldaddy.core.theme_reference import THEME_FAMILIES
from ephemeraldaddy.gui.features.charts import prediction_norms_snapshot_core as _core

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


def enneagram_type_snapshot_averages(
    snapshot: Mapping[str, Any] | None = None,
) -> dict[int, float]:
    """Read a complete finite Enneagram 1-9 baseline from the selected snapshot."""
    payload = dict(snapshot or _core.load_prediction_norms_snapshot())
    rows = payload.get("enneagram_type_raw_averages", {}) if isinstance(payload, dict) else {}
    if not isinstance(rows, Mapping):
        return {}
    averages: dict[int, float] = {}
    for enneagram_type in range(1, 10):
        if enneagram_type in rows:
            raw_value = rows[enneagram_type]
        elif str(enneagram_type) in rows:
            raw_value = rows[str(enneagram_type)]
        else:
            return {}
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            return {}
        if not math.isfinite(value):
            return {}
        averages[enneagram_type] = value
    return averages if len(averages) == 9 else {}


def _calculate_enneagram_snapshot_section(charts: list[Any]) -> tuple[dict[int, float], str]:
    """Calculate the Enneagram population baseline with the production scorer."""
    from ephemeraldaddy.gui.features.charts import enneagram_predictions

    def calculate_type_weights(chart: Any) -> dict[int, float]:
        return enneagram_predictions.calculate_enneagram_type_weights(
            chart,
            enneagram=enneagram_predictions.ENNEAGRAM_REALMS,
            calculate_sign_weights=enneagram_predictions.calculate_dominant_sign_weights,
            calculate_body_weights=enneagram_predictions.calculate_dominant_planet_weights,
            calculate_house_weights=enneagram_predictions.calculate_dominant_house_weights,
            chart_uses_houses=enneagram_predictions.chart_uses_houses,
        )

    averages = enneagram_predictions.calculate_database_enneagram_type_averages(
        charts,
        calculate_type_weights=calculate_type_weights,
    )
    if charts and set(averages) != set(range(1, 10)):
        raise RuntimeError(
            "Could not calculate a complete Enneagram 1-9 baseline for the Predictions norms snapshot."
        )
    return averages, enneagram_predictions._enneagram_definition_signature()


def refresh_prediction_norms_snapshot(
    owner: Any,
    *,
    user_initiated: bool = False,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Rebuild all snapshot-backed Predictions population norms on explicit request.

    Deliberately included here: custom Traits, semantic Theme macro-families,
    Fantasy RPG alignment traits, Fantasy RPG Stat Block raw averages, and
    Enneagram type averages. Sign Dominance, Fantasy RPG Species/Class, and
    OCEAN are intentionally not part of this snapshot.
    """
    if not user_initiated:
        raise _core.ExplicitNormRecalculationRequired(
            "Whole-database prediction norms can only be rebuilt by the explicit "
            "Recalculate DB Norms action."
        )

    last_terminal_percent = -5

    def report(
        completed: int,
        total: int,
        message: str,
        *,
        force_terminal: bool = False,
    ) -> None:
        nonlocal last_terminal_percent
        line = f"[Prediction Norms] {completed}/{total}: {message}"
        percent = int((float(completed) / float(total)) * 100.0) if total else 0
        if force_terminal or completed == total or percent >= last_terminal_percent + 5:
            _core.logger.info(line)
            print(line, flush=True)
            last_terminal_percent = percent
        if progress_callback is not None:
            progress_callback(completed, total, message)

    charts = _core._load_norm_charts(owner)
    traits = _core.list_traits(active_only=True)
    try:
        from ephemeraldaddy.gui.features.charts.dnd_predictions import _dnd_alignment_trait_items

        dnd_alignment_traits = _dnd_alignment_trait_items()
    except Exception:
        _core.logger.exception(
            "Could not include Fantasy RPG alignment traits in Predictions norms snapshot."
        )
        dnd_alignment_traits = []

    trait_baselines: dict[str, dict[str, Any]] = {}
    trait_groups = (
        ("custom_trait", traits),
        ("dnd_alignment", dnd_alignment_traits),
    )
    active_trait_groups = [(source, rows) for source, rows in trait_groups if rows]
    # Work units track completed calculations rather than elapsed-time guesses:
    # loading, each trait family, each D&D chart, Enneagram, Themes, and saving.
    total_work = 4 + len(active_trait_groups) + len(charts)
    completed_work = 1
    report(
        completed_work,
        total_work,
        f"Loaded {len(charts)} database charts",
        force_terminal=True,
    )
    for source, group_traits in active_trait_groups:
        report(
            completed_work,
            total_work,
            f"Calculating {source.replace('_', ' ')} baselines",
            force_terminal=True,
        )
        from ephemeraldaddy.gui.features.charts.trait_predictions import _database_trait_averages

        averages = _database_trait_averages(owner, group_traits, force_refresh_stale=True)
        for trait in group_traits:
            name = str(trait.get("name", "") or "").strip()
            if not name or name not in averages:
                continue
            payload = _core._trait_payload(trait)
            trait_baselines[payload["key"]] = {
                **payload,
                "source": source,
                "db_average": float(averages[name]),
            }
        completed_work += 1
        report(completed_work, total_work, f"Completed {source.replace('_', ' ')} baselines")

    dnd_stat_totals = {key: 0.0 for key in _core.DND_STAT_KEYS}
    dnd_stat_count = 0
    for chart_index, chart in enumerate(charts, start=1):
        raw_scores = _core.calculate_weighted_criteria_scores(
            chart,
            predictors=_core.DND_STAT_PREDICTORS,
        )
        for key in _core.DND_STAT_KEYS:
            dnd_stat_totals[key] += float(raw_scores.get(key, 0.0))
        dnd_stat_count += 1
        completed_work += 1
        report(
            completed_work,
            total_work,
            f"Calculated Fantasy RPG stats for chart {chart_index} of {len(charts)}",
        )
    dnd_stat_raw_averages = (
        {
            key: dnd_stat_totals[key] / float(dnd_stat_count)
            for key in _core.DND_STAT_KEYS
        }
        if dnd_stat_count
        else {}
    )

    report(
        completed_work,
        total_work,
        "Calculating Enneagram baselines",
        force_terminal=True,
    )
    enneagram_type_raw_averages, enneagram_definition_signature = (
        _calculate_enneagram_snapshot_section(charts)
    )
    completed_work += 1
    report(completed_work, total_work, "Completed Enneagram baselines")

    report(
        completed_work,
        total_work,
        "Calculating availability-stratified Theme baselines",
        force_terminal=True,
    )
    theme_family_raw_averages = calculate_database_theme_family_averages(charts)
    if charts and set(theme_family_raw_averages) != set(THEME_FAMILIES):
        raise RuntimeError(
            "Could not calculate complete Theme family baselines for the Predictions norms snapshot."
        )
    theme_family_definition_signature = theme_definition_signature()
    completed_work += 1
    report(completed_work, total_work, "Completed Theme baselines")

    chart_uids = tuple(
        sorted(_core._chart_uid(chart) for chart in charts if _core._chart_uid(chart))
    )
    norm_signature = _core._stable_hash({"chart_uids": chart_uids})
    snapshot = {
        "version": _core.PREDICTION_NORMS_SNAPSHOT_VERSION,
        "snapshot_id": _core._stable_hash(
            {
                "version": _core.PREDICTION_NORMS_SNAPSHOT_VERSION,
                "chart_uids": chart_uids,
                "traits": sorted(trait_baselines),
                "enneagram_definition_signature": enneagram_definition_signature,
                "theme_family_definition_signature": theme_family_definition_signature,
                "created_seed": time.time(),
            }
        ),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "chart_count": len(charts),
        "norm_signature": norm_signature,
        "trait_baselines": trait_baselines,
        "retired_trait_keys": [],
        "dnd_alignment_trait_keys": [
            str(trait.get("name", "") or "") for trait in dnd_alignment_traits
        ],
        "dnd_stat_raw_averages": dnd_stat_raw_averages,
        "enneagram_type_raw_averages": {
            str(enneagram_type): float(value)
            for enneagram_type, value in enneagram_type_raw_averages.items()
        },
        "enneagram_definition_signature": enneagram_definition_signature,
        "theme_family_raw_averages": {
            family_key: float(value)
            for family_key, value in theme_family_raw_averages.items()
        },
        "theme_family_definition_signature": theme_family_definition_signature,
    }

    # A manual rebuild creates/replaces My Database only. The bundled Official
    # catalog and the user's explicit source selection are independent.
    report(
        completed_work,
        total_work,
        "Saving database norms snapshot",
        force_terminal=True,
    )
    _core.save_prediction_norms_snapshot(snapshot, _core.PREDICTION_NORMS_SNAPSHOT_PATH)
    resolved_snapshot = _core.load_prediction_norms_snapshot(
        source=_core.PREDICTION_NORMS_SOURCE_MY_DATABASE
    )
    try:
        setattr(owner, "_prediction_norms_snapshot_cache", resolved_snapshot)
        setattr(
            owner,
            "_prediction_norms_revision",
            int(getattr(owner, "_prediction_norms_revision", 0) or 0) + 1,
        )
    except Exception:
        pass
    completed_work += 1
    report(completed_work, total_work, "Database norms recalculation complete")
    return resolved_snapshot


_core.enneagram_type_snapshot_averages = enneagram_type_snapshot_averages
_core.refresh_prediction_norms_snapshot = refresh_prediction_norms_snapshot

# The Themes UI extension checks this marker so it does not wrap the now-native
# Theme snapshot implementation a second time.
_ephemeraldaddy_theme_norms_installed = True

del _name
