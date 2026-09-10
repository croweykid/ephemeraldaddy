from pathlib import Path

import pytest

from ephemeraldaddy.analysis import plugins


@pytest.fixture
def plugin_dirs(monkeypatch, tmp_path):
    plugin_dir = tmp_path / "plugins"
    monkeypatch.setattr(plugins, "PLUGIN_DIR", plugin_dir)
    monkeypatch.setattr(plugins, "DISABLED_PLUGIN_DIR", plugin_dir / "disabled")
    plugins.invalidate_plugin_caches()
    return plugin_dir


def _write_python_plugin(folder: Path, *, body: str = "return [[{'text': 'ok'}]]") -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "sun_moon_hot_takes.json").write_text("{}", encoding="utf-8")
    path = folder / "sun-moon_hot-takes.py"
    path.write_text(
        "PLUGIN_MANIFEST = {'api_version': 1, 'name': 'Sun-Moon Hot Takes', "
        "'hooks': ['chart_info'], 'data_files': ['sun_moon_hot_takes.json']}\n"
        f"def chart_info(context):\n    {body}\n",
        encoding="utf-8",
    )
    return path


def test_registry_contains_both_supported_plugins():
    assert plugins.recognized_plugin_names() == ["humdes_gates.json", "sun-moon_hot-takes.py"]
    assert [spec.display_name for spec in plugins.PLUGIN_SPECS] == [
        "Human Design Gates-Lines Supplement",
        "Sun-Moon Hot Takes",
    ]


def test_install_disable_reenable_dispatch_and_companion_policy(plugin_dirs, tmp_path):
    source = _write_python_plugin(tmp_path / "source")
    installed = plugins.install_plugin_file(source)
    companion = plugin_dirs / "sun_moon_hot_takes.json"
    assert installed.exists() and companion.exists()
    assert plugins.chart_info_plugin_paragraphs({}) == [[{"text": "ok"}]]

    revision = plugins.plugin_revision()
    plugins.set_plugin_enabled(source.name, False)
    assert plugins.plugin_revision() == revision + 1
    assert plugins.chart_info_plugin_paragraphs({}) == []
    # The primary file alone controls state; inert companion data stays put.
    assert companion.exists()

    plugins.set_plugin_enabled(source.name, True)
    assert plugins.chart_info_plugin_paragraphs({}) == [[{"text": "ok"}]]


@pytest.mark.parametrize(
    ("manifest", "message"),
    [
        ({"api_version": 2, "name": "x", "hooks": ["chart_info"]}, "Unsupported"),
        ({"api_version": 1, "name": "x", "hooks": []}, "at least one hook"),
        (
            {"api_version": 1, "name": "x", "hooks": ["chart_info"], "data_files": ["../x"]},
            "sibling filenames",
        ),
        (
            {"api_version": 1, "name": "x", "hooks": ["chart_info"], "data_files": ["missing.json"]},
            "is missing",
        ),
    ],
)
def test_manifest_validation_rejects_invalid_contracts(tmp_path, manifest, message):
    path = tmp_path / "sun-moon_hot-takes.py"
    path.write_text(f"PLUGIN_MANIFEST = {manifest!r}\n", encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        plugins.validate_plugin_file(path)


def test_manifest_validation_is_literal_and_does_not_execute(tmp_path):
    marker = tmp_path / "executed"
    path = tmp_path / "sun-moon_hot-takes.py"
    path.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n"
        "PLUGIN_MANIFEST = dict(api_version=1)\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="literal dictionary"):
        plugins.validate_plugin_file(path)
    assert not marker.exists()


def test_unregistered_python_is_rejected(tmp_path):
    path = tmp_path / "other.py"
    path.write_text("PLUGIN_MANIFEST = {'api_version': 1, 'name': 'x', 'hooks': ['chart_info']}\n")
    with pytest.raises(ValueError, match="not recognized"):
        plugins.validate_plugin_file(path)


@pytest.mark.parametrize("body", ["raise RuntimeError('broken')", "return 'malformed'"])
def test_hook_failures_are_isolated(plugin_dirs, tmp_path, body):
    plugins.install_plugin_file(_write_python_plugin(tmp_path / "source", body=body))
    assert plugins.chart_info_plugin_paragraphs({}) == []


def test_import_failure_is_isolated(plugin_dirs):
    plugin_dirs.mkdir(parents=True)
    path = plugin_dirs / "sun-moon_hot-takes.py"
    path.write_text(
        "PLUGIN_MANIFEST = {'api_version': 1, 'name': 'x', 'hooks': ['chart_info']}\n"
        "raise LookupError('broken import')\n",
        encoding="utf-8",
    )
    plugins.invalidate_plugin_caches()
    assert plugins.chart_info_plugin_paragraphs({}) == []
