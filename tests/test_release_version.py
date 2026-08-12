from pathlib import Path

from ephemeraldaddy.version import __version__
from ephemeraldaddy.updates.versioning import ReleaseVersion

ROOT = Path(__file__).resolve().parents[1]


def test_authoritative_release_is_valid():
    assert str(ReleaseVersion.parse(__version__)) == __version__


def test_packaging_uses_authoritative_dynamic_version():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dynamic = ["version"]' in pyproject
    assert 'version = {attr = "ephemeraldaddy.version.__version__"}' in pyproject
    assert 'version = "0.1.0"' not in pyproject


def test_windows_installers_use_generated_version_include():
    generated = (ROOT / "packaging" / "windows" / "version.iss").read_text(
        encoding="utf-8"
    )
    assert f'#define MyAppVersion "{__version__}"' in generated
    for filename in ("installer.iss", "installer-onefile.iss"):
        source = (ROOT / filename).read_text(encoding="utf-8")
        assert '#include "packaging\\windows\\version.iss"' in source
        assert "AppVersion={#MyAppVersion}" in source
