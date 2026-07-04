from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_chart_info_ambiguous_short_tokens_require_uppercase_word_matches():
    source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()

    assert 'uppercase_word_only_tokens = {"AS", "IC", "G"}' in source
    assert "if token in uppercase_word_only_tokens" in source
    assert "if token and token not in uppercase_word_only_tokens" in source
    assert 'rf"(?<!\\w)(?:{\'|\'.join(strict_pattern_parts)})(?!\\w)"' in source
    assert "pattern = re.compile(" in source
    assert "color_by_exact = {token: color for token, color in tokens}" in source
    assert "elif raw in uppercase_word_only_tokens:" in source
    assert "color = color_by_exact.get(raw)" in source
