"""Release acceptance scenarios required of every native update adapter."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ephemeraldaddy.updates.acceptance import (
    AcceptanceResult,
    FailureAction,
    UpdateAcceptanceCoordinator,
    UpdateAcceptanceError,
    artifact_sha256_check,
    boolean_check,
)


def passing(name="healthy"):
    return lambda: AcceptanceResult(name, True)


def failing(name, detail="failed"):
    return lambda: AcceptanceResult(name, False, detail)


def coordinator(state, *, preflight=(), post_install=(), backup=True, require_backup=True):
    def create_backup():
        state["events"].append("backup")
        state["snapshot"] = dict(state.get("user_data", {}))
        return Path("pre-update.edbackup") if backup else None

    def restore_backup(_path):
        state["events"].append("restore-data")
        state["user_data"] = dict(state["snapshot"])

    return UpdateAcceptanceCoordinator(
        preflight_checks=preflight,
        post_install_checks=post_install,
        create_backup=create_backup,
        restore_backup=restore_backup,
        require_backup=require_backup,
    )


def apply(state, service, *, install=None):
    def default_install():
        state["events"].append("install")
        state["version"] = "3.1.0"

    def rollback():
        state["events"].append("rollback-app")
        state["version"] = "3.0.0"

    return service.apply(install=install or default_install, rollback=rollback)


def test_fresh_install_acceptance_without_existing_user_data():
    state = {"events": [], "version": None}
    service = coordinator(
        state,
        preflight=[passing("fresh-install")],
        post_install=[passing()],
        backup=False,
        require_backup=False,
    )
    assert apply(state, service).passed
    assert state["version"] == "3.1.0"


@pytest.mark.parametrize("installed_version", ["3.0.0", "2.5.0"])
def test_update_from_previous_and_oldest_supported_release(installed_version):
    state = {"events": [], "version": installed_version}
    supported = boolean_check(
        "supported_base_version",
        lambda: state["version"] in {"2.5.0", "3.0.0"},
        "installed release is older than the supported update path",
    )
    service = coordinator(state, preflight=[supported], post_install=[passing()])
    assert apply(state, service).passed


def test_update_with_existing_charts_database_creates_backup_before_install():
    state = {"events": [], "version": "3.0.0", "user_data": {"charts": "uid-1"}}
    service = coordinator(state, preflight=[passing()], post_install=[passing()])
    apply(state, service)
    assert state["events"][:2] == ["backup", "install"]


def test_failed_preupdate_backup_cancels_before_install():
    state = {"events": [], "version": "3.0.0"}

    def create_backup():
        state["events"].append("backup-failed")
        raise OSError("backup verification failed")

    service = UpdateAcceptanceCoordinator(
        preflight_checks=[passing()],
        post_install_checks=[passing()],
        create_backup=create_backup,
        restore_backup=lambda _path: None,
    )
    with pytest.raises(UpdateAcceptanceError) as caught:
        apply(state, service)
    assert caught.value.action is FailureAction.CANCEL
    assert state["events"] == ["backup-failed"]


def test_missing_required_preupdate_backup_cancels_before_install():
    state = {"events": [], "version": "3.0.0"}
    service = coordinator(state, preflight=[passing()], post_install=[passing()], backup=False)
    with pytest.raises(UpdateAcceptanceError) as caught:
        apply(state, service)
    assert caught.value.action is FailureAction.CANCEL
    assert state["events"] == ["backup"]


def test_interrupted_download_or_install_rolls_back_app_and_user_data():
    state = {"events": [], "version": "3.0.0", "user_data": {"charts": "original"}}
    service = coordinator(state, preflight=[passing()], post_install=[passing()])

    def interrupted_install():
        state["version"] = "partial"
        state["user_data"]["charts"] = "partial migration"
        raise ConnectionError("download interrupted")

    with pytest.raises(UpdateAcceptanceError) as caught:
        apply(state, service, install=interrupted_install)
    assert caught.value.action is FailureAction.ROLLBACK
    assert state["version"] == "3.0.0"
    assert state["user_data"]["charts"] == "original"


def test_invalid_signature_cancels_before_backup_or_install():
    state = {"events": [], "version": "3.0.0"}
    signature = boolean_check("native_signature", lambda: False, "invalid platform signature")
    service = coordinator(state, preflight=[signature], post_install=[passing()])
    with pytest.raises(UpdateAcceptanceError) as caught:
        apply(state, service)
    assert caught.value.action is FailureAction.CANCEL
    assert state["events"] == []


def test_corrupted_update_artifact_cancels_before_install(tmp_path):
    artifact = tmp_path / "update.bin"
    artifact.write_bytes(b"corrupted")
    expected = hashlib.sha256(b"authentic").hexdigest()
    state = {"events": [], "version": "3.0.0"}
    service = coordinator(
        state,
        preflight=[artifact_sha256_check(artifact, expected)],
        post_install=[passing()],
    )
    with pytest.raises(UpdateAcceptanceError):
        apply(state, service)
    assert "install" not in state["events"]


@pytest.mark.parametrize(
    ("check_name", "detail"),
    [
        ("sufficient_disk_space", "not enough free disk space"),
        ("application_not_running", "EphemeralDaddy must be closed"),
    ],
)
def test_ineligible_machine_conditions_cancel_before_install(check_name, detail):
    state = {"events": [], "version": "3.0.0"}
    service = coordinator(state, preflight=[failing(check_name, detail)], post_install=[passing()])
    with pytest.raises(UpdateAcceptanceError) as caught:
        apply(state, service)
    assert caught.value.report.failures[0].name == check_name
    assert state["events"] == []


def test_upgrade_must_launch_before_candidate_is_accepted():
    state = {"events": [], "version": "3.0.0"}
    service = coordinator(state, preflight=[passing()], post_install=[failing("launch_probe")])
    with pytest.raises(UpdateAcceptanceError):
        apply(state, service)
    assert state["version"] == "3.0.0"


def test_database_backup_and_successful_migration_are_accepted():
    state = {"events": [], "version": "3.0.0", "user_data": {"schema": 20}}
    migrated = boolean_check(
        "database_migration",
        lambda: state["user_data"]["schema"] == 21,
        "database schema migration incomplete",
    )
    service = coordinator(state, preflight=[passing()], post_install=[migrated])

    def install():
        state["version"] = "3.1.0"
        state["user_data"]["schema"] = 21

    assert apply(state, service, install=install).passed
    assert state["events"][0] == "backup"


def test_failed_migration_restores_prior_release_and_database():
    state = {"events": [], "version": "3.0.0", "user_data": {"schema": 20}}
    service = coordinator(
        state,
        preflight=[passing()],
        post_install=[failing("database_migration")],
    )

    def install():
        state["version"] = "3.1.0"
        state["user_data"]["schema"] = "broken"

    with pytest.raises(UpdateAcceptanceError):
        apply(state, service, install=install)
    assert state["version"] == "3.0.0"
    assert state["user_data"]["schema"] == 20


def test_settings_photos_and_charts_survive_failed_update_unchanged():
    original = {"settings": "dark", "photos": b"photo", "charts": "uid-1"}
    state = {"events": [], "version": "3.0.0", "user_data": dict(original)}
    service = coordinator(state, preflight=[passing()], post_install=[failing("data_survival")])

    def install():
        state["version"] = "3.1.0"
        state["user_data"].update(settings="lost", photos=b"", charts="")

    with pytest.raises(UpdateAcceptanceError):
        apply(state, service, install=install)
    assert state["user_data"] == original


def test_settings_photos_and_charts_survive_successful_update_unchanged():
    original = {"settings": "dark", "photos": b"photo", "charts": "uid-1"}
    state = {"events": [], "version": "3.0.0", "user_data": dict(original)}
    survival = boolean_check(
        "data_survival",
        lambda: state["user_data"] == original,
        "user data changed during application update",
    )
    service = coordinator(state, preflight=[passing()], post_install=[survival])
    assert apply(state, service).passed
    assert state["user_data"] == original
