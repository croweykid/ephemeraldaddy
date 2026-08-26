from pathlib import Path
import tomllib


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_setuptools_discovery_is_limited_to_application_packages():
    with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)

    package_find = pyproject["tool"]["setuptools"]["packages"]["find"]
    assert package_find["include"] == ["ephemeraldaddy*"]
    assert "ephemeraldaddy.graphics.alternate icons" in package_find["exclude"]
