"""Platform-neutral update discovery for EphemeralDaddy.

Installing an update remains the responsibility of each signed platform
updater (MSIX/App Installer, Sparkle, Flatpak, or AppImageUpdate).
"""

from .checker import UpdateCheckResult, UpdateChecker, UpdateStatus
from .manifest import UpdateArtifact, UpdateManifest

__all__ = [
    "UpdateArtifact",
    "UpdateChecker",
    "UpdateCheckResult",
    "UpdateManifest",
    "UpdateStatus",
]

