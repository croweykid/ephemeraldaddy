"""Side-effect-free update decisions with an injectable manifest transport."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ephemeraldaddy.version import __version__

from .manifest import UpdateArtifact, UpdateManifest
from .platforms import current_platform_key
from .versioning import ReleaseVersion

ManifestFetcher = Callable[[str], bytes]


class UpdateStatus(str, Enum):
    CURRENT = "current"
    AVAILABLE = "available"
    FULL_UPDATE_REQUIRED = "full_update_required"
    PLATFORM_UNSUPPORTED = "platform_unsupported"


@dataclass(frozen=True, slots=True)
class UpdateCheckResult:
    status: UpdateStatus
    current_version: ReleaseVersion
    manifest: UpdateManifest
    artifact: UpdateArtifact | None


def fetch_manifest(url: str) -> bytes:
    """Fetch a manifest only when explicitly requested by the caller."""

    request = Request(url, headers={"User-Agent": f"EphemeralDaddy/{__version__}"})
    with urlopen(request, timeout=10) as response:  # noqa: S310 - configured HTTPS endpoint
        return response.read()


class UpdateChecker:
    """Discover an update; installation is delegated to the platform updater."""

    def __init__(self, manifest_url: str, *, fetcher: ManifestFetcher = fetch_manifest) -> None:
        if urlparse(manifest_url).scheme.lower() != "https":
            raise ValueError("Update manifests must be loaded over HTTPS")
        self.manifest_url = manifest_url
        self._fetcher = fetcher

    def check(
        self,
        *,
        channel: str = "stable",
        platform_key: str | None = None,
    ) -> UpdateCheckResult:
        payload = json.loads(self._fetcher(self.manifest_url).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Update manifest root must be an object")
        manifest = UpdateManifest.from_mapping(payload)
        if manifest.channel != channel:
            raise ValueError(
                f"Expected {channel!r} update channel, received {manifest.channel!r}"
            )
        current = ReleaseVersion.parse(__version__)
        artifact = manifest.artifacts.get(platform_key or current_platform_key())
        if artifact is None:
            status = UpdateStatus.PLATFORM_UNSUPPORTED
        elif current < manifest.minimum_supported_version:
            status = UpdateStatus.FULL_UPDATE_REQUIRED
        elif current < manifest.version:
            status = UpdateStatus.AVAILABLE
        else:
            status = UpdateStatus.CURRENT
        return UpdateCheckResult(status, current, manifest, artifact)
