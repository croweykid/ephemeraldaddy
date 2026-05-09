from ephemeraldaddy.gui.features.charts import anagram_engine


def test_fallback_dictionary_keeps_anagrams_available_without_os_words(monkeypatch):
    def missing_open(*args, **kwargs):
        raise OSError("no dictionary installed")

    anagram_engine.anagram_dictionary_words.cache_clear()
    monkeypatch.setattr(anagram_engine, "open", missing_open, raising=False)

    try:
        words = anagram_engine.collect_anagram_words("Listen", max_results=10)
    finally:
        anagram_engine.anagram_dictionary_words.cache_clear()

    assert "listen" in words
    assert "silent" in words


def test_collect_anagram_words_strips_non_letters_and_sorts_longest_first():
    words = anagram_engine.collect_anagram_words("Chart!!!", max_results=10)

    assert words[:2] == ["chart", "arch"]
    assert "art" in words


def test_render_anagrams_text_reports_dictionary_matches_for_long_names(monkeypatch):
    monkeypatch.setattr(
        anagram_engine,
        "collect_chart_name_anagrams",
        lambda _chart_name, max_results=30: ["listen", "silent"],
    )

    rendered = anagram_engine.render_anagrams_text("Listen")

    assert 'Chart name: "Listen"' in rendered
    assert "listen, silent" in rendered
