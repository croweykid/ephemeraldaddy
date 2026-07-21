from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
QUAD_STATE_SOURCE = (REPO_ROOT / "ephemeraldaddy/gui/widgets/quad_state.py").read_text(encoding="utf-8")


def test_quad_state_slider_paints_indicator_manually_to_clear_stale_exclusion_glyphs():
    indicator_class = QUAD_STATE_SOURCE.split("class _QuadStateIndicatorButton", 1)[1].split(
        "class QuadStateSlider", 1
    )[0]
    render_method = QUAD_STATE_SOURCE.split("def _render_mode", 1)[1]
    assert "painter.fillRect" in indicator_class
    assert "drawText" in indicator_class
    assert 'self._button.setText("")' in render_method
    assert "red exclusion X" in render_method
