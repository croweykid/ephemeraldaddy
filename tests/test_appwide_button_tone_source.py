from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_style_defines_universal_affirmative_and_negation_button_tones():
    source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()

    assert 'APPWIDE_AFFIRMATIVE_BUTTON_TONE = "affirmative"' in source
    assert 'APPWIDE_NEGATION_BUTTON_TONE = "negation"' in source
    assert 'APPWIDE_AFFIRMATIVE_BUTTON_BACKGROUND_COLOR = "#7b2cbf"' in source
    assert 'APPWIDE_NEGATION_BUTTON_BACKGROUND_COLOR = "#4a4d57"' in source
    assert '"okay"' in source
    assert '"cool"' in source
    assert '"affirmative"' in source
    assert '"cancel"' in source
    assert 'QPushButton[eddButtonTone="{APPWIDE_AFFIRMATIVE_BUTTON_TONE}"]' in source
    assert 'QPushButton[eddButtonTone="{APPWIDE_NEGATION_BUTTON_TONE}"]' in source


def test_appwide_button_filter_tags_common_dialog_buttons():
    source = (REPO_ROOT / "ephemeraldaddy/gui/style.py").read_text()

    assert 'def apply_appwide_button_tone' in source
    assert 'tone_property = tone or ""' in source
    assert 'button.setProperty("eddButtonTone", tone_property)' in source
    assert 'apply_appwide_button_tone(obj)' in source
    assert 'apply_appwide_button_tone(child)' in source
