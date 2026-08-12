import json

import pytest

from ephemeraldaddy.updates.checker import UpdateChecker, UpdateStatus
from ephemeraldaddy.updates.manifest import UpdateManifest
from ephemeraldaddy.updates.versioning import ReleaseVersion


def _manifest(**overrides):
    data = {
        "schema_version": 1,
        "channel": "stable",
        "version": "3.1.0",
        "minimum_supported_version": "3.0.0",
        "published_at": "2026-09-01T00:00:00Z",
        "release_notes_url": "https://updates.example/releases/3.1.0",
        "artifacts": {
            "windows-x86_64": {
                "type": "appinstaller",
                "url": "https://updates.example/EphemeralDaddy.appinstaller",
            }
        },
    }
    data.update(overrides)
    return data


def _checker(data):
    payload = json.dumps(data).encode("utf-8")
    return UpdateChecker("https://updates.example/stable.json", fetcher=lambda _url: payload)


def test_release_versions_compare_prereleases_before_final_releases():
    assert ReleaseVersion.parse("3.1.0-beta.2") < ReleaseVersion.parse("3.1.0")
    assert ReleaseVersion.parse("3.0.9") < ReleaseVersion.parse("3.1.0")


def test_checker_reports_update_for_supported_platform():
    result = _checker(_manifest()).check(platform_key="windows-x86_64")
    assert result.status is UpdateStatus.AVAILABLE
    assert result.artifact is not None
    assert result.artifact.kind == "appinstaller"


def test_checker_reports_current_version():
    result = _checker(_manifest(version="3.0.0")).check(platform_key="windows-x86_64")
    assert result.status is UpdateStatus.CURRENT


def test_checker_requires_full_package_below_supported_base():
    result = _checker(_manifest(minimum_supported_version="3.0.1")).check(
        platform_key="windows-x86_64"
    )
    assert result.status is UpdateStatus.FULL_UPDATE_REQUIRED


def test_checker_reports_platform_without_artifact():
    result = _checker(_manifest()).check(platform_key="linux-arm64")
    assert result.status is UpdateStatus.PLATFORM_UNSUPPORTED


def test_manifest_rejects_unknown_artifact_type():
    data = _manifest(
        artifacts={"windows-x86_64": {"type": "shell-script", "url": "https://bad"}}
    )
    with pytest.raises(ValueError, match="Unsupported update artifact type"):
        UpdateManifest.from_mapping(data)


def test_checker_rejects_insecure_manifest_url():
    with pytest.raises(ValueError, match="HTTPS"):
        UpdateChecker("http://updates.example/stable.json")
