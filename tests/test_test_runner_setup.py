from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_test_setup_does_not_require_editable_application_install():
    readme = (REPOSITORY_ROOT / "README.md").read_text(encoding="utf-8")
    requirements = (REPOSITORY_ROOT / "requirements-test.txt").read_text(
        encoding="utf-8"
    )

    assert "--no-cache-dir -r requirements-test.txt" in readme
    assert "pip install -e" not in readme
    assert "pytest>=8" in requirements
