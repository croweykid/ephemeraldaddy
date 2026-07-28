from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")


def test_birth_date_inputs_are_bottom_aligned_with_rectified_time() -> None:
    for field_name in ("birth_month_edit", "birth_day_edit", "birth_year_edit"):
        assert (
            f"birth_time_row.addWidget(self.{field_name}, 0, Qt.AlignBottom)"
            in APP_SOURCE
        )


def test_birth_date_inputs_do_not_use_stacked_caption_containers() -> None:
    assert "_labeled_birth_date_field" not in APP_SOURCE
