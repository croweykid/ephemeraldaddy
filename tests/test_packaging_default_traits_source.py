from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_default_traits_are_in_python_package_data():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"ephemeraldaddy.analysis" = ["default_traits.json"]' in pyproject


def test_default_traits_are_in_pyinstaller_datas():
    build_source = (ROOT / "tools" / "build_desktop_app.py").read_text(encoding="utf-8")

    assert '"analysis" / "default_traits.json"' in build_source
    assert '"ephemeraldaddy/analysis"' in build_source
