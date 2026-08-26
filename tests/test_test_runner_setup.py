from pathlib import Path

from tools.run_tests import operating_system_summary


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_test_setup_does_not_require_editable_application_install():
    readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
    requirements = (REPOSITORY_ROOT / "requirements-test.txt").read_text(
        encoding="utf-8"
    )

    assert "--no-cache-dir -r requirements-test.txt" in readme
    assert "pip install -e" not in readme
    assert "pytest>=8" in requirements


def test_test_report_header_has_an_explicit_operating_system_summary():
    source = (REPOSITORY_ROOT / "tools" / "run_tests.py").read_text(encoding="utf-8")

    assert operating_system_summary()
    assert 'f"Operating system: {operating_system_summary()}"' in source
    assert source.index("Operating system:") < source.index('f"Platform: {platform.platform()}"')
