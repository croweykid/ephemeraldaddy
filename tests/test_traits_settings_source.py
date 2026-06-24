from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_traits_settings_ui_lives_outside_app_py():
    app_source = (ROOT / "ephemeraldaddy" / "gui" / "app.py").read_text(encoding="utf-8")
    settings_source = (ROOT / "ephemeraldaddy" / "gui" / "features" / "settings" / "traits.py").read_text(
        encoding="utf-8"
    )

    assert "add_traits_settings_section(self, content_layout)" in app_source
    assert "def _on_trait_upload_clicked" not in app_source
    assert "def add_traits_settings_section" in settings_source
    assert "def on_trait_upload_clicked" in settings_source


def test_trait_prediction_rendering_lives_outside_app_py():
    app_source = (ROOT / "ephemeraldaddy" / "gui" / "app.py").read_text(encoding="utf-8")
    predictions_source = (
        ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "trait_predictions.py"
    ).read_text(encoding="utf-8")

    assert "def _render_traits_predictions" in app_source
    assert "_render_traits_predictions(self, chart)" in app_source
    assert "def render_traits_predictions" in predictions_source
    assert "calculate_trait_scores" in predictions_source
