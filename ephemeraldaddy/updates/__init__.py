"""Platform-neutral update discovery for EphemeralDaddy.

Installing an update remains the responsibility of each signed platform
updater (MSIX/App Installer, Sparkle, Flatpak, or AppImageUpdate).
"""

from .acceptance import (
    AcceptanceReport,
    AcceptanceResult,
    AcceptanceStage,
    FailureAction,
    UpdateAcceptanceCoordinator,
    UpdateAcceptanceError,
)
from .checker import UpdateCheckResult, UpdateChecker, UpdateStatus
from .manifest import UpdateArtifact, UpdateManifest

__all__ = [
    "AcceptanceReport",
    "AcceptanceResult",
    "AcceptanceStage",
    "FailureAction",
    "UpdateArtifact",
    "UpdateAcceptanceCoordinator",
    "UpdateAcceptanceError",
    "UpdateChecker",
    "UpdateCheckResult",
    "UpdateManifest",
    "UpdateStatus",
]
