"""Chart View custom trait prediction rendering helpers."""

from __future__ import annotations

import hashlib
import html
import json
import logging
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QLabel, QComboBox

from ephemeraldaddy.analysis.traits import DEFAULT_TRAIT_COLOR, calculate_trait_likelihoods, list_traits, normalize_trait_color
from ephemeraldaddy.core import db
from ephemeraldaddy.core.chart import chart_uses_houses

logger = logging.getLogger(__name__)

TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD = 5.0
TRAIT_DB_NORMS_CACHE_VERSION = 1
TRAIT_DB_NORMS_CACHE_PATH = Path.home() / ".ephemeraldaddy" / "cache" / "trait_db_norms.json"


def _format_signed_percentage(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.1f}%"


def _traits_table_header() -> str:
    return (
        "<tr>"
        "<th style='padding:1px 8px 2px 0; text-align:left; color:#f5f5f5;'>trait</th>"
        "<th style='padding:1px 8px 2px 0; text-align:right; color:#f5f5f5;'>%</th>"
        "<th style='padding:1px 0 2px 0; text-align:right; color:#f5f5f5;'>vs DB avg</th>"
        "</tr>"
    )


def _trait_rank_row(
    name: str,
    percentage: float,
    *,
    color: str,
    db_average: float,
    db_deviation: float,
) -> str:
    safe_name = html.escape(name)
    pct = max(0.0, min(100.0, percentage))
    safe_color = html.escape(normalize_trait_color(color))
    difference_text = html.escape(_format_signed_percentage(db_deviation))
    difference_color = "#d8d8d8"
    if db_deviation > 0:
        difference_color = "#90ee90"
    elif db_deviation < 0:
        difference_color = "#ffb3b3"
    safe_title = html.escape(f"DB average: {max(0.0, min(100.0, db_average)):.1f}%")
    return (
        "<tr>"
        f"<td style='padding:1px 8px 1px 0; white-space:nowrap; color:{safe_color};' title='{safe_title}'>{safe_name}</td>"
        f"<td style='padding:1px 8px 1px 0; text-align:right; color:#d8d8d8;'>{pct:.1f}%</td>"
        f"<td style='padding:1px 0; text-align:right; color:{difference_color};'>{difference_text}</td>"
        "</tr>"
    )


def _trait_table(title: str, rows: list[tuple[str, float, float, float]], color_by_name: dict[str, str]) -> str:
    if rows:
        body = "".join(
            _trait_rank_row(
                name,
                pct,
                color=color_by_name.get(name, DEFAULT_TRAIT_COLOR),
                db_average=db_average,
                db_deviation=db_deviation,
            )
            for name, pct, db_average, db_deviation in rows
        )
    else:
        body = (
            "<tr><td colspan='3' style='padding:3px 0; color:#9a9a9a;'>"
            "No traits meet the 5% deviation threshold."
            "</td></tr>"
        )
    return (
        f"<div style='padding-bottom:3px;'><b>{html.escape(title)}</b></div>"
        "<table cellspacing='0' cellpadding='0' style='width:100%;'>"
        f"{_traits_table_header()}{body}"
        "</table>"
    )


def _stable_json_hash(value: Any) -> str:
    try:
        payload = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    except TypeError:
        payload = repr(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _database_chart_rows(owner: Any) -> list[Any]:
    chart_rows = list(getattr(owner, "_chart_rows", []) or [])
    if chart_rows:
        return chart_rows
    try:
        return list(db.list_charts())
    except Exception as exc:
        logger.warning("Traits panel could not load database chart rows for DB averages: %s", exc, exc_info=True)
        return []


def _database_chart_ids(owner: Any) -> tuple[int, ...]:
    chart_rows = _database_chart_rows(owner)
    normalize_row = getattr(owner, "_normalize_chart_row", None)
    chart_ids: set[int] = set()
    for row in chart_rows:
        normalized = normalize_row(row) if callable(normalize_row) else row
        if normalized is None:
            continue
        try:
            chart_ids.add(int(normalized[0]))
        except (TypeError, ValueError, IndexError):
            continue
    return tuple(sorted(chart_ids))


def _database_chart_uids(owner: Any) -> tuple[str, ...]:
    chart_rows = _database_chart_rows(owner)
    chart_uids: set[str] = set()
    missing_uid_ids: set[int] = set()
    for row in chart_rows:
        try:
            chart_id = int(row[0])
        except (TypeError, ValueError, IndexError):
            continue
        raw_uid = None
        try:
            raw_uid = row[30]
        except (TypeError, IndexError):
            raw_uid = None
        chart_uid = str(raw_uid or "").strip().upper()
        if chart_uid:
            chart_uids.add(chart_uid)
        else:
            missing_uid_ids.add(chart_id)
    if missing_uid_ids:
        try:
            chart_uids.update(
                str(uid).strip().upper()
                for uid in db.get_chart_uid_map(missing_uid_ids).values()
                if str(uid or "").strip()
            )
        except Exception as exc:
            logger.warning("Traits panel could not resolve chart UIDs for norm signature: %s", exc, exc_info=True)
    return tuple(sorted(chart_uids))


def _chart_uid_for_trait_metadata(chart: Any) -> str | None:
    chart_uid = str(getattr(chart, "chart_uid", "") or "").strip()
    return chart_uid or None


def _chart_trait_metadata_signature(chart: Any) -> str:
    try:
        uses_houses = bool(chart_uses_houses(chart))
    except Exception:
        uses_houses = bool(getattr(chart, "use_birth_time_data", False))
    return _stable_json_hash(
        {
            "birth_date": getattr(chart, "birth_date", None),
            "birth_time": getattr(chart, "birth_time", None),
            "dt": getattr(chart, "dt", None),
            "dt_local": getattr(chart, "dt_local", None),
            "birth_place": getattr(chart, "birth_place", None),
            "datetime": getattr(chart, "datetime", None),
            "datetime_iso": getattr(chart, "datetime_iso", None),
            "lat": getattr(chart, "lat", None),
            "lon": getattr(chart, "lon", None),
            "birthtime_unknown": bool(getattr(chart, "birthtime_unknown", False)),
            "retcon_time_used": bool(getattr(chart, "retcon_time_used", False)),
            "retcon_hour": getattr(chart, "retcon_hour", None),
            "retcon_minute": getattr(chart, "retcon_minute", None),
            "chart_uses_houses": uses_houses,
        }
    )


def _trait_norm_cache_key(chart_uids: tuple[str, ...], trait: dict[str, Any]) -> str | None:
    name = str(trait.get("name", "")).strip()
    if not name or bool(trait.get("archived", False)):
        return None
    payload = {
        "version": TRAIT_DB_NORMS_CACHE_VERSION,
        "chart_uids": chart_uids,
        "trait_name": name,
        "trait_color": normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR))),
        "trait_profile": trait.get("profile", {}),
    }
    return _stable_json_hash(payload)


def _load_trait_norm_cache() -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(TRAIT_DB_NORMS_CACHE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning(
            "Traits panel skipped corrupt DB norm cache %s: %s",
            TRAIT_DB_NORMS_CACHE_PATH,
            exc,
            exc_info=True,
        )
        return {}
    if not isinstance(payload, dict) or payload.get("version") != TRAIT_DB_NORMS_CACHE_VERSION:
        logger.warning(
            "Traits panel skipped DB norm cache %s because it has an unsupported format or version.",
            TRAIT_DB_NORMS_CACHE_PATH,
        )
        return {}
    entries = payload.get("entries", {})
    if not isinstance(entries, dict):
        logger.warning(
            "Traits panel skipped DB norm cache entries from %s because entries is not a mapping.",
            TRAIT_DB_NORMS_CACHE_PATH,
        )
        return {}
    return entries


def _save_trait_norm_cache(entries: dict[str, dict[str, Any]]) -> None:
    try:
        TRAIT_DB_NORMS_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temp_path = TRAIT_DB_NORMS_CACHE_PATH.with_suffix(f"{TRAIT_DB_NORMS_CACHE_PATH.suffix}.tmp")
        temp_path.write_text(
            json.dumps(
                {"version": TRAIT_DB_NORMS_CACHE_VERSION, "entries": entries},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
        temp_path.replace(TRAIT_DB_NORMS_CACHE_PATH)
    except Exception:
        return


def clear_trait_norm_cache(trait_names: set[str] | None = None) -> None:
    """Clear persisted DB norm cache entries for selected traits or all traits."""
    if trait_names is None:
        TRAIT_DB_NORMS_CACHE_PATH.unlink(missing_ok=True)
        return
    normalized_names = {name.casefold() for name in trait_names}
    entries = _load_trait_norm_cache()
    for key, entry in list(entries.items()):
        if str(entry.get("trait_name", "")).casefold() in normalized_names:
            entries.pop(key, None)
    _save_trait_norm_cache(entries)


def _calculate_database_trait_averages_direct(
    owner: Any,
    chart_ids: tuple[int, ...],
    traits: list[dict[str, Any]],
) -> dict[str, float]:
    """Calculate DB trait averages without relying on Database Analytics caches."""
    if not chart_ids or not traits:
        return {}
    get_chart = getattr(owner, "_get_chart_for_filter", None)
    is_placeholder = getattr(owner, "_is_placeholder_chart", None)
    chart_count = 0
    totals: dict[str, float] = {str(trait.get("name", "")).strip(): 0.0 for trait in traits}
    totals = {name: total for name, total in totals.items() if name}
    if not totals:
        return {}
    for chart_id in chart_ids:
        try:
            chart = get_chart(int(chart_id)) if callable(get_chart) else db.load_chart(int(chart_id))
        except Exception as exc:
            logger.warning("Traits panel could not load chart %s while calculating DB trait averages: %s", chart_id, exc)
            continue
        if chart is None:
            continue
        if callable(is_placeholder) and is_placeholder(chart):
            continue
        try:
            likelihoods = calculate_trait_likelihoods(chart, traits)
        except Exception as exc:
            logger.warning(
                "Traits panel could not score chart %s while calculating DB trait averages: %s",
                chart_id,
                exc,
                exc_info=True,
            )
            continue
        chart_count += 1
        for name in totals:
            try:
                totals[name] += float(likelihoods.get(name, 0.0))
            except (TypeError, ValueError):
                continue
    if not chart_count:
        return {}
    return {name: total / float(chart_count) for name, total in totals.items()}


def _database_trait_averages(owner: Any, traits: list[dict[str, Any]]) -> dict[str, float]:
    chart_ids = _database_chart_ids(owner)
    chart_uids = _database_chart_uids(owner)
    collect = getattr(owner, "_collect_traits_distribution_analytics", None)
    signature_builder = getattr(owner, "_traits_distribution_signature", None)
    if not chart_ids or not chart_uids:
        return {}
    if not callable(collect) or not callable(signature_builder):
        return _calculate_database_trait_averages_direct(owner, chart_ids, traits)
    averages: dict[str, float] = {}
    cache_entries = _load_trait_norm_cache()
    missing_traits: list[dict[str, Any]] = []
    for trait in traits:
        name = str(trait.get("name", "")).strip()
        cache_key = _trait_norm_cache_key(chart_uids, trait)
        cached = cache_entries.get(cache_key or "")
        if isinstance(cached, dict) and cached.get("trait_name") == name:
            try:
                averages[name] = float(cached["db_average"])
                continue
            except (KeyError, TypeError, ValueError):
                pass
        missing_traits.append(trait)
    if not missing_traits:
        return averages

    try:
        analytics = collect(chart_ids, trait_items=missing_traits, trait_signature=signature_builder(missing_traits))
    except Exception as exc:
        logger.warning("Traits panel could not collect Database Analytics trait averages: %s", exc, exc_info=True)
        direct_averages = _calculate_database_trait_averages_direct(owner, chart_ids, missing_traits)
        averages.update(direct_averages)
        return averages
    chart_count = max(0, int(analytics.get("chart_count", 0)))
    if not chart_count:
        direct_averages = _calculate_database_trait_averages_direct(owner, chart_ids, missing_traits)
        averages.update(direct_averages)
        return averages
    totals = analytics.get("totals", {})
    for trait_name in analytics.get("trait_names", []):
        name = str(trait_name)
        db_average = (float(totals.get(name, 0.0)) / float(chart_count)) * 100.0
        averages[name] = db_average
        trait_item = next((trait for trait in missing_traits if str(trait.get("name", "")).strip() == name), None)
        cache_key = _trait_norm_cache_key(chart_uids, trait_item or {})
        if cache_key:
            cache_entries[cache_key] = {
                "trait_name": name,
                "db_average": db_average,
                "chart_count": chart_count,
            }
    _save_trait_norm_cache(cache_entries)
    return averages


def warm_trait_database_norms(owner: Any, trait_names: set[str] | None = None) -> dict[str, float]:
    """Precompute and persist DB norms for selected active traits."""
    traits = list_traits(active_only=True)
    if trait_names is not None:
        normalized_names = {name.casefold() for name in trait_names}
        traits = [trait for trait in traits if str(trait.get("name", "")).casefold() in normalized_names]
    return _database_trait_averages(owner, traits)


def trait_metadata_for_chart(owner: Any, chart: Any) -> dict[str, Any]:
    """Return and attach derived trait metadata for a chart."""
    traits = list_traits(active_only=True)
    if chart is None or getattr(owner, "_is_placeholder_chart", lambda _chart: False)(chart) or not traits:
        metadata = {"above": set(), "below": set(), "deviations": {}, "likelihoods": {}}
        setattr(chart, "predicted_traits_above_avg", set())
        setattr(chart, "predicted_traits_below_avg", set())
        setattr(chart, "predicted_trait_deviations", {})
        return metadata

    trait_signature = _stable_json_hash(
        {
            "version": TRAIT_DB_NORMS_CACHE_VERSION,
            "traits": [
                {
                    "name": trait.get("name", ""),
                    "color": normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR))),
                    "profile": trait.get("profile", {}),
                }
                for trait in traits
            ],
        }
    )
    norm_signature = _stable_json_hash(_database_chart_uids(owner))
    chart_signature = _chart_trait_metadata_signature(chart)
    signature = (TRAIT_DB_NORMS_CACHE_VERSION, trait_signature, norm_signature, chart_signature)
    cached = getattr(chart, "_trait_prediction_metadata_cache", None)
    if isinstance(cached, dict) and cached.get("signature") == signature:
        return dict(cached.get("metadata", {}))

    chart_uid = _chart_uid_for_trait_metadata(chart)
    active_trait_names = {str(trait.get("name", "")).strip() for trait in traits if str(trait.get("name", "")).strip()}
    if chart_uid is not None:
        try:
            rows = db.get_chart_trait_metadata(chart_uid)
        except Exception as exc:
            logger.warning(
                "Traits panel skipped cached DB trait metadata for chart UID %s: %s",
                chart_uid,
                exc,
                exc_info=True,
            )
            rows = []
        if rows and {str(row.get("trait_name", "")) for row in rows} == active_trait_names and all(
            str(row.get("trait_signature", "")) == trait_signature
            and str(row.get("norm_signature", "")) == norm_signature
            and str(row.get("chart_signature", "")) == chart_signature
            for row in rows
        ):
            above = {str(row["trait_name"]) for row in rows if row.get("direction") == "above"}
            below = {str(row["trait_name"]) for row in rows if row.get("direction") == "below"}
            deviations = {str(row["trait_name"]): float(row.get("deviation", 0.0)) for row in rows}
            likelihoods = {str(row["trait_name"]): float(row.get("likelihood", 0.0)) for row in rows}
            database_averages = {str(row["trait_name"]): float(row.get("db_average", 0.0)) for row in rows}
            metadata = {
                "above": above,
                "below": below,
                "deviations": deviations,
                "likelihoods": likelihoods,
                "database_averages": database_averages,
            }
            setattr(chart, "predicted_traits_above_avg", set(above))
            setattr(chart, "predicted_traits_below_avg", set(below))
            setattr(chart, "predicted_trait_deviations", dict(deviations))
            setattr(chart, "_trait_prediction_metadata_cache", {"signature": signature, "metadata": metadata})
            return metadata

    likelihoods = calculate_trait_likelihoods(chart, traits)
    database_averages = _database_trait_averages(owner, traits)
    deviations = {
        name: float(pct) - float(database_averages[name])
        for name, pct in likelihoods.items()
        if name in database_averages
    }
    threshold = TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD
    above = {name for name, deviation in deviations.items() if deviation >= threshold}
    below = {name for name, deviation in deviations.items() if deviation <= -threshold}
    metadata = {
        "above": above,
        "below": below,
        "deviations": deviations,
        "likelihoods": likelihoods,
        "database_averages": database_averages,
    }
    setattr(chart, "predicted_traits_above_avg", set(above))
    setattr(chart, "predicted_traits_below_avg", set(below))
    setattr(chart, "predicted_trait_deviations", dict(deviations))
    setattr(chart, "_trait_prediction_metadata_cache", {"signature": signature, "metadata": metadata})
    if chart_uid is not None:
        try:
            db.upsert_chart_trait_metadata(
                chart_uid,
                [
                    {
                        "trait_name": name,
                        "direction": "above" if name in above else "below" if name in below else "neutral",
                        "likelihood": likelihoods.get(name, 0.0),
                        "db_average": database_averages.get(name, 0.0),
                        "deviation": deviations.get(name, 0.0),
                    }
                    for name in active_trait_names
                ],
                trait_signature=trait_signature,
                norm_signature=norm_signature,
                chart_signature=chart_signature,
            )
        except Exception as exc:
            logger.warning(
                "Traits panel could not update cached DB trait metadata for chart UID %s: %s",
                chart_uid,
                exc,
                exc_info=True,
            )
    return metadata


def render_traits_predictions(owner: Any, chart: Any | None) -> None:
    """Render uploaded custom trait scores into Chart View's Predictions panel."""
    label = getattr(owner, "traits_prediction_label", None)
    if not isinstance(label, QLabel):
        return
    traits = list_traits(active_only=True)
    if not traits:
        if list_traits():
            label.setText("No active traits. Reactivate traits in Settings > Traits to include them in Predictions.")
        else:
            label.setText("No traits uploaded. Add traits in Settings > Traits.")
        return
    if chart is None or owner._is_placeholder_chart(chart):
        label.setText("Trait predictions unavailable for this chart.")
        return
    try:
        metadata = trait_metadata_for_chart(owner, chart)
        likelihoods = dict(metadata.get("likelihoods", {}))
        database_averages = dict(metadata.get("database_averages", {}))
        db_deviations = dict(metadata.get("deviations", {}))
    except Exception as exc:
        label.setText(f"Trait predictions unavailable: {html.escape(str(exc))}")
        return
    color_by_name = {
        str(trait.get("name", "")): normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR)))
        for trait in traits
    }
    if not likelihoods:
        label.setText("No scorable traits uploaded.")
        return
    if not database_averages:
        label.setText("Trait predictions unavailable until database trait averages can be calculated.")
        return
    threshold = TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD
    above_avg_traits = sorted(
        (
            (name, float(likelihoods[name]), float(database_averages[name]), float(db_deviation))
            for name, db_deviation in db_deviations.items()
            if db_deviation >= threshold
        ),
        key=lambda item: item[3],
        reverse=True,
    )
    below_avg_traits = sorted(
        (
            (name, float(likelihoods[name]), float(database_averages[name]), float(db_deviation))
            for name, db_deviation in db_deviations.items()
            if db_deviation <= -threshold
        ),
        key=lambda item: item[3],
    )
    intro = (
        "<div style='color:#d8d8d8; padding-bottom:4px;'>"
        "Traits are assigned by deviation from the active database average. "
        f"Above-average traits are at least {threshold:.0f}% higher than DB average; "
        f"below-average traits are at least {threshold:.0f}% lower than DB average."
        "</div>"
    )
    owner._traits_prediction_above_avg_html = "".join(
        [_trait_table("Above avg traits", above_avg_traits, color_by_name)] #removed "intro, " and ", footer"  from "intro, _trait_table..., footer"
    )
    owner._traits_prediction_below_avg_html = "".join(
        [_trait_table("Below avg traits", below_avg_traits, color_by_name)] #removed "intro, " and ", footer" from "intro, _trait_table..., footer"
    )
    combo = getattr(owner, "traits_prediction_mode_combo", None)
    mode = combo.currentData() if isinstance(combo, QComboBox) else "above"
    label.setText(
        owner._traits_prediction_below_avg_html
        if mode == "below"
        else owner._traits_prediction_above_avg_html
    )
