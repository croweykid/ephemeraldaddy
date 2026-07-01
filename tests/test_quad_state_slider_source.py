from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def test_quad_state_slider_empty_state_paints_nonempty_blank_text():
    render_method = APP_SOURCE.split("def _render_mode", 1)[1].split(
        "class AlignmentEmojiSlider", 1
    )[0]
    assert 'visual["text"] or " "' in render_method
    assert "red exclusion mark" in render_method
