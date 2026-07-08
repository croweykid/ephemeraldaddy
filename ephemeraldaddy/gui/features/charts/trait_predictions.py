"""Chart View custom trait prediction rendering helpers."""

from __future__ import annotations

import hashlib
import html
import json
import logging
import sys
import urllib.parse
from datetime import datetime
from typing import Any

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import QLabel, QComboBox, QWidget

from ephemeraldaddy.analysis.traits import (
    DEFAULT_TRAIT_COLOR,
    calculate_trait_likelihoods,
    list_traits,
    normalize_trait_color,
    trait_sample_total,
    trait_uid_for_profile,
)
from ephemeraldaddy.core import db
from ephemeraldaddy.core.chart import chart_uses_houses
from ephemeraldaddy.gui.style import apply_chart_info_link_cursor, set_chart_info_html

logger = logging.getLogger(__name__)

TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD = 5.0
TRAIT_DB_NORMS_CACHE_VERSION = 1
DATABASE_NORMS_CACHE_FILENAME = ".database_norms_cache.json"
TRAIT_DB_NORMS_CACHE_PATH = db.DB_DIR / DATABASE_NORMS_CACHE_FILENAME
TRAIT_DB_NORMS_MAX_STALE_RATIO = 0.10


def _predictions_debug_enabled(owner: Any) -> bool:
    return bool(getattr(owner, "_predictions_thread_debug", False))


def _predictions_debug(owner: Any, message: str, *args: object) -> None:
    """Emit terminal Predictions step logs when Settings > Dev Tools enables them."""
    if not _predictions_debug_enabled(owner):
        return
    rendered = message % args if args else message
    timestamp = datetime.now().isoformat(timespec="milliseconds")
    logger.info("[predictions-thread-debug][traits] %s", rendered)
    print(f"[predictions-thread-debug][{timestamp}][traits] {rendered}", file=sys.stderr, flush=True)


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
    safe_href = html.escape(f"trait:{urllib.parse.quote(name, safe='')}", quote=True)
    difference_text = html.escape(_format_signed_percentage(db_deviation))
    difference_color = "#d8d8d8"
    if db_deviation > 0:
        difference_color = "#90ee90"
    elif db_deviation < 0:
        difference_color = "#ffb3b3"
    safe_title = html.escape(f"DB average: {max(0.0, min(100.0, db_average)):.1f}%")
    return (
        "<tr>"
        f"<td style='padding:1px 8px 1px 0; white-space:nowrap; color:{safe_color};' title='{safe_title}'>"
        f"<a href='{safe_href}' style='color:{safe_color}; text-decoration:none;'>{safe_name}</a>"
        "</td>"
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


def _trait_sample_count(trait: dict[str, Any]) -> int:
    samples = trait.get("samples")
    if samples is None and isinstance(trait.get("profile"), dict):
        samples = trait["profile"].get("samples")
    return trait_sample_total(samples, trait_name=str(trait.get("name", "")))


def _trait_info_html(trait: dict[str, Any]) -> str:
    name = str(trait.get("name", "")).strip() or "Trait"
    color = normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR)))
    description = str(trait.get("description", "")).strip() or "no description provided"
    sample_count = _trait_sample_count(trait)
    return (
        f"<div style='font-size:18px; font-weight:700; color:{html.escape(color)};'>"
        f"{html.escape(name)}</div>"
        "<div style='height:6px;'></div>"
        "<div style='font-size:12px; color:#f5f5f5; font-style:italic; line-height:1.35;'>"
        f"{html.escape(description).replace(chr(10), '<br>')}"
        "</div>"
        "<div style='height:8px;'></div>"
        "<div style='font-size:9px; color:#b8b8b8; font-variant:small-caps; letter-spacing:0.8px;'>"
        f"based on aggregated data from {sample_count}"
        "</div>"
    )


def _show_trait_chart_info(owner: Any, trait_name: str) -> None:
    trait_lookup = getattr(owner, "_traits_prediction_trait_lookup", {}) or {}
    trait = trait_lookup.get(str(trait_name or "").casefold())
    if trait is None:
        return
    set_mode = getattr(owner, "_set_chart_info_panel_mode", None)
    if callable(set_mode):
        set_mode("chart_info")
    output = getattr(owner, "chart_info_output", None)
    if isinstance(output, QWidget) or hasattr(output, "setHtml") or hasattr(output, "setPlainText"):
        set_chart_info_html(output, _trait_info_html(trait))


def _on_trait_prediction_link_activated(owner: Any, target: str) -> None:
    parts = str(target or "").split(":", 1)
    if len(parts) != 2 or parts[0] != "trait":
        return
    _show_trait_chart_info(owner, urllib.parse.unquote(parts[1]))


def _configure_traits_prediction_label(owner: Any, label: QLabel) -> None:
    label.setOpenExternalLinks(False)
    apply_chart_info_link_cursor(label)
    if getattr(label, "_ephemeraldaddy_trait_links_connected", False):
        return
    label.linkActivated.connect(lambda target: _on_trait_prediction_link_activated(owner, target))
    label._ephemeraldaddy_trait_links_connected = True


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
            if len(row) > 30:
                raw_uid = row[30]
        except TypeError:
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


def _database_norm_refresh_threshold(chart_count: int) -> int:
    """Return how many birth-data cohort changes justify refreshing DB norms."""
    count = max(0, int(chart_count))
    if count < 10:
        return 1
    return max(1, int(count * TRAIT_DB_NORMS_MAX_STALE_RATIO))


def _database_norm_chart_token_source(owner: Any) -> tuple[tuple[str, str], ...]:
    """Return stable tokens for the non-placeholder charts that define DB norms."""
    rows_provider = getattr(owner, "_prediction_norm_rows", None)
    normalize_row = getattr(owner, "_normalize_chart_row", None)
    rows: list[Any] = []
    if callable(rows_provider):
        try:
            rows = list(rows_provider())
        except Exception:
            rows = []
    if not rows:
        return tuple((uid, "") for uid in _database_chart_uids(owner))

    normalized_rows_by_id: dict[int, Any] = {}
    for row in rows:
        normalized = normalize_row(row) if callable(normalize_row) else row
        if normalized is None:
            continue
        try:
            chart_id = int(normalized[0])
        except Exception:
            continue
        normalized_rows_by_id[chart_id] = normalized

    tokens: list[tuple[str, str]] = []
    uid_map: dict[int, str] = {}
    missing_uid_ids: list[int] = []
    for chart_id, normalized in normalized_rows_by_id.items():
        uid = ""
        if isinstance(normalized, (list, tuple)) and len(normalized) > 30 and normalized[30]:
            uid = str(normalized[30]).strip().upper()
        if not uid:
            missing_uid_ids.append(chart_id)
            continue
        token_payload = {
            "uid": uid,
            "row": repr(normalized),
        }
        tokens.append((uid, _stable_json_hash(token_payload)))

    if missing_uid_ids:
        try:
            uid_map = db.get_chart_uid_map(missing_uid_ids)
        except Exception:
            uid_map = {}
        for chart_id in missing_uid_ids:
            normalized = normalized_rows_by_id.get(chart_id)
            uid = str(uid_map.get(chart_id, "")).strip().upper()
            if not uid:
                continue
            token_payload = {
                "uid": uid,
                "row": repr(normalized),
            }
            tokens.append((uid, _stable_json_hash(token_payload)))
    return tuple(sorted(tokens))


def _database_norm_state(owner: Any) -> dict[str, Any]:
    tokens = _database_norm_chart_token_source(owner)
    return {
        "version": TRAIT_DB_NORMS_CACHE_VERSION,
        "chart_count": len(tokens),
        "chart_tokens": {uid: token for uid, token in tokens},
    }


def _database_norm_state_change_count(saved_state: dict[str, Any], current_state: dict[str, Any]) -> int:
    saved_tokens = saved_state.get("chart_tokens", {}) if isinstance(saved_state, dict) else {}
    current_tokens = current_state.get("chart_tokens", {}) if isinstance(current_state, dict) else {}
    if not isinstance(saved_tokens, dict) or not isinstance(current_tokens, dict):
        return max(
            int(saved_state.get("chart_count", 0) or 0) if isinstance(saved_state, dict) else 0,
            int(current_state.get("chart_count", 0) or 0) if isinstance(current_state, dict) else 0,
        )
    all_uids = set(saved_tokens) | set(current_tokens)
    return sum(1 for uid in all_uids if saved_tokens.get(uid) != current_tokens.get(uid))


def _database_norm_state_is_fresh(saved_state: dict[str, Any], current_state: dict[str, Any]) -> bool:
    saved_count = int(saved_state.get("chart_count", 0) or 0) if isinstance(saved_state, dict) else 0
    current_count = int(current_state.get("chart_count", 0) or 0) if isinstance(current_state, dict) else 0
    threshold = _database_norm_refresh_threshold(max(saved_count, current_count))
    return _database_norm_state_change_count(saved_state, current_state) < threshold


def _database_norm_signature_from_state(state: dict[str, Any]) -> str:
    """Return the DB-norm generation used by per-chart metadata."""
    return _stable_json_hash(
        {
            "version": TRAIT_DB_NORMS_CACHE_VERSION,
            "scope": "database_statistics_threshold",
            "chart_count": int(state.get("chart_count", 0) or 0),
            "chart_tokens": state.get("chart_tokens", {}),
        }
    )


def _database_norm_signature_for_traits(owner: Any, traits: list[dict[str, Any]]) -> str:
    """Return the active DB norm signature, preserving it until the refresh threshold is crossed."""
    current_norm_state = _database_norm_state(owner)
    cache_entries = _load_trait_norm_cache()
    fresh_signatures: set[str] = set()
    stale_signatures: set[str] = set()
    chart_uids = _database_chart_uids(owner)
    for trait in traits:
        cache_key = _trait_norm_cache_key(chart_uids, trait)
        cached = cache_entries.get(cache_key or "")
        cached_state = cached.get("norm_state", {}) if isinstance(cached, dict) else {}
        cached_signature = str(cached.get("norm_signature", "")).strip() if isinstance(cached, dict) else ""
        if not cached_signature:
            continue
        if _database_norm_state_is_fresh(cached_state, current_norm_state):
            fresh_signatures.add(cached_signature)
        else:
            stale_signatures.add(cached_signature)
    if fresh_signatures:
        return sorted(fresh_signatures)[0]
    if stale_signatures:
        _predictions_debug(
            owner,
            "Trait DB norm signature using stale persistent cache while background refresh can update it signatures=%s",
            sorted(stale_signatures),
        )
        return sorted(stale_signatures)[0]
    return _database_norm_signature_from_state(current_norm_state)


def _trait_definition_signature(trait: dict[str, Any]) -> str:
    trait_uid = str(trait.get("uid") or trait.get("trait_uid") or "").strip()
    scoring_profile = _trait_analytical_profile(trait.get("profile", {}), strip_uids=True)
    return _stable_json_hash(
        {
            "version": TRAIT_DB_NORMS_CACHE_VERSION,
            "uid": trait_uid,
            "profile": scoring_profile,
        }
    )


def _trait_uid_for_item(trait: dict[str, Any]) -> str:
    uid = str(trait.get("uid") or trait.get("trait_uid") or "").strip()
    if uid:
        return uid
    name = str(trait.get("name", "")).strip()
    return trait_uid_for_profile(name, trait.get("profile", {}) if isinstance(trait.get("profile"), dict) else {})


def _trait_analytical_profile(profile: Any, *, strip_uids: bool = False) -> dict[str, Any]:
    """Return only scoring-relevant trait factors, excluding display-only metadata."""
    if not isinstance(profile, dict):
        return {}
    excluded = {"name", "color", "description", "motivation", "quotes", "archived", "samples"}
    if strip_uids:
        excluded.update({"uid", "trait_uid"})
    return {str(key): value for key, value in profile.items() if str(key) not in excluded}


def _trait_signature_payload(traits: list[dict[str, Any]], *, strip_uids: bool = False) -> dict[str, Any]:
    trait_payloads: list[dict[str, Any]] = []
    for trait in traits:
        profile = _trait_analytical_profile(trait.get("profile", {}), strip_uids=strip_uids)
        trait_payloads.append(
            {
                "uid": "" if strip_uids else str(trait.get("uid") or trait.get("trait_uid") or "").strip(),
                "profile": profile,
            }
        )
    return {"version": TRAIT_DB_NORMS_CACHE_VERSION, "traits": trait_payloads}


def _trait_norm_cache_key(chart_uids: tuple[str, ...], trait: dict[str, Any]) -> str | None:
    name = str(trait.get("name", "")).strip()
    if not name or bool(trait.get("archived", False)):
        return None
    payload = {
        "version": TRAIT_DB_NORMS_CACHE_VERSION,
        "cache_scope": "appwide_database_norms",
        "refresh_policy": "database_statistics_threshold",
        "norm_kind": "trait_database_average",
        "trait_uid": str(trait.get("uid") or trait.get("trait_uid") or "").strip(),
        "analytical_profile": _trait_analytical_profile(trait.get("profile", {})),
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
    _predictions_debug(owner, "Trait DB averages requested traits=%s", len(traits))
    chart_ids = _database_chart_ids(owner)
    chart_uids = _database_chart_uids(owner)
    current_norm_state = _database_norm_state(owner)
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
        cached_state = cached.get("norm_state", {}) if isinstance(cached, dict) else {}
        if isinstance(cached, dict) and cached.get("trait_name") == name:
            try:
                averages[name] = float(cached["db_average"])
                if not _database_norm_state_is_fresh(cached_state, current_norm_state):
                    _predictions_debug(
                        owner,
                        "Trait DB average using stale persistent norm trait=%s cached_chart_count=%s current_chart_count=%s",
                        name,
                        cached.get("chart_count"),
                        current_norm_state.get("chart_count"),
                    )
                continue
            except (KeyError, TypeError, ValueError):
                pass
        missing_traits.append(trait)
    if not missing_traits:
        _predictions_debug(owner, "Trait DB averages served entirely from persistent cache traits=%s", len(averages))
        return averages

    try:
        _predictions_debug(owner, "Trait DB averages collecting missing traits=%s chart_ids=%s", len(missing_traits), len(chart_ids))
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
                "norm_state": current_norm_state,
                "norm_signature": _database_norm_signature_from_state(current_norm_state),
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
    _predictions_debug(owner, "Trait metadata start chart=%s", getattr(chart, "name", getattr(chart, "chart_uid", "unknown")))
    traits = list_traits(active_only=True)
    if chart is None or getattr(owner, "_is_placeholder_chart", lambda _chart: False)(chart) or not traits:
        metadata = {"above": set(), "below": set(), "deviations": {}, "likelihoods": {}}
        setattr(chart, "predicted_traits_above_avg", set())
        setattr(chart, "predicted_traits_below_avg", set())
        setattr(chart, "predicted_trait_deviations", {})
        return metadata

    trait_signature = _stable_json_hash(_trait_signature_payload(traits))
    legacy_trait_signature = _stable_json_hash(_trait_signature_payload(traits, strip_uids=True))
    norm_signature = _database_norm_signature_for_traits(owner, traits)
    chart_signature = _chart_trait_metadata_signature(chart)
    signature = (TRAIT_DB_NORMS_CACHE_VERSION, trait_signature, norm_signature, chart_signature)
    cached = getattr(chart, "_trait_prediction_metadata_cache", None)
    if isinstance(cached, dict) and cached.get("signature") == signature:
        _predictions_debug(owner, "Trait metadata memory cache hit chart=%s", getattr(chart, "name", getattr(chart, "chart_uid", "unknown")))
        return dict(cached.get("metadata", {}))

    chart_uid = _chart_uid_for_trait_metadata(chart)
    traits_by_name = {str(trait.get("name", "")).strip(): trait for trait in traits if str(trait.get("name", "")).strip()}
    trait_uids_by_name = {name: _trait_uid_for_item(trait) for name, trait in traits_by_name.items()}
    traits_by_uid = {uid: trait for name, trait in traits_by_name.items() if (uid := trait_uids_by_name.get(name))}
    names_by_uid = {uid: name for name, uid in trait_uids_by_name.items() if uid}
    active_trait_names = set(traits_by_name)
    cached_rows_by_name: dict[str, dict[str, Any]] = {}
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
        for row in rows:
            row_uid = str(row.get("trait_uid", "") or "").strip()
            name = names_by_uid.get(row_uid) if row_uid else str(row.get("trait_name", "")).strip()
            trait = traits_by_uid.get(row_uid) if row_uid else traits_by_name.get(name)
            if trait is None:
                continue
            row_trait_signature = str(row.get("trait_signature", ""))
            valid_trait_signature = row_trait_signature in {
                trait_signature,
                legacy_trait_signature,
                _trait_definition_signature(trait),
            }
            if (
                valid_trait_signature
                and str(row.get("norm_signature", "")) == norm_signature
                and str(row.get("chart_signature", "")) == chart_signature
            ):
                cached_rows_by_name[name] = row
        if active_trait_names and set(cached_rows_by_name) == active_trait_names:
            _predictions_debug(owner, "Trait metadata DB row cache hit chart_uid=%s traits=%s", chart_uid, len(active_trait_names))
            above = {name for name, row in cached_rows_by_name.items() if row.get("direction") == "above"}
            below = {name for name, row in cached_rows_by_name.items() if row.get("direction") == "below"}
            deviations = {name: float(row.get("deviation", 0.0)) for name, row in cached_rows_by_name.items()}
            likelihoods = {name: float(row.get("likelihood", 0.0)) for name, row in cached_rows_by_name.items()}
            database_averages = {name: float(row.get("db_average", 0.0)) for name, row in cached_rows_by_name.items()}
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

    cached_likelihoods = {name: float(row.get("likelihood", 0.0)) for name, row in cached_rows_by_name.items()}
    cached_database_averages = {name: float(row.get("db_average", 0.0)) for name, row in cached_rows_by_name.items()}
    missing_traits = [trait for name, trait in traits_by_name.items() if name not in cached_rows_by_name]
    likelihoods = dict(cached_likelihoods)
    if missing_traits:
        _predictions_debug(owner, "Trait metadata scoring missing chart traits=%s", len(missing_traits))
        likelihoods.update(calculate_trait_likelihoods(chart, missing_traits))
    database_averages = dict(cached_database_averages)
    missing_average_traits = [trait for name, trait in traits_by_name.items() if name not in database_averages]
    if missing_average_traits:
        _predictions_debug(owner, "Trait metadata resolving DB averages missing_traits=%s", len(missing_average_traits))
        database_averages.update(_database_trait_averages(owner, missing_average_traits))
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
                        "trait_uid": trait_uids_by_name.get(name, ""),
                        "trait_signature": _trait_definition_signature(traits_by_name[name]),
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


def _trait_predictions_cache_key(
    owner: Any,
    chart: Any | None,
    traits: list[dict[str, Any]],
) -> str | None:
    if chart is None:
        return None
    chart_uid = str(getattr(chart, "chart_uid", "") or "").strip().upper()
    chart_scope = f"uid:{chart_uid}" if chart_uid else "draft"
    trait_signature = _stable_json_hash(_trait_signature_payload(traits))
    try:
        norm_signature = _database_norm_signature_for_traits(owner, traits)
    except Exception as exc:
        logger.warning(
            "Traits panel could not build DB norm signature for view cache: %s",
            exc,
            exc_info=True,
        )
        norm_signature = "norm:unavailable"
    return _stable_json_hash(
        {
            "version": TRAIT_DB_NORMS_CACHE_VERSION,
            "chart_scope": chart_scope,
            "chart_signature": _chart_trait_metadata_signature(chart),
            "trait_signature": trait_signature,
            "norm_signature": norm_signature,
        }
    )


def _trait_predictions_refresh_message(updated_at: str | None) -> str:
    timestamp = html.escape(updated_at or "never")
    return (
        "<div style='color:#70d878; font-style:italic; padding-bottom:5px; text-align:center;'>"
        f"Predictions panel is refreshing. Current results last updated: {timestamp} ♻️"
        "</div>"
    )


def _current_traits_prediction_html(owner: Any) -> str:
    combo = getattr(owner, "traits_prediction_mode_combo", None)
    mode = combo.currentData() if isinstance(combo, QComboBox) else "above"
    return getattr(
        owner,
        "_traits_prediction_below_avg_html" if mode == "below" else "_traits_prediction_above_avg_html",
        "",
    )


def _set_traits_prediction_label_for_mode(owner: Any) -> None:
    label = getattr(owner, "traits_prediction_label", None)
    if isinstance(label, QLabel):
        label.setText(_current_traits_prediction_html(owner) or "Trait predictions unavailable for this chart.")


def _trait_predictions_html_from_metadata(
    traits: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> tuple[str, str]:
    likelihoods = dict(metadata.get("likelihoods", {}))
    database_averages = dict(metadata.get("database_averages", {}))
    db_deviations = dict(metadata.get("deviations", {}))
    if not likelihoods:
        message = "No scorable traits uploaded."
        return message, message
    if not database_averages:
        message = "Trait predictions unavailable until database trait averages can be calculated."
        return message, message
    color_by_name = {
        str(trait.get("name", "")): normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR)))
        for trait in traits
    }
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
    return (
        _trait_table("Above avg traits", above_avg_traits, color_by_name),
        _trait_table("Below avg traits", below_avg_traits, color_by_name),
    )


class _TraitPredictionsRefreshWorker(QObject):
    """Calculate trait prediction HTML away from the Qt GUI thread."""

    finished = Signal(object, object, object)
    failed = Signal(object, str)

    def __init__(self, owner: Any, chart: Any, traits: list[dict[str, Any]], token: object) -> None:
        super().__init__()
        self._owner = owner
        self._chart = chart
        self._traits = traits
        self._token = token

    @Slot()
    def run(self) -> None:
        try:
            _predictions_debug(self._owner, "Trait refresh worker start token=%s", id(self._token))
            metadata = trait_metadata_for_chart(self._owner, self._chart)
            above_html, below_html = _trait_predictions_html_from_metadata(self._traits, metadata)
        except Exception as exc:
            logger.warning("Traits panel background refresh failed: %s", exc, exc_info=True)
            self.failed.emit(self._token, str(exc))
            return
        _predictions_debug(self._owner, "Trait refresh worker finished token=%s", id(self._token))
        self.finished.emit(self._token, above_html, below_html)


class _TraitPredictionsRefreshReceiver(QObject):
    """Receive worker results on the GUI thread before touching widgets."""

    def __init__(self, owner: Any, cache_key: str, token: object) -> None:
        parent = owner if isinstance(owner, QWidget) else None
        super().__init__(parent)
        self._owner = owner
        self._cache_key = cache_key
        self._token = token
        self._thread: QThread | None = None
        self._worker: QObject | None = None

    def set_job(self, thread: QThread, worker: QObject) -> None:
        self._thread = thread
        self._worker = worker

    @Slot(object, object, object)
    def handle_finished(self, finished_token: object, above_html: object, below_html: object) -> None:
        if finished_token is not self._token:
            return
        if getattr(self._owner, "_traits_prediction_render_token", None) is not finished_token:
            return
        updated_at = datetime.now().isoformat(timespec="seconds")
        _cache_traits_prediction_view(
            self._owner,
            self._cache_key,
            str(above_html),
            str(below_html),
            updated_at,
        )
        _apply_traits_prediction_view(self._owner, str(above_html), str(below_html))

    @Slot(object, str)
    def handle_failed(self, finished_token: object, error_message: str) -> None:
        if finished_token is not self._token:
            return
        if getattr(self._owner, "_traits_prediction_render_token", None) is not finished_token:
            return
        message = f"Trait predictions unavailable: {html.escape(error_message)}"
        _apply_traits_prediction_view(self._owner, message, message)

    @Slot()
    def cleanup(self) -> None:
        if self._thread is not None and self._worker is not None:
            _forget_traits_prediction_worker_job(self._owner, self._thread, self._worker, self)
        self.deleteLater()


def _cache_traits_prediction_view(
    owner: Any,
    cache_key: str,
    above_html: str,
    below_html: str,
    updated_at: str,
) -> None:
    cache = getattr(owner, "_traits_prediction_view_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        owner._traits_prediction_view_cache = cache
    cache[cache_key] = {"above": above_html, "below": below_html, "updated_at": updated_at}


def _apply_traits_prediction_view(owner: Any, above_html: str, below_html: str, *, prefix_html: str = "") -> None:
    owner._traits_prediction_above_avg_html = f"{prefix_html}{above_html}"
    owner._traits_prediction_below_avg_html = f"{prefix_html}{below_html}"
    _set_traits_prediction_label_for_mode(owner)


def _forget_traits_prediction_worker_job(
    owner: Any,
    thread: QThread,
    worker: QObject,
    receiver: QObject,
) -> None:
    jobs = getattr(owner, "_traits_prediction_worker_jobs", None)
    if isinstance(jobs, list):
        try:
            jobs.remove((thread, worker, receiver))
        except ValueError:
            pass
    thread.deleteLater()


def stop_traits_prediction_refresh_workers(owner: Any, wait_msecs: int | None = None) -> None:
    """Stop Chart View trait prediction refresh threads before their owner is destroyed."""
    owner._traits_prediction_render_token = object()
    jobs = getattr(owner, "_traits_prediction_worker_jobs", None)
    if not isinstance(jobs, list) or not jobs:
        return

    for thread, _worker, _receiver in list(jobs):
        if not isinstance(thread, QThread):
            continue
        try:
            if thread.isRunning():
                thread.requestInterruption()
                thread.quit()
                if wait_msecs is None:
                    thread.wait()
                else:
                    thread.wait(max(0, int(wait_msecs)))
        except RuntimeError:
            continue
    jobs.clear()


def _start_traits_prediction_refresh_worker(
    owner: Any,
    chart: Any,
    traits: list[dict[str, Any]],
    cache_key: str,
    token: object,
) -> None:
    label = getattr(owner, "traits_prediction_label", None)
    if not isinstance(label, QLabel):
        return

    _predictions_debug(owner, "Trait refresh worker scheduling token=%s cache_key=%s", id(token), cache_key[:12])
    thread_parent = owner if isinstance(owner, QWidget) else None
    thread = QThread(thread_parent)
    worker = _TraitPredictionsRefreshWorker(owner, chart, traits, token)
    receiver = _TraitPredictionsRefreshReceiver(owner, cache_key, token)
    receiver.set_job(thread, worker)
    worker.moveToThread(thread)

    thread.started.connect(worker.run)
    worker.finished.connect(receiver.handle_finished, Qt.QueuedConnection)
    worker.failed.connect(receiver.handle_failed, Qt.QueuedConnection)
    worker.finished.connect(worker.deleteLater)
    worker.failed.connect(worker.deleteLater)
    worker.finished.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.finished.connect(receiver.cleanup, Qt.QueuedConnection)

    jobs = getattr(owner, "_traits_prediction_worker_jobs", None)
    if not isinstance(jobs, list):
        jobs = []
        owner._traits_prediction_worker_jobs = jobs
    jobs.append((thread, worker, receiver))
    thread.start()


def render_traits_predictions(owner: Any, chart: Any | None) -> None:
    """Render uploaded custom trait scores into Chart View's Predictions panel without showing stale chart data."""
    _predictions_debug(owner, "Trait render requested chart=%s", getattr(chart, "name", getattr(chart, "chart_uid", "none")))
    label = getattr(owner, "traits_prediction_label", None)
    if not isinstance(label, QLabel):
        return
    _configure_traits_prediction_label(owner, label)
    owner._traits_prediction_render_token = object()
    token = owner._traits_prediction_render_token
    traits = list_traits(active_only=True)
    owner._traits_prediction_trait_lookup = {
        str(trait.get("name", "")).strip().casefold(): trait
        for trait in traits
        if str(trait.get("name", "")).strip()
    }
    if not traits:
        message = (
            "No active traits. Reactivate traits in Settings > Traits to include them in Predictions."
            if list_traits()
            else "No traits uploaded. Add traits in Settings > Traits."
        )
        _apply_traits_prediction_view(owner, message, message)
        return
    if chart is None or owner._is_placeholder_chart(chart):
        _apply_traits_prediction_view(
            owner,
            "Trait predictions unavailable for this chart.",
            "Trait predictions unavailable for this chart.",
        )
        return

    cache_key = _trait_predictions_cache_key(owner, chart, traits)
    cached = (getattr(owner, "_traits_prediction_view_cache", {}) or {}).get(cache_key or "")
    if isinstance(cached, dict):
        _predictions_debug(owner, "Trait render view cache hit cache_key=%s", (cache_key or "")[:12])
        _apply_traits_prediction_view(
            owner,
            str(cached.get("above", "")),
            str(cached.get("below", "")),
            prefix_html=_trait_predictions_refresh_message(str(cached.get("updated_at", "") or "unknown")),
        )
    else:
        message = (
            _trait_predictions_refresh_message(None)
            + "<div style='color:#d8d8d8;'>Loading trait predictions for this chart…</div>"
        )
        _predictions_debug(owner, "Trait render no view cache; deferring metadata work to worker cache_key=%s", (cache_key or "")[:12])
        _apply_traits_prediction_view(owner, message, message)

    _start_traits_prediction_refresh_worker(owner, chart, traits, cache_key or "", token)
