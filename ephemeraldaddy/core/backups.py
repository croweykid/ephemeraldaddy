"""Full-app backup packages for EphemeralDaddy data stores."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import uuid
import zipfile
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Literal

from ephemeraldaddy.core import db as chart_db
from ephemeraldaddy.core.material_facts import personal_identifiers_path
from ephemeraldaddy.core.photo_gallery import photo_gallery_path
from ephemeraldaddy.analysis.time_sensitivity import TIME_SENSITIVITY_DB_PATH

BACKUP_PACKAGE_FORMAT = "ephemeraldaddy-backup"
BACKUP_PACKAGE_VERSION = 1
BACKUP_PACKAGE_SUFFIX = ".edbackup"
BACKUP_PACKAGE_FILENAME_PREFIX = "ephemeraldaddy_backup_"
PRE_RESTORE_BACKUP_FILENAME_PREFIX = "ephemeraldaddy_prerestore_backup_"
LEGACY_CHARTS_COMPONENT_KEY = "charts"
PENDING_APPEND_DIRECTORY_NAME = ".pending_backup_append"
PENDING_APPEND_STATE_FILENAME = "state.json"

BackupComponentKind = Literal["sqlite", "json", "file"]
BackupProgressCallback = Callable[[str, str, str, int, int], None]


@dataclass(frozen=True)
class BackupComponent:
    """A user data component that belongs in a full app backup package."""

    key: str
    path: Path
    archive_name: str
    kind: BackupComponentKind
    required: bool = False
    contains_sensitive_data: bool = True


def iter_backup_components() -> list[BackupComponent]:
    """Return all known app data components covered by one-click backups."""

    return [
        BackupComponent(
            key=LEGACY_CHARTS_COMPONENT_KEY,
            path=chart_db.DB_PATH,
            archive_name="charts.db",
            kind="sqlite",
            required=True,
            contains_sensitive_data=True,
        ),
        BackupComponent(
            key="photo_gallery",
            path=photo_gallery_path(),
            archive_name="charts.photo_gallery.db",
            kind="sqlite",
            required=False,
            contains_sensitive_data=True,
        ),
        BackupComponent(
            key="time_sensitivity",
            path=TIME_SENSITIVITY_DB_PATH,
            archive_name="time_sensitivity.db",
            kind="sqlite",
            required=False,
            contains_sensitive_data=False,
        ),
        BackupComponent(
            key="personal_identifiers",
            path=personal_identifiers_path(),
            archive_name="charts.personal_identifiers.json",
            kind="json",
            required=False,
            contains_sensitive_data=True,
        ),
    ]


def timestamped_backup_package_path(*, prefix: str = BACKUP_PACKAGE_FILENAME_PREFIX) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return chart_db.DB_DIR / f"{prefix}{timestamp}{BACKUP_PACKAGE_SUFFIX}"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot_sqlite(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    # A sqlite connection's context manager commits or rolls back, but does not
    # close the connection.  Explicitly close both handles so Windows can remove
    # the staged database when the backup temporary directory is cleaned up.
    with closing(sqlite3.connect(source)) as source_conn:
        with closing(sqlite3.connect(destination)) as destination_conn:
            source_conn.backup(destination_conn)


def _validate_sqlite(path: Path) -> None:
    with closing(sqlite3.connect(path)) as conn:
        row = conn.execute("PRAGMA integrity_check").fetchone()
    if not row or str(row[0]).lower() != "ok":
        raise ValueError(f"SQLite integrity check failed for {path.name}: {row[0] if row else 'no result'}")


def _snapshot_component(component: BackupComponent, destination: Path) -> None:
    if component.kind == "sqlite":
        _snapshot_sqlite(component.path, destination)
        _validate_sqlite(destination)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(component.path, destination)


def create_backup_package(
    destination: Path | None = None,
    *,
    component_source_overrides: dict[str, Path] | None = None,
    included_component_keys: Iterable[str] | None = None,
    preserve_missing_component_keys: Iterable[str] | None = None,
) -> Path:
    """Create a versioned backup package containing selected app data stores."""

    if destination is None:
        destination = timestamped_backup_package_path()
    destination = Path(destination)
    component_source_overrides = component_source_overrides or {}
    included_keys = set(included_component_keys) if included_component_keys is not None else None
    preserve_missing_keys = set(preserve_missing_component_keys or [])
    if destination.suffix.lower() != BACKUP_PACKAGE_SUFFIX:
        destination = destination.with_suffix(BACKUP_PACKAGE_SUFFIX)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ephemeraldaddy-backup-") as tmp_name:
        tmp_dir = Path(tmp_name)
        payload_dir = tmp_dir / "payload"
        data_dir = payload_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        manifest_components: list[dict[str, Any]] = []

        for component in iter_backup_components():
            relative_path = Path("data") / component.archive_name
            source_path = Path(component_source_overrides.get(component.key, component.path))
            component_selected = included_keys is None or component.key in included_keys
            restore_missing = "preserve" if component.key in preserve_missing_keys else "delete"
            manifest_entry: dict[str, Any] = {
                "key": component.key,
                "relative_path": relative_path.as_posix(),
                "kind": component.kind,
                "required": component.required,
                "contains_sensitive_data": component.contains_sensitive_data,
                "present": component_selected and source_path.exists(),
                "restore_missing": restore_missing,
            }
            if not component_selected or not source_path.exists():
                if component.required and component_selected:
                    raise FileNotFoundError(f"Required backup component missing: {source_path}")
                manifest_entry.update({"size_bytes": 0, "sha256": ""})
                manifest_components.append(manifest_entry)
                continue
            staged_path = payload_dir / relative_path
            snapshot_component = BackupComponent(
                key=component.key,
                path=source_path,
                archive_name=component.archive_name,
                kind=component.kind,
                required=component.required,
                contains_sensitive_data=component.contains_sensitive_data,
            )
            _snapshot_component(snapshot_component, staged_path)
            manifest_entry.update(
                {
                    "size_bytes": staged_path.stat().st_size,
                    "sha256": _sha256(staged_path),
                }
            )
            manifest_components.append(manifest_entry)

        manifest = {
            "format": BACKUP_PACKAGE_FORMAT,
            "format_version": BACKUP_PACKAGE_VERSION,
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "components": manifest_components,
        }
        (payload_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

        tmp_package = tmp_dir / f"{destination.name}.tmp"
        with zipfile.ZipFile(tmp_package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(payload_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(payload_dir).as_posix())
        shutil.move(str(tmp_package), destination)
    return destination


def _safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    destination_resolved = destination.resolve()
    for member in archive.infolist():
        target = (destination / member.filename).resolve()
        if not target.is_relative_to(destination_resolved):
            raise ValueError(f"Unsafe backup package path: {member.filename}")
    archive.extractall(destination)


def _load_manifest(archive: zipfile.ZipFile) -> dict[str, Any]:
    try:
        with archive.open("manifest.json") as fh:
            manifest = json.loads(fh.read().decode("utf-8"))
    except KeyError as exc:
        raise ValueError("Backup package is missing manifest.json") from exc
    if manifest.get("format") != BACKUP_PACKAGE_FORMAT:
        raise ValueError("Selected file is not an EphemeralDaddy backup package")
    if int(manifest.get("format_version", 0)) > BACKUP_PACKAGE_VERSION:
        raise ValueError("Backup package was created by a newer unsupported format")
    return manifest


def _pending_append_directory() -> Path:
    return chart_db.DB_DIR / PENDING_APPEND_DIRECTORY_NAME


def pending_backup_append_source() -> Path | None:
    """Return the source of an interrupted package append, if one exists."""

    state_path = _pending_append_directory() / PENDING_APPEND_STATE_FILENAME
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        if _pending_append_directory().exists():
            cancel_pending_backup_append()
        return None
    source = Path(str(state.get("source") or ""))
    if not source.exists():
        cancel_pending_backup_append()
        return None
    return source


def pending_backup_append_key() -> str | None:
    """Return the stable key used to make a resumed append idempotent."""

    state_path = _pending_append_directory() / PENDING_APPEND_STATE_FILENAME
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    import_key = str(state.get("import_key") or "").strip()
    return import_key or None


def cancel_pending_backup_append() -> None:
    """Discard files staged by an interrupted package append."""

    shutil.rmtree(_pending_append_directory(), ignore_errors=True)


def _save_pending_append_state(state: dict[str, Any]) -> None:
    pending_dir = _pending_append_directory()
    pending_dir.mkdir(parents=True, exist_ok=True)
    state_path = pending_dir / PENDING_APPEND_STATE_FILENAME
    temporary_path = state_path.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary_path, state_path)


@contextmanager
def staged_backup_component(
    source: Path,
    component_key: str,
    *,
    progress_callback: BackupProgressCallback | None = None,
):
    """Persistently stage all package members and yield one validated component.

    Staging every member preserves the complete append payload. Progress is
    recorded after each archive member so an interrupted import can resume on
    the next launch instead of expanding large sidecars again.
    """

    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"Backup file not found: {source}")

    pending_dir = _pending_append_directory()
    extract_dir = pending_dir / "extract"
    state_path = pending_dir / PENDING_APPEND_STATE_FILENAME
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {}
    if str(state.get("source") or "") != str(source.resolve()):
        cancel_pending_backup_append()
        state = {
            "source": str(source.resolve()),
            "import_key": uuid.uuid4().hex,
            "extracted_members": [],
        }
        _save_pending_append_state(state)
    elif not str(state.get("import_key") or "").strip():
        state["import_key"] = uuid.uuid4().hex
        _save_pending_append_state(state)
    extracted_members = set(state.get("extracted_members") or [])

    completed = False
    try:
        with zipfile.ZipFile(source) as archive:
            manifest = _load_manifest(archive)
            components = manifest.get("components")
            if not isinstance(components, list):
                raise ValueError("Backup package manifest has no components list")

            entry = next(
                (
                    item
                    for item in components
                    if isinstance(item, dict) and str(item.get("key") or "") == component_key
                ),
                None,
            )
            if entry is None or entry.get("present") is False:
                raise ValueError(f"Backup package does not contain component: {component_key}")

            relative_path = str(entry.get("relative_path") or "")
            try:
                member = archive.getinfo(relative_path)
            except KeyError as exc:
                raise ValueError(
                    f"Backup package is missing component file: {component_key}"
                ) from exc
            extract_root = extract_dir.resolve()
            archive_members = archive.infolist()
            completed_count = sum(
                1
                for archive_member in archive_members
                if archive_member.filename in extracted_members
                and (extract_dir / archive_member.filename).exists()
            )
            if progress_callback is not None:
                progress_callback(
                    "Database import", "extracting", "backup files", completed_count, len(archive_members)
                )
            for archive_member in archive_members:
                target = (extract_dir / archive_member.filename).resolve()
                if not target.is_relative_to(extract_root):
                    raise ValueError(f"Unsafe backup package path: {archive_member.filename}")
                if archive_member.filename in extracted_members and target.exists():
                    continue
                archive.extract(archive_member, extract_dir)
                extracted_members.add(archive_member.filename)
                state["extracted_members"] = sorted(extracted_members)
                _save_pending_append_state(state)
                completed_count += 1
                if progress_callback is not None:
                    progress_callback(
                        "Database import",
                        "extracting",
                        "backup files",
                        completed_count,
                        len(archive_members),
                    )

        staged_path = (extract_dir / member.filename).resolve()
        if not staged_path.is_relative_to(extract_dir.resolve()):
            raise ValueError(f"Unsafe backup package path for component {component_key}")
        expected_hash = str(entry.get("sha256") or "")
        if expected_hash and _sha256(staged_path) != expected_hash:
            raise ValueError(f"Checksum mismatch for backup component: {component_key}")
        if str(entry.get("kind") or "") == "sqlite":
            _validate_sqlite(staged_path)
        yield staged_path
        completed = True
    finally:
        if completed:
            cancel_pending_backup_append()


def _component_destinations() -> dict[str, Path]:
    return {component.key: component.path for component in iter_backup_components()}


def _create_pre_restore_backup() -> Path | None:
    if not chart_db.DB_PATH.exists():
        return None
    return create_backup_package(timestamped_backup_package_path(prefix=PRE_RESTORE_BACKUP_FILENAME_PREFIX))


def restore_backup_package(source: Path) -> None:
    """Validate and restore a full-app backup package."""

    source = Path(source)
    if not source.exists():
        raise FileNotFoundError(f"Backup file not found: {source}")
    destination_by_key = _component_destinations()

    with tempfile.TemporaryDirectory(prefix="ephemeraldaddy-restore-") as tmp_name:
        tmp_dir = Path(tmp_name)
        extract_dir = tmp_dir / "extract"
        with zipfile.ZipFile(source) as archive:
            manifest = _load_manifest(archive)
            _safe_extract(archive, extract_dir)

        components = manifest.get("components")
        if not isinstance(components, list):
            raise ValueError("Backup package manifest has no components list")

        staged_by_key: dict[str, Path] = {}
        preserve_missing_keys: set[str] = set()
        for entry in components:
            if not isinstance(entry, dict):
                raise ValueError("Backup package manifest contains an invalid component entry")
            key = str(entry.get("key") or "")
            relative_path = str(entry.get("relative_path") or "")
            expected_hash = str(entry.get("sha256") or "")
            kind = str(entry.get("kind") or "")
            if not key or key not in destination_by_key:
                continue
            if entry.get("present") is False:
                if entry.get("restore_missing") == "preserve":
                    preserve_missing_keys.add(key)
                continue
            staged_path = (extract_dir / relative_path).resolve()
            if not staged_path.is_relative_to(extract_dir.resolve()):
                raise ValueError(f"Unsafe backup package path for component {key}")
            if not staged_path.exists():
                raise ValueError(f"Backup package is missing component file: {key}")
            if expected_hash and _sha256(staged_path) != expected_hash:
                raise ValueError(f"Checksum mismatch for backup component: {key}")
            if kind == "sqlite":
                _validate_sqlite(staged_path)
            staged_by_key[key] = staged_path

        if LEGACY_CHARTS_COMPONENT_KEY not in staged_by_key:
            raise ValueError("Backup package is missing required charts database")

        _create_pre_restore_backup()

        chart_db.DB_DIR.mkdir(parents=True, exist_ok=True)
        rollback_dir = tmp_dir / "rollback"
        rollback_dir.mkdir(parents=True, exist_ok=True)
        replaced: list[tuple[Path, Path | None]] = []
        try:
            for key, destination in destination_by_key.items():
                source_component = staged_by_key.get(key)
                if source_component is None and key in preserve_missing_keys:
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                rollback_path: Path | None = None
                if destination.exists():
                    rollback_path = rollback_dir / destination.name
                    shutil.move(str(destination), rollback_path)
                replaced.append((destination, rollback_path))
                if source_component is None:
                    continue
                shutil.copy2(source_component, destination)
        except Exception:
            for destination, rollback_path in reversed(replaced):
                try:
                    if destination.exists():
                        destination.unlink()
                    if rollback_path is not None and rollback_path.exists():
                        shutil.move(str(rollback_path), destination)
                except Exception:
                    pass
            raise
