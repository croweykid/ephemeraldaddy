from pathlib import Path


def test_trait_prediction_color_delegate_uses_qpalette_color_role():
    source = Path("ephemeraldaddy/gui/features/charts/trait_predictions.py").read_text(encoding="utf-8")

    assert "from PySide6.QtGui import QColor, QPalette" in source
    assert "option.palette.setColor(QPalette.ColorRole.Text, color)" in source
    assert "option.palette.setColor(option.palette.Text, color)" not in source
