"""Explicit controller boundary for single-chart Markdown exports."""

from __future__ import annotations

import datetime
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ephemeraldaddy.gui.features.import_export.chart_markdown import (
    build_chart_export_markdown,
)

ChooseDestination = Callable[[str, str, str], str]
ShowMessage = Callable[[str, str], None]
RenderMarkdown = Callable[[object], str]
WriteText = Callable[[str, str], None]


@dataclass(frozen=True, slots=True)
class ChartMarkdownExportCallbacks:
    """Narrow UI and persistence ports required by the export workflow."""

    choose_destination: ChooseDestination
    show_information: ShowMessage
    show_error: ShowMessage


class ChartMarkdownExportController:
    """Coordinate one Markdown export without depending on a Qt window."""

    def __init__(
        self,
        callbacks: ChartMarkdownExportCallbacks,
        *,
        render_markdown: RenderMarkdown = build_chart_export_markdown,
        write_text: WriteText | None = None,
        today: Callable[[], datetime.date] = datetime.date.today,
    ) -> None:
        self._callbacks = callbacks
        self._render_markdown = render_markdown
        self._write_text = write_text or _write_utf8_text
        self._today = today

    def export(self, chart: object | None) -> bool:
        """Prompt for a destination and export ``chart``; return whether it saved."""
        if chart is None:
            self._callbacks.show_information(
                "incomplete birthdate",
                "Generate or load a chart before exporting.",
            )
            return False

        default_filename = self.default_filename(chart)
        destination = self._callbacks.choose_destination(
            "Export chart analysis (MD)",
            default_filename,
            "Markdown Files (*.md)",
        )
        if not destination:
            return False
        if not destination.lower().endswith(".md"):
            destination = f"{destination}.md"

        try:
            self._write_text(destination, self._render_markdown(chart))
        except Exception as exc:
            self._callbacks.show_error(
                "Export failed",
                f"Could not export chart markdown:\n{exc}",
            )
            return False

        self._callbacks.show_information(
            "Export complete",
            f"Saved chart markdown to:\n{destination}",
        )
        return True

    def default_filename(self, chart: object) -> str:
        """Return the stable, filesystem-safe default filename for a chart."""
        chart_title = (getattr(chart, "name", None) or "chart").strip() or "chart"
        safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", chart_title).strip("_")
        return (
            f"ephemeraldaddy_{safe_title or 'birthchart'}_chart-"
            f"{self._today().isoformat()}.md"
        )


def _write_utf8_text(file_path: str, content: str) -> None:
    Path(file_path).write_text(content, encoding="utf-8")
