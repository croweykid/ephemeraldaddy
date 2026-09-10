# LEGACY CHART ID WARNING: any chart_id reference in this file is transitional compatibility only; new code must use chart_uid/Chart UID and must not introduce new chart ID reliance.
"""Static Predictions norm snapshot facade.

The implementation core remains stable while this facade owns population sections
that must be regenerated only by the explicit Recalculate DB Norms action.
"""

from __future__ import annotations

import math
import time
from typing import Any, Mapping

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
    owner: Any, *, user_initiated: bool = False
) -> dict[str, Any]:
    """Rebuild all snapshot-backed Predictions population norms on explicit request.

    Deliberately included here: custom Traits, Fantasy RPG alignment traits,
    Fantasy RPG Stat Block raw averages, and Enneagram type averages.
    Sign Dominance, Fantasy RPG Species/Class, and OCEAN are intentionally not
    part of this snapshot.
    """
    if not user_initiated:
        raise _core.ExplicitNormRecalculationRequired(
            "Whole-database prediction norms can only be rebuilt by the explicit "
            "Recalculate DB Norms action."
        )

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
    for source, group_traits in trait_groups:
        if not group_traits:
            continue
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

    dnd_stat_totals = {key: 0.0 for key in _core.DND_STAT_KEYS}
    dnd_stat_count = 0
    for chart in charts:
        raw_scores = _core.calculate_weighted_criteria_scores(
            chart,
            predictors=_core.DND_STAT_PREDICTORS,
        )
        for key in _core.DND_STAT_KEYS:
            dnd_stat_totals[key] += float(raw_scores.get(key, 0.0))
        dnd_stat_count += 1
    dnd_stat_raw_averages = (
        {
            key: dnd_stat_totals[key] / float(dnd_stat_count)
            for key in _core.DND_STAT_KEYS
        }
        if dnd_stat_count
        else {}
    )

    enneagram_type_raw_averages, enneagram_definition_signature = (
        _calculate_enneagram_snapshot_section(charts)
    )

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
    }

    # A manual rebuild creates/replaces My Database only. The bundled Official
    # catalog and the user's explicit source selection are independent.
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
    return resolved_snapshot


_core.enneagram_type_snapshot_averages = enneagram_type_snapshot_averages
_core.refresh_prediction_norms_snapshot = refresh_prediction_norms_snapshot

del _name
