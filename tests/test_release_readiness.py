from pathlib import Path

from tools.check_release_readiness import common_checks, platform_checks

ROOT = Path(__file__).resolve().parents[1]


def test_common_release_inputs_are_ready():
    failures = [check for check in common_checks() if check.required and not check.passed]
    assert failures == []


def test_windows_installers_have_stable_identity_and_close_running_app():
    for filename in ("installer.iss", "installer-onefile.iss"):
        source = (ROOT / filename).read_text(encoding="utf-8")
        assert "AppId=io.github.ephemeraldaddy.EphemeralDaddy" in source
        assert "CloseApplications=yes" in source
        assert "RestartApplications=no" in source


def test_linux_packaging_paths_and_permissions_are_release_safe():
    manifest = (
        ROOT / "flatpak" / "io.github.ephemeraldaddy.EphemeralDaddy.yml"
    ).read_text(encoding="utf-8")
    assert "cp -a dist/EphemeralDaddy/. /app/lib/ephemeraldaddy/" in manifest
    assert "../dist/EphemeralDaddy" not in manifest
    assert "--filesystem=~/.ephemeraldaddy:create" in manifest
    assert "--filesystem=home" not in manifest


def test_optional_platform_tools_do_not_make_repository_preflight_fail():
    for target in ("windows", "linux"):
        assert all(check.passed or not check.required for check in platform_checks(target))


def test_pyinstaller_does_not_bundle_every_pyside_module():
    source = (ROOT / "tools" / "build_desktop_app.py").read_text(encoding="utf-8")
    assert 'collect_all("PySide6")' not in source
    assert 'collect_all("shiboken6")' not in source
    assert 'hooksconfig={{"matplotlib": {{"backends": ["QtAgg"]}}}}' in source
