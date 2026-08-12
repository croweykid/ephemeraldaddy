"""Preflight, post-install, and rollback gates for native update adapters.

This module never replaces application files itself. Platform adapters provide
atomic install and rollback functions while this coordinator decides whether an
update may proceed and whether an installed candidate may be accepted.
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class AcceptanceStage(str, Enum):
    PREFLIGHT = "preflight"
    POST_INSTALL = "post_install"


class FailureAction(str, Enum):
    CANCEL = "cancel"
    ROLLBACK = "rollback"


@dataclass(frozen=True, slots=True)
class AcceptanceResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class AcceptanceReport:
    stage: AcceptanceStage
    results: tuple[AcceptanceResult, ...]

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.results)

    @property
    def failures(self) -> tuple[AcceptanceResult, ...]:
        return tuple(result for result in self.results if not result.passed)


class UpdateAcceptanceError(RuntimeError):
    """Raised after an update is cancelled or rolled back safely."""

    def __init__(
        self,
        message: str,
        *,
        action: FailureAction,
        report: AcceptanceReport | None = None,
    ) -> None:
        super().__init__(message)
        self.action = action
        self.report = report


AcceptanceCheck = Callable[[], AcceptanceResult]
BackupCreator = Callable[[], Path | None]
BackupRestorer = Callable[[Path], None]
UpdateOperation = Callable[[], None]


def run_acceptance_checks(
    stage: AcceptanceStage,
    checks: Iterable[AcceptanceCheck],
) -> AcceptanceReport:
    """Run every check so diagnostics contain all eligibility failures."""

    results: list[AcceptanceResult] = []
    for check in checks:
        try:
            result = check()
            if not isinstance(result, AcceptanceResult):
                raise TypeError("acceptance check did not return AcceptanceResult")
        except Exception as exc:
            name = getattr(check, "__name__", check.__class__.__name__)
            result = AcceptanceResult(name=name, passed=False, detail=str(exc))
        results.append(result)
    return AcceptanceReport(stage=stage, results=tuple(results))


class UpdateAcceptanceCoordinator:
    """Accept a native update only after preflight and post-install gates pass."""

    def __init__(
        self,
        *,
        preflight_checks: Iterable[AcceptanceCheck],
        post_install_checks: Iterable[AcceptanceCheck],
        create_backup: BackupCreator,
        restore_backup: BackupRestorer,
        require_backup: bool = True,
    ) -> None:
        self._preflight_checks = tuple(preflight_checks)
        self._post_install_checks = tuple(post_install_checks)
        self._create_backup = create_backup
        self._restore_backup = restore_backup
        self._require_backup = require_backup

    def apply(self, *, install: UpdateOperation, rollback: UpdateOperation) -> AcceptanceReport:
        """Install, validate, or restore both native app and user-data backup.

        A preflight failure cancels before backup or installation. Once a backup
        exists, any installer exception or post-install failure invokes the
        native rollback and restores the user-data snapshot.
        """

        preflight = run_acceptance_checks(AcceptanceStage.PREFLIGHT, self._preflight_checks)
        if not preflight.passed:
            raise UpdateAcceptanceError(
                "This machine is not currently eligible for the update.",
                action=FailureAction.CANCEL,
                report=preflight,
            )

        try:
            backup_path = self._create_backup()
            if self._require_backup and backup_path is None:
                raise RuntimeError("backup creator did not return a verified backup path")
        except Exception as exc:
            raise UpdateAcceptanceError(
                "A verified pre-update backup could not be created; the update was cancelled.",
                action=FailureAction.CANCEL,
                report=preflight,
            ) from exc
        try:
            install()
            post_install = run_acceptance_checks(
                AcceptanceStage.POST_INSTALL,
                self._post_install_checks,
            )
            if not post_install.passed:
                raise UpdateAcceptanceError(
                    "The updated application did not pass its acceptance checks.",
                    action=FailureAction.ROLLBACK,
                    report=post_install,
                )
            return post_install
        except Exception as exc:
            rollback_errors: list[str] = []
            try:
                rollback()
            except Exception as rollback_exc:
                rollback_errors.append(f"application rollback failed: {rollback_exc}")
            if backup_path is not None:
                try:
                    self._restore_backup(backup_path)
                except Exception as restore_exc:
                    rollback_errors.append(f"user-data restore failed: {restore_exc}")
            if rollback_errors:
                detail = (
                    " Automatic rollback was incomplete; manual recovery is required: "
                    f"{'; '.join(rollback_errors)}"
                )
            else:
                detail = ""
            if isinstance(exc, UpdateAcceptanceError):
                raise UpdateAcceptanceError(
                    f"{exc}{detail}",
                    action=FailureAction.ROLLBACK,
                    report=exc.report,
                ) from exc
            raise UpdateAcceptanceError(
                (
                    "Update installation did not complete; the prior release was restored."
                    if not rollback_errors
                    else "Update installation did not complete."
                )
                + detail,
                action=FailureAction.ROLLBACK,
            ) from exc


def disk_space_check(target: Path, required_bytes: int) -> AcceptanceCheck:
    def check() -> AcceptanceResult:
        free_bytes = shutil.disk_usage(target).free
        return AcceptanceResult(
            name="sufficient_disk_space",
            passed=free_bytes >= required_bytes,
            detail=f"required={required_bytes} free={free_bytes}",
        )

    return check


def artifact_sha256_check(artifact: Path, expected_sha256: str) -> AcceptanceCheck:
    def check() -> AcceptanceResult:
        digest = hashlib.sha256()
        with artifact.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        actual = digest.hexdigest()
        return AcceptanceResult(
            name="artifact_sha256",
            passed=actual.lower() == expected_sha256.strip().lower(),
            detail=f"expected={expected_sha256} actual={actual}",
        )

    return check


def boolean_check(name: str, predicate: Callable[[], bool], failure_detail: str) -> AcceptanceCheck:
    """Adapt native signature/process/launch/database probes to one contract."""

    def check() -> AcceptanceResult:
        passed = bool(predicate())
        return AcceptanceResult(name=name, passed=passed, detail="" if passed else failure_detail)

    return check
