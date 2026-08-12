"""Validated model for the public update manifest."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .versioning import ReleaseVersion

SUPPORTED_SCHEMA_VERSION = 1
SUPPORTED_CHANNELS = frozenset({"stable", "beta"})
SUPPORTED_ARTIFACT_TYPES = frozenset(
    {"appinstaller", "sparkle-appcast", "flatpak", "appimage-zsync"}
)


@dataclass(frozen=True, slots=True)
class UpdateArtifact:
    """A platform updater endpoint advertised by a release manifest."""

    kind: str
    url: str = ""
    ref: str = ""
    sha256: str = ""

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "UpdateArtifact":
        kind = str(data.get("type", "")).strip()
        if kind not in SUPPORTED_ARTIFACT_TYPES:
            raise ValueError(f"Unsupported update artifact type: {kind!r}")
        url = str(data.get("url", "")).strip()
        ref = str(data.get("ref", "")).strip()
        if not url and not ref:
            raise ValueError("Update artifact requires a URL or platform reference")
        return cls(kind=kind, url=url, ref=ref, sha256=str(data.get("sha256", "")).strip())


@dataclass(frozen=True, slots=True)
class UpdateManifest:
    """Release metadata shared by update discovery on every platform."""

    channel: str
    version: ReleaseVersion
    minimum_supported_version: ReleaseVersion
    published_at: str
    release_notes_url: str
    artifacts: Mapping[str, UpdateArtifact]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "UpdateManifest":
        schema_version = data.get("schema_version")
        if schema_version != SUPPORTED_SCHEMA_VERSION:
            raise ValueError(f"Unsupported update manifest schema: {schema_version!r}")
        channel = str(data.get("channel", "")).strip().lower()
        if channel not in SUPPORTED_CHANNELS:
            raise ValueError(f"Unsupported update channel: {channel!r}")
        raw_artifacts = data.get("artifacts")
        if not isinstance(raw_artifacts, Mapping) or not raw_artifacts:
            raise ValueError("Update manifest must contain platform artifacts")
        artifacts = {
            str(platform_key): UpdateArtifact.from_mapping(artifact)
            for platform_key, artifact in raw_artifacts.items()
            if isinstance(artifact, Mapping)
        }
        if len(artifacts) != len(raw_artifacts):
            raise ValueError("Every update artifact must be an object")
        return cls(
            channel=channel,
            version=ReleaseVersion.parse(str(data.get("version", ""))),
            minimum_supported_version=ReleaseVersion.parse(
                str(data.get("minimum_supported_version", ""))
            ),
            published_at=str(data.get("published_at", "")).strip(),
            release_notes_url=str(data.get("release_notes_url", "")).strip(),
            artifacts=artifacts,
        )

