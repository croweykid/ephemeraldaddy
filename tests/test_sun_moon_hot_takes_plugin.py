import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "docs/sun-moon_hot-takes.py"
DATA_PATH = ROOT / "docs/sun_moon_hot_takes.json"


def _load_plugin(path=PLUGIN_PATH):
    spec = importlib.util.spec_from_file_location("sun_moon_hot_takes_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _context(body="Sun", signs=None):
    return {
        "target": "position",
        "body": body,
        "chart_signs": signs if signs is not None else {"Sun": "Aries", "Moon": "Aries"},
    }


def test_plugin_filters_irrelevant_or_incomplete_contexts():
    plugin = _load_plugin()
    assert plugin.chart_info({"target": "aspect"}) == []
    assert plugin.chart_info(_context("Mars")) == []
    assert plugin.chart_info(_context(signs={})) == []
    assert plugin.chart_info(_context(signs={"Sun": "Aries"})) == []


def test_case_insensitive_sign_keys_and_exact_source_strings():
    plugin = _load_plugin()
    source = json.loads(DATA_PATH.read_text(encoding="utf-8"))["aries"]["aries"]
    paragraphs = plugin.chart_info(_context(signs={"sUN": "ARIES", "mOoN": "aries"}))
    assert paragraphs[0][0] == {
        "text": "Sun-Moon Hot Takes:",
        "bold": True,
        "color_role": "highlight",
    }
    assert paragraphs[0][2] == {"text": source["average"], "italic": True}
    assert paragraphs[1] == [{"text": "Best case: ", "bold": True}, {"text": source["best_case"]}]
    assert paragraphs[2] == [{"text": "Worst case: ", "bold": True}, {"text": source["worst_case"]}]
    assert plugin.chart_info(_context("Moon")) == plugin.chart_info(_context("Sun"))


@pytest.mark.parametrize(
    ("missing", "forbidden"),
    [("average", None), ("best_case", "Best case: "), ("worst_case", "Worst case: ")],
)
def test_null_fields_are_omitted(tmp_path, missing, forbidden):
    plugin_path = tmp_path / PLUGIN_PATH.name
    plugin_path.write_text(PLUGIN_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    entry = {"average": "average", "best_case": "best", "worst_case": "worst"}
    entry[missing] = None
    (tmp_path / "sun_moon_hot_takes.json").write_text(
        json.dumps({"aries": {"aries": entry}}), encoding="utf-8"
    )
    rendered = _load_plugin(plugin_path).chart_info(_context())
    text = "".join(segment["text"] for paragraph in rendered for segment in paragraph)
    if missing == "average":
        assert "average" not in text
    else:
        assert forbidden not in text


def test_missing_or_invalid_json_fails_closed(tmp_path):
    plugin_path = tmp_path / PLUGIN_PATH.name
    plugin_path.write_text(PLUGIN_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    plugin = _load_plugin(plugin_path)
    assert plugin.chart_info(_context()) == []
    (tmp_path / "sun_moon_hot_takes.json").write_text("not json", encoding="utf-8")
    plugin = _load_plugin(plugin_path)
    assert plugin.chart_info(_context()) == []


def test_json_payload_is_cached(monkeypatch):
    plugin = _load_plugin()
    calls = 0
    original_open = Path.open

    def counting_open(path, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", counting_open)
    plugin.chart_info(_context())
    plugin.chart_info(_context("Moon"))
    assert calls == 1
