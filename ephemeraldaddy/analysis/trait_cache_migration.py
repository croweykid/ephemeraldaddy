"""One-way import of legacy analytics vectors into the existing SQLite cache."""
from __future__ import annotations
import json
import logging
import threading
from ephemeraldaddy.core import db
from ephemeraldaddy.analysis.trait_signatures import trait_definition_signature

_lock = threading.RLock()
_imported: set[tuple[object, ...]] = set()


def import_legacy_trait_cache(traits=None):
    if traits is None:
        from ephemeraldaddy.analysis.traits import list_traits
        traits = list_traits(active_only=True)
    path = db.DB_DIR / ".traits_distribution_likelihood_cache.json"
    try:
        token = (str(path), path.stat().st_mtime_ns, tuple(sorted(trait_definition_signature(t) for t in traits)))
    except FileNotFoundError:
        return
    with _lock:
        if token in _imported:
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("version") not in (3, 4):
                return
            sequence = int(payload.get("db_change_sequence", 0) or 0)
            changed = {str(event["chart_uid"]).upper() for event in db.chart_changes_since(sequence)
                       if event.get("astro_data_changed")} if sequence else set()
            profiles = payload.get("profiles", [])
            definitions = {}
            for index, raw in enumerate(profiles):
                try:
                    signature = trait_definition_signature({"profile": json.loads(raw)})
                except (ValueError, TypeError):
                    continue
                definitions[index] = [t for t in traits if trait_definition_signature(t) == signature]
            rows = []
            for entry in payload.get("profile_entries", []):
                uid = str(entry.get("chart_uid", "") or "").strip().upper()
                if not uid or uid in changed:
                    continue  # Obsolete numeric identifiers never escape their adapter.
                try:
                    value = float(entry["likelihood"])
                    matched = definitions.get(int(entry["profile"]), [])
                except (KeyError, TypeError, ValueError):
                    continue
                for trait in matched:
                    rows.append({"chart_uid": uid, "trait_uid": str(trait.get("uid") or ""),
                                 "trait_name": trait["name"], "trait_signature": trait_definition_signature(trait),
                                 "likelihood": value, "chart_signature": "legacy-json"})
            db.import_trait_likelihood_rows(rows)
            _imported.add(token)
        except (OSError, ValueError):
            logging.getLogger(__name__).warning("Could not migrate the legacy Trait cache", exc_info=True)
