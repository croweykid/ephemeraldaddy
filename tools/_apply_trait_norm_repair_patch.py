from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match in {path}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


traits_path = ROOT / "ephemeraldaddy" / "analysis" / "traits.py"
snapshot_path = ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "prediction_norms_snapshot.py"
predictions_path = ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "trait_predictions.py"

# 1. Bundled default UIDs are permanent identities. Duplicate resolved UIDs are fatal.
replace_once(
    traits_path,
    '''def trait_uid_for_profile(name: str, profile: Mapping[str, Any], *, bundled: bool = False) -> str:\n    for key in ("uid", "trait_uid"):\n        uid = normalize_trait_uid(profile.get(key))\n        if uid:\n            return uid\n    slug = _slugify_trait_name(name).lower()\n    return f"{'default' if bundled else 'custom'}_{slug}"\n\n\ndef _rewrite_single_trait''',
    '''def trait_uid_for_profile(name: str, profile: Mapping[str, Any], *, bundled: bool = False) -> str:\n    for key in ("uid", "trait_uid"):\n        uid = normalize_trait_uid(profile.get(key))\n        if uid:\n            return uid\n    slug = _slugify_trait_name(name).lower()\n    return f"{'default' if bundled else 'custom'}_{slug}"\n\n\nclass DuplicateBundledTraitUIDError(ValueError):\n    """Raised when bundled defaults resolve to the same permanent trait UID."""\n\n\ndef _validate_bundled_trait_uids(profiles: Mapping[str, Mapping[str, Any]]) -> None:\n    names_by_uid: dict[str, list[str]] = {}\n    for name, profile in profiles.items():\n        uid = trait_uid_for_profile(str(name), profile, bundled=True)\n        names_by_uid.setdefault(uid, []).append(str(name))\n    duplicates = {\n        uid: names\n        for uid, names in names_by_uid.items()\n        if len(names) > 1\n    }\n    if not duplicates:\n        return\n    detail = "; ".join(\n        f"{uid}: {', '.join(sorted(names, key=str.casefold))}"\n        for uid, names in sorted(duplicates.items())\n    )\n    raise DuplicateBundledTraitUIDError(\n        "Bundled default traits must have unique permanent UIDs; " + detail\n    )\n\n\ndef _rewrite_single_trait''',
    "insert bundled UID validator",
)

replace_once(
    traits_path,
    '''    try:\n        profiles = parse_trait_file(DEFAULT_TRAITS_PATH, skip_invalid_profiles=skip_corrupt)\n    except Exception as exc:\n        if not skip_corrupt:\n            raise\n        logger.warning(\n            "Traits panel skipped bundled default traits file %s while loading traits: %s",\n            DEFAULT_TRAITS_PATH,\n            exc,\n            exc_info=True,\n        )\n        return []\n''',
    '''    try:\n        profiles = parse_trait_file(DEFAULT_TRAITS_PATH, skip_invalid_profiles=skip_corrupt)\n        _validate_bundled_trait_uids(profiles)\n    except DuplicateBundledTraitUIDError:\n        logger.error(\n            "Bundled default trait UID validation failed for %s.",\n            DEFAULT_TRAITS_PATH,\n            exc_info=True,\n        )\n        raise\n    except Exception as exc:\n        if not skip_corrupt:\n            raise\n        logger.warning(\n            "Traits panel skipped bundled default traits file %s while loading traits: %s",\n            DEFAULT_TRAITS_PATH,\n            exc,\n            exc_info=True,\n        )\n        return []\n''',
    "validate bundled UIDs while loading defaults",
)

# 2. Stable norm identity migration + targeted repair.
replace_once(
    snapshot_path,
    '''    try:\n        profile_uid = trait_uid_for_profile(trait.get("profile", {}) or {})\n    except Exception:\n        profile_uid = ""\n''',
    '''    try:\n        profile_uid = trait_uid_for_profile(\n            str(trait.get("name", "") or "").strip(),\n            trait.get("profile", {}) or {},\n        )\n    except Exception:\n        profile_uid = ""\n''',
    "fix trait key fallback UID call",
)

migration_block = '''\n\ndef _trait_norm_row_matches(row: Any, trait: Mapping[str, Any]) -> bool:\n    if not isinstance(row, dict):\n        return False\n    if str(row.get("profile_hash", "") or "") != _stable_hash(trait.get("profile", {}) or {}):\n        return False\n    try:\n        float(row["db_average"])\n    except (KeyError, TypeError, ValueError):\n        return False\n    return True\n\n\ndef migrate_trait_norm_identities(\n    traits: list[dict[str, Any]],\n    snapshot: Mapping[str, Any] | None = None,\n    *,\n    path: Path | None = None,\n) -> dict[str, Any]:\n    """Copy compatible old norm rows to the current permanent trait UID once.\n\n    A migration is identity-only: the stored row must have the same trait name\n    and the exact same analytical profile hash. Changed profiles are deliberately\n    left unresolved so they are recalculated instead of inheriting stale norms.\n    Old rows are retained for backward compatibility.\n    """\n    combined = dict(snapshot or load_prediction_norms_snapshot())\n    combined_rows = combined.get("trait_baselines", {}) if isinstance(combined, dict) else {}\n    if not isinstance(combined_rows, dict) or not traits:\n        return combined\n\n    destination = path or _writable_trait_norms_path()\n    writable = _load_snapshot_file(destination)\n    if not writable:\n        writable = {\n            "version": PREDICTION_NORMS_SNAPSHOT_VERSION,\n            "snapshot_id": "",\n            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),\n            "chart_count": int(combined.get("chart_count", 0) or 0),\n            "snapshot_kind": "custom_trait_extensions",\n            "norm_signature": str(combined.get("norm_signature", "") or "custom_trait_extensions"),\n            "trait_baselines": {},\n            "retired_trait_keys": [],\n            "dnd_alignment_trait_keys": [],\n            "dnd_stat_raw_averages": {},\n        }\n    writable_rows = writable.setdefault("trait_baselines", {})\n    if not isinstance(writable_rows, dict):\n        writable_rows = {}\n        writable["trait_baselines"] = writable_rows\n\n    migrated: list[tuple[str, str, str]] = []\n    for trait in traits:\n        name = str(trait.get("name", "") or "").strip()\n        if not name:\n            continue\n        current_key = _trait_key(trait)\n        if _trait_norm_row_matches(combined_rows.get(current_key), trait):\n            continue\n        current_hash = _stable_hash(trait.get("profile", {}) or {})\n        candidates: list[tuple[str, dict[str, Any]]] = []\n        for old_key, row in combined_rows.items():\n            if old_key == current_key or not isinstance(row, dict):\n                continue\n            if str(row.get("name", "") or "").strip().casefold() != name.casefold():\n                continue\n            if str(row.get("profile_hash", "") or "") != current_hash:\n                continue\n            try:\n                float(row["db_average"])\n            except (KeyError, TypeError, ValueError):\n                continue\n            candidates.append((str(old_key), row))\n        if len(candidates) != 1:\n            continue\n        old_key, old_row = candidates[0]\n        payload = _trait_payload(trait)\n        writable_rows[current_key] = {\n            **old_row,\n            **payload,\n            "db_average": float(old_row["db_average"]),\n        }\n        migrated.append((old_key, current_key, name))\n\n    if not migrated:\n        return combined\n    writable["snapshot_id"] = _stable_hash(\n        {\n            "previous": str(writable.get("snapshot_id", "") or combined.get("snapshot_id", "")),\n            "migrated_trait_keys": sorted(new_key for _old_key, new_key, _name in migrated),\n        }\n    )\n    writable["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())\n    save_prediction_norms_snapshot(writable, destination)\n    logger.info(\n        "Migrated %s stored trait norm identity row(s): %s",\n        len(migrated),\n        ", ".join(f"{name} ({old_key} -> {new_key})" for old_key, new_key, name in migrated),\n    )\n    return _load_snapshot_file(destination) if path is not None else load_prediction_norms_snapshot()\n\n\ndef repair_trait_norms_snapshot(owner: Any, traits: list[dict[str, Any]]) -> dict[str, Any]:\n    """Migrate compatible norm identities, then recalculate only unresolved profiles."""\n    snapshot = migrate_trait_norm_identities(traits)\n    missing = missing_trait_norms(traits, snapshot)\n    if not missing:\n        return snapshot\n    names = [str(trait.get("name", "") or "").strip() for trait in missing]\n    logger.info(\n        "Recalculating %s missing or changed trait norm profile(s): %s",\n        len(missing),\n        ", ".join(name for name in names if name),\n    )\n    return refresh_trait_norms_snapshot(owner, missing)\n'''
replace_once(
    snapshot_path,
    '''\n\ndef prospective_trait_snapshot_token(\n''',
    migration_block + '''\n\ndef prospective_trait_snapshot_token(\n''',
    "insert identity migration and targeted repair",
)

replace_once(
    snapshot_path,
    '''    return _stable_hash(\n        {\n            "source": payload.get("active_source", load_prediction_norms_source()),\n            "population": payload.get("population_snapshot_id", ""),\n            "trait_extensions": local_token,\n        }\n    )\n''',
    '''    source = str(\n        payload.get("active_source", load_prediction_norms_source())\n        or load_prediction_norms_source()\n    )\n    population_token = str(payload.get("population_snapshot_id", "") or "")\n    extension_token = str(payload.get("trait_extension_snapshot_id", "") or "")\n    if source == PREDICTION_NORMS_SOURCE_MY_DATABASE:\n        population_token = local_token\n    else:\n        extension_token = local_token\n    return _stable_hash(\n        {\n            "source": source,\n            "population": population_token,\n            "trait_extensions": extension_token,\n        }\n    )\n''',
    "make prospective norm token source-aware",
)

# 3. Predictions: repair missing norms in the worker and keep unavailable rows visible.
replace_once(
    predictions_path,
    '''from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import (\n    load_prediction_norms_snapshot,\n    missing_trait_norms,\n    prospective_trait_snapshot_token,\n    trait_snapshot_averages,\n)\n''',
    '''from ephemeraldaddy.gui.features.charts.prediction_norms_snapshot import (\n    load_prediction_norms_snapshot,\n    migrate_trait_norm_identities,\n    missing_trait_norms,\n    prospective_trait_snapshot_token,\n    repair_trait_norms_snapshot,\n    trait_snapshot_averages,\n)\n''',
    "import norm migration and repair helpers",
)

replace_once(
    predictions_path,
    '''        row = self._rows[index.row()]\n        column = index.column()\n        if role == Qt.DisplayRole:\n''',
    '''        row = self._rows[index.row()]\n        column = index.column()\n        raw_deviation = row.get("deviation")\n        if role == Qt.DisplayRole:\n''',
    "capture optional deviation",
)
replace_once(
    predictions_path,
    '''            if column == 2:\n                return _format_signed_percentage(float(row.get("deviation", 0.0)))\n''',
    '''            if column == 2:\n                return _format_signed_percentage(\n                    None if raw_deviation is None else float(raw_deviation)\n                )\n''',
    "render unavailable deviation as dash",
)
replace_once(
    predictions_path,
    '''            if column == 2:\n                red, green, blue = appwide_red_green_rgb_for_range(float(row.get("deviation", 0.0)), -100.0, 100.0)\n                return QColor(red, green, blue)\n''',
    '''            if column == 2:\n                if raw_deviation is None:\n                    return QColor("#9a9a9a")\n                red, green, blue = appwide_red_green_rgb_for_range(float(raw_deviation), -100.0, 100.0)\n                return QColor(red, green, blue)\n''',
    "color unavailable deviation neutrally",
)
replace_once(
    predictions_path,
    '''        if role == Qt.ToolTipRole and column == 0:\n            return str(row.get("name", ""))\n''',
    '''        if role == Qt.ToolTipRole:\n            if column == 0:\n                return str(row.get("name", ""))\n            if column == 2 and raw_deviation is None:\n                return "Database norm unavailable; chart likelihood is still shown."\n''',
    "add unavailable norm tooltip",
)
replace_once(
    predictions_path,
    '''        if role == TRAIT_ROW_DEVIATION_ROLE:\n            return float(row.get("deviation", 0.0))\n        if role == TRAIT_ROW_DIRECTION_ROLE:\n            deviation = float(row.get("deviation", 0.0))\n''',
    '''        if role == TRAIT_ROW_DEVIATION_ROLE:\n            return None if raw_deviation is None else float(raw_deviation)\n        if role == TRAIT_ROW_DIRECTION_ROLE:\n            if raw_deviation is None:\n                return "unavailable"\n            deviation = float(raw_deviation)\n''',
    "classify unavailable norm rows",
)
replace_once(
    predictions_path,
    '''        mode = combo.currentData() if isinstance(combo, QComboBox) else "above"\n        return direction == ("below" if mode == "below" else "above")\n''',
    '''        mode = combo.currentData() if isinstance(combo, QComboBox) else "above"\n        target = "below" if mode == "below" else "above"\n        return direction in {target, "unavailable"}\n''',
    "show unavailable rows in either mode",
)
replace_once(
    predictions_path,
    '''        left_deviation = float(source.data(source.index(left.row(), 0), TRAIT_ROW_DEVIATION_ROLE) or 0.0)\n        right_deviation = float(source.data(source.index(right.row(), 0), TRAIT_ROW_DEVIATION_ROLE) or 0.0)\n        return abs(left_deviation) < abs(right_deviation)\n''',
    '''        left_deviation = float(source.data(source.index(left.row(), 0), TRAIT_ROW_DEVIATION_ROLE) or 0.0)\n        right_deviation = float(source.data(source.index(right.row(), 0), TRAIT_ROW_DEVIATION_ROLE) or 0.0)\n        return left_deviation < right_deviation\n''',
    "sort unavailable rows after significant rows",
)

replace_once(
    predictions_path,
    '''def _trait_rank_row(\n    name: str,\n    percentage: float,\n    *,\n    color: str,\n    db_average: float,\n    db_deviation: float,\n) -> str:\n    safe_name = html.escape(name)\n    pct = max(0.0, min(100.0, percentage))\n    safe_color = html.escape(normalize_trait_color(color))\n    safe_href = html.escape(f"trait:{urllib.parse.quote(name, safe='')}", quote=True)\n    difference_text = html.escape(_format_signed_percentage(db_deviation))\n    percentage_color = _percentage_color(pct, 0.0, 100.0)\n    difference_color = _percentage_color(db_deviation, -100.0, 100.0)\n    safe_title = html.escape(f"DB average: {max(0.0, min(100.0, db_average)):.1f}%")\n''',
    '''def _trait_rank_row(\n    name: str,\n    percentage: float,\n    *,\n    color: str,\n    db_average: float | None,\n    db_deviation: float | None,\n) -> str:\n    safe_name = html.escape(name)\n    pct = max(0.0, min(100.0, percentage))\n    safe_color = html.escape(normalize_trait_color(color))\n    safe_href = html.escape(f"trait:{urllib.parse.quote(name, safe='')}", quote=True)\n    difference_text = html.escape(_format_signed_percentage(db_deviation))\n    percentage_color = _percentage_color(pct, 0.0, 100.0)\n    difference_color = "#9a9a9a" if db_deviation is None else _percentage_color(db_deviation, -100.0, 100.0)\n    safe_title = html.escape(\n        "DB average unavailable"\n        if db_average is None\n        else f"DB average: {max(0.0, min(100.0, db_average)):.1f}%"\n    )\n''',
    "support unavailable HTML norm rows",
)
replace_once(
    predictions_path,
    '''def _trait_table(title: str, rows: list[tuple[str, float, float, float]], color_by_name: dict[str, str]) -> str:\n''',
    '''def _trait_table(\n    title: str,\n    rows: list[tuple[str, float, float | None, float | None]],\n    color_by_name: dict[str, str],\n) -> str:\n''',
    "allow optional DB values in HTML table",
)

replace_once(
    predictions_path,
    '''    snapshot = load_prediction_norms_snapshot()\n    missing_traits = missing_trait_norms(traits, snapshot)\n''',
    '''    try:\n        snapshot = migrate_trait_norm_identities(traits)\n    except Exception as exc:\n        logger.warning(\n            "Traits panel could not migrate stored trait norm identities: %s",\n            exc,\n            exc_info=True,\n        )\n        snapshot = load_prediction_norms_snapshot()\n    missing_traits = missing_trait_norms(traits, snapshot)\n''',
    "run cheap identity migration before render signatures",
)

old_rows_function = '''def _trait_prediction_rows_from_metadata(\n    traits: list[dict[str, Any]],\n    metadata: dict[str, Any],\n) -> list[dict[str, Any]]:\n    likelihoods = dict(metadata.get("likelihoods", {}))\n    database_averages = dict(metadata.get("database_averages", {}))\n    db_deviations = dict(metadata.get("deviations", {}))\n    color_by_name = {\n        str(trait.get("name", "")): normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR)))\n        for trait in traits\n    }\n    rows: list[dict[str, Any]] = []\n    for name, db_deviation in db_deviations.items():\n        if name not in likelihoods or name not in database_averages:\n            continue\n        deviation = float(db_deviation)\n        if abs(deviation) < TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD:\n            continue\n        rows.append(\n            {\n                "name": str(name),\n                "likelihood": float(likelihoods[name]),\n                "database_average": float(database_averages[name]),\n                "deviation": deviation,\n                "color": color_by_name.get(str(name), DEFAULT_TRAIT_COLOR),\n            }\n        )\n    return rows\n'''
new_rows_function = '''def _trait_prediction_rows_from_metadata(\n    traits: list[dict[str, Any]],\n    metadata: dict[str, Any],\n) -> list[dict[str, Any]]:\n    likelihoods = dict(metadata.get("likelihoods", {}))\n    database_averages = dict(metadata.get("database_averages", {}))\n    db_deviations = dict(metadata.get("deviations", {}))\n    color_by_name = {\n        str(trait.get("name", "")): normalize_trait_color(str(trait.get("color", DEFAULT_TRAIT_COLOR)))\n        for trait in traits\n    }\n    rows: list[dict[str, Any]] = []\n    for name, likelihood in likelihoods.items():\n        has_norm = name in database_averages and name in db_deviations\n        deviation = float(db_deviations[name]) if has_norm else None\n        if deviation is not None and abs(deviation) < TRAIT_DEVIATION_ASSIGNMENT_THRESHOLD:\n            continue\n        rows.append(\n            {\n                "name": str(name),\n                "likelihood": float(likelihood),\n                "database_average": float(database_averages[name]) if has_norm else None,\n                "deviation": deviation,\n                "color": color_by_name.get(str(name), DEFAULT_TRAIT_COLOR),\n            }\n        )\n    return rows\n'''
replace_once(predictions_path, old_rows_function, new_rows_function, "keep unavailable traits in table rows")

replace_once(
    predictions_path,
    '''    if not database_averages:\n        message = "Trait predictions unavailable until database trait averages can be calculated."\n        return message, message\n''',
    '''''',
    "do not hide all likelihoods when norms are unavailable",
)
replace_once(
    predictions_path,
    '''    below_avg_traits = sorted(\n        (\n            (name, float(likelihoods[name]), float(database_averages[name]), float(db_deviation))\n            for name, db_deviation in db_deviations.items()\n            if db_deviation <= -threshold\n        ),\n        key=lambda item: item[3],\n    )\n    return (\n''',
    '''    below_avg_traits = sorted(\n        (\n            (name, float(likelihoods[name]), float(database_averages[name]), float(db_deviation))\n            for name, db_deviation in db_deviations.items()\n            if db_deviation <= -threshold\n        ),\n        key=lambda item: item[3],\n    )\n    unavailable_rows = [\n        (name, float(likelihoods[name]), None, None)\n        for name in sorted(set(likelihoods) - set(database_averages), key=str.casefold)\n    ]\n    above_avg_traits.extend(unavailable_rows)\n    below_avg_traits.extend(unavailable_rows)\n    return (\n''',
    "append unavailable traits to legacy HTML tables",
)
replace_once(
    predictions_path,
    '''        f"The following traits failed to load: {html.escape(', '.join(names))}. "\n''',
    '''        f"DB comparison unavailable for: {html.escape(', '.join(names))}. "\n''',
    "describe unavailable norms accurately",
)

replace_once(
    predictions_path,
    '''            if self._is_cancelled():\n                _predictions_debug(self._owner, "Trait refresh worker cancelled before metadata token=%s", id(self._token))\n                self.failed.emit(self._token, "cancelled")\n                return\n            metadata = trait_metadata_for_chart(\n''',
    '''            if self._is_cancelled():\n                _predictions_debug(self._owner, "Trait refresh worker cancelled before metadata token=%s", id(self._token))\n                self.failed.emit(self._token, "cancelled")\n                return\n            snapshot = load_prediction_norms_snapshot()\n            missing_before = missing_trait_norms(self._traits, snapshot)\n            if missing_before:\n                _predictions_debug(\n                    self._owner,\n                    "Trait refresh worker repairing missing norm profiles=%s",\n                    len(missing_before),\n                )\n                try:\n                    snapshot = repair_trait_norms_snapshot(self._owner, self._traits)\n                except Exception as exc:\n                    logger.warning(\n                        "Traits panel targeted norm repair failed; rendering available likelihoods: %s",\n                        exc,\n                        exc_info=True,\n                    )\n                    snapshot = load_prediction_norms_snapshot()\n                actual_token = str(\n                    snapshot.get("snapshot_id")\n                    or snapshot.get("norm_signature")\n                    or "prediction_norm_snapshot:missing"\n                )\n                self._signatures["norm_signature"] = f"prediction_norms_snapshot:{actual_token}"\n                missing_after = missing_trait_norms(self._traits, snapshot)\n                if missing_after:\n                    logger.warning(\n                        "Traits panel still has unavailable norm profiles after targeted repair: %s",\n                        ", ".join(\n                            sorted(\n                                str(trait.get("name", "") or "").strip()\n                                for trait in missing_after\n                                if str(trait.get("name", "") or "").strip()\n                            )\n                        ),\n                    )\n            metadata = trait_metadata_for_chart(\n''',
    "repair only missing trait norms in background worker",
)

replace_once(
    predictions_path,
    '''    if chart_uid is not None:\n        rows_for_persistence = [\n            {\n                "trait_name": name,\n                "trait_uid": trait_uids_by_name.get(name, ""),\n                "trait_signature": trait_signature,\n                "direction": _direction_for_deviation(float(metadata.get("deviations", {}).get(name, 0.0))),\n                "likelihood": likelihoods.get(name, 0.0),\n                "db_average": database_averages.get(name, 0.0),\n                "deviation": metadata.get("deviations", {}).get(name, 0.0),\n            }\n            for name in active_trait_names\n        ]\n''',
    '''    if chart_uid is not None:\n        metadata_deviations = dict(metadata.get("deviations", {}) or {})\n        persistable_names = (\n            active_trait_names\n            & set(likelihoods)\n            & set(database_averages)\n            & set(metadata_deviations)\n        )\n        rows_for_persistence = [\n            {\n                "trait_name": name,\n                "trait_uid": trait_uids_by_name.get(name, ""),\n                "trait_signature": trait_signature,\n                "direction": _direction_for_deviation(float(metadata_deviations[name])),\n                "likelihood": float(likelihoods[name]),\n                "db_average": float(database_averages[name]),\n                "deviation": float(metadata_deviations[name]),\n            }\n            for name in sorted(persistable_names)\n        ]\n''',
    "never persist unresolved norms as zero",
)

# 4. Regression tests for permanent UID validation, identity migration, and source-aware tokens.
test_path = ROOT / "tests" / "test_trait_norm_identity_migration.py"
if test_path.exists():
    raise RuntimeError(f"Refusing to overwrite existing {test_path}")
test_path.write_text(
    '''from __future__ import annotations\n\nimport json\n\nimport pytest\n\nfrom ephemeraldaddy.analysis import traits as traits_module\nfrom ephemeraldaddy.gui.features.charts import prediction_norms_snapshot as pns\n\n\ndef _trait(name: str, uid: str, profile: dict) -> dict:\n    return {"name": name, "uid": uid, "trait_uid": uid, "profile": profile}\n\n\ndef _snapshot(rows: dict[str, dict], *, source: str = pns.PREDICTION_NORMS_SOURCE_MY_DATABASE) -> dict:\n    return {\n        "version": pns.PREDICTION_NORMS_SNAPSHOT_VERSION,\n        "snapshot_id": "combined-before",\n        "population_snapshot_id": "population-before",\n        "trait_extension_snapshot_id": "extension-before",\n        "active_source": source,\n        "chart_count": 2354,\n        "trait_baselines": rows,\n        "retired_trait_keys": [],\n        "dnd_alignment_trait_keys": [],\n        "dnd_stat_raw_averages": {},\n    }\n\n\ndef test_bundled_default_trait_uids_are_unique() -> None:\n    profiles = traits_module.parse_trait_file(\n        traits_module.DEFAULT_TRAITS_PATH,\n        skip_invalid_profiles=False,\n    )\n    traits_module._validate_bundled_trait_uids(profiles)\n    resolved = [\n        traits_module.trait_uid_for_profile(name, profile, bundled=True)\n        for name, profile in profiles.items()\n    ]\n    assert len(resolved) == len(set(resolved))\n\n\ndef test_duplicate_bundled_trait_uid_fails_loudly() -> None:\n    profiles = {\n        "first": {"uid": "default_same"},\n        "second": {"uid": "default_same"},\n    }\n    with pytest.raises(traits_module.DuplicateBundledTraitUIDError, match="default_same"):\n        traits_module._validate_bundled_trait_uids(profiles)\n\n\ndef test_identity_migration_copies_only_exact_analytical_match(tmp_path) -> None:\n    profile = {"signs": {"Taurus": 12}, "houses": {"10": 8}}\n    old_trait = _trait("cowboy", "legacy_cowboy", profile)\n    current_trait = _trait("cowboy", "default_cowboy", profile)\n    old_payload = pns._trait_payload(old_trait)\n    old_row = {**old_payload, "source": "custom_trait", "db_average": 63.25}\n    snapshot = _snapshot({old_payload["key"]: old_row})\n    destination = tmp_path / "snapshot.json"\n    destination.write_text(json.dumps(snapshot), encoding="utf-8")\n\n    migrated = pns.migrate_trait_norm_identities(\n        [current_trait],\n        snapshot=snapshot,\n        path=destination,\n    )\n\n    current_key = pns._trait_key(current_trait)\n    assert current_key in migrated["trait_baselines"]\n    assert migrated["trait_baselines"][current_key]["uid"] == "default_cowboy"\n    assert migrated["trait_baselines"][current_key]["db_average"] == pytest.approx(63.25)\n    assert old_payload["key"] in migrated["trait_baselines"]\n\n\ndef test_identity_migration_refuses_changed_profile(tmp_path) -> None:\n    old_trait = _trait("cowboy", "legacy_cowboy", {"signs": {"Taurus": 12}})\n    current_trait = _trait("cowboy", "default_cowboy", {"signs": {"Taurus": 13}})\n    old_payload = pns._trait_payload(old_trait)\n    snapshot = _snapshot(\n        {old_payload["key"]: {**old_payload, "source": "custom_trait", "db_average": 63.25}}\n    )\n    destination = tmp_path / "snapshot.json"\n    destination.write_text(json.dumps(snapshot), encoding="utf-8")\n\n    migrated = pns.migrate_trait_norm_identities(\n        [current_trait],\n        snapshot=snapshot,\n        path=destination,\n    )\n\n    assert pns._trait_key(current_trait) not in migrated["trait_baselines"]\n\n\ndef test_prospective_token_updates_my_database_population_component() -> None:\n    trait = _trait("intellectual", "default_intellectual", {"signs": {"Aquarius": 10}})\n    snapshot = _snapshot({})\n    token = pns.prospective_trait_snapshot_token([trait], snapshot)\n    local_token = pns._stable_hash(\n        {\n            "previous": "combined-before",\n            "updated_trait_keys": ["uid:default_intellectual"],\n        }\n    )\n    expected = pns._stable_hash(\n        {\n            "source": pns.PREDICTION_NORMS_SOURCE_MY_DATABASE,\n            "population": local_token,\n            "trait_extensions": "extension-before",\n        }\n    )\n    assert token == expected\n''',
    encoding="utf-8",
)

print("Trait norm repair patch applied successfully.")
