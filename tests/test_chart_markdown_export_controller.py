import datetime
from types import SimpleNamespace

from ephemeraldaddy.gui.features.import_export.chart_markdown_controller import (
    ChartMarkdownExportCallbacks,
    ChartMarkdownExportController,
)


class Recorder:
    def __init__(self, destination: str = "") -> None:
        self.destination = destination
        self.information: list[tuple[str, str]] = []
        self.errors: list[tuple[str, str]] = []
        self.writes: list[tuple[str, str]] = []

    def callbacks(self) -> ChartMarkdownExportCallbacks:
        return ChartMarkdownExportCallbacks(
            choose_destination=lambda _title, _default, _filter: self.destination,
            show_information=lambda title, message: self.information.append(
                (title, message)
            ),
            show_error=lambda title, message: self.errors.append((title, message)),
        )


def _controller(recorder: Recorder) -> ChartMarkdownExportController:
    return ChartMarkdownExportController(
        recorder.callbacks(),
        render_markdown=lambda chart: f"# {chart.name}",
        write_text=lambda path, text: recorder.writes.append((path, text)),
        today=lambda: datetime.date(2026, 9, 11),
    )


def test_export_adds_markdown_suffix_and_reports_success():
    recorder = Recorder("/tmp/Ada chart")

    exported = _controller(recorder).export(SimpleNamespace(name="Ada"))

    assert exported
    assert recorder.writes == [("/tmp/Ada chart.md", "# Ada")]
    assert recorder.information == [
        ("Export complete", "Saved chart markdown to:\n/tmp/Ada chart.md")
    ]
    assert not recorder.errors


def test_export_without_chart_reports_existing_guidance():
    recorder = Recorder("/tmp/unused.md")

    exported = _controller(recorder).export(None)

    assert not exported
    assert not recorder.writes
    assert recorder.information == [
        ("incomplete birthdate", "Generate or load a chart before exporting.")
    ]


def test_cancelled_export_has_no_side_effects():
    recorder = Recorder("")

    exported = _controller(recorder).export(SimpleNamespace(name="Ada"))

    assert not exported
    assert not recorder.writes
    assert not recorder.information
    assert not recorder.errors


def test_export_failure_is_reported_and_not_marked_successful():
    recorder = Recorder("/tmp/chart.md")
    controller = ChartMarkdownExportController(
        recorder.callbacks(),
        render_markdown=lambda _chart: "content",
        write_text=lambda _path, _text: (_ for _ in ()).throw(OSError("disk full")),
    )

    exported = controller.export(SimpleNamespace(name="Ada"))

    assert not exported
    assert recorder.errors == [
        ("Export failed", "Could not export chart markdown:\ndisk full")
    ]
    assert not recorder.information


def test_default_filename_is_safe_and_date_stamped():
    recorder = Recorder()

    filename = _controller(recorder).default_filename(
        SimpleNamespace(name="  Ada Lovelace / Notes  ")
    )

    assert filename == "ephemeraldaddy_Ada_Lovelace_Notes_chart-2026-09-11.md"
