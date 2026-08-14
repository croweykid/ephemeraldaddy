from importlib import resources
from pathlib import Path

from ephemeraldaddy.gui.features.popouts.synastry_conversation import (
    load_synastry_conversation,
    passage_html,
)


def test_bundled_synastry_twine_conversation_is_loadable() -> None:
    start_name, passages = load_synastry_conversation()

    assert start_name == "Untitled Passage"
    assert "What is Synastry?" in passages[start_name]
    assert "Synastry Definition" in passages
    assert len(passages) > 10


def test_packaged_story_matches_the_editable_twine_export() -> None:
    packaged_story = (
        resources.files("ephemeraldaddy.gui.features.popouts")
        .joinpath("assets", "what_is_synastry.html")
        .read_text(encoding="utf-8")
    )
    repository_story = (
        Path(__file__).resolve().parents[1] / "docs" / "what is synastry.html"
    ).read_text(encoding="utf-8")

    assert packaged_story == repository_story


def test_passage_renderer_preserves_nonlinear_links_and_lists() -> None:
    rendered = passage_html("''Choose:''\n* One\n* [[Two->Next Passage]]")

    assert "<strong>Choose:</strong>" in rendered
    assert "<ul>" in rendered
    assert 'href="twine:Next%20Passage"' in rendered
    assert ">Two</a>" in rendered


def test_loader_rejects_html_without_twine_passages(tmp_path: Path) -> None:
    source = tmp_path / "empty.html"
    source.write_text("<html><body>Nothing here</body></html>", encoding="utf-8")

    try:
        load_synastry_conversation(source)
    except ValueError as error:
        assert "No Twine passages found" in str(error)
    else:
        raise AssertionError("Expected invalid Twine HTML to be rejected")
