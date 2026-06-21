from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = REPO_ROOT / "ephemeraldaddy/gui/app.py"


def _method_source(name: str, *, end: str | None = None) -> str:
    source = APP_SOURCE.read_text()
    start = source.index(f"    def {name}")
    if end is None:
        end = "\n    def "
        stop = source.index(end, start + 1)
    else:
        stop = source.index(f"    def {end}", start)
    return source[start:stop]


def test_database_row_rectified_time_uses_saved_retcon_hour_and_minute():
    source = APP_SOURCE.read_text()
    row_start = source.index("display_name = name or \"Unnamed\"")
    row_block = source[row_start : source.index("place = birth_place or \"\"", row_start)]

    assert "retcon_hour = int(_retcon_hour)" in row_block
    assert "retcon_minute = int(_retcon_minute)" in row_block
    assert 'retcon_time_value = f"{retcon_hour:02d}:{retcon_minute:02d}"' in row_block
    assert 'retcon_time_label = f"({retcon_time_value})" if retcon_time_value else ""' in row_block


def test_database_row_rectified_time_does_not_only_reformat_birth_datetime():
    source = APP_SOURCE.read_text()
    row_start = source.index("display_name = name or \"Unnamed\"")
    row_block = source[row_start : source.index("place = birth_place or \"\"", row_start)]

    assert row_block.count("format_chart_row_datetime(") == 2
    assert row_block.index("retcon_hour = int(_retcon_hour)") < row_block.index(
        "fallback_retcon_time_value = format_chart_row_datetime("
    )
    assert "has_known_retcon_time" not in row_block


def test_retcon_time_change_marks_lucygoosey_before_autosave():
    method = _method_source("_on_retcon_time_changed", end="_update_time_input_visibility")

    mark_index = method.index("self._mark_lucygoosey()")
    autosave_index = method.index("self._autosave_checkbox_state()")
    assert mark_index < autosave_index
    assert "should_refresh_retcon_preview" in method
    assert "self.retcon_time_checkbox.isChecked()" in method
