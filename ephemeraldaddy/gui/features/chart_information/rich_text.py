"""Window-independent rich-text documents for Chart Information presenters."""

from __future__ import annotations

from dataclasses import dataclass

from ephemeraldaddy.core.interpretations import MODE_COLORS, PLANET_COLORS
from ephemeraldaddy.gui.features.chart_information.keyword_models import (
    DecanInformationModel,
    ModeKeywordModel,
)

DEFAULT_TEXT_COLOR = "#f5f5f5"


@dataclass(frozen=True, slots=True)
class RichTextStyle:
    """Toolkit-neutral formatting for one run of Chart Information text."""

    color: str | None = None
    bold: bool = False
    italic: bool = False
    point_size: float | None = None


@dataclass(frozen=True, slots=True)
class RichTextRun:
    text: str
    style: RichTextStyle = RichTextStyle()


@dataclass(frozen=True, slots=True)
class ChartInformationDocument:
    runs: tuple[RichTextRun, ...]


def build_decan_document(
    decan: DecanInformationModel,
    *,
    body_name: str,
    display_body: str,
    default_text_color: str = DEFAULT_TEXT_COLOR,
) -> ChartInformationDocument:
    """Build the styled title, description, and keywords for one decan."""
    runs = [
        RichTextRun(
            f"{display_body}: {decan.ordinal_label} decan of {decan.sign_name}\n\n",
            RichTextStyle(
                color=PLANET_COLORS.get(body_name, default_text_color),
                bold=True,
            ),
        )
    ]
    if decan.description:
        runs.append(
            RichTextRun(
                f"{decan.description}\n\n",
                RichTextStyle(
                    color=PLANET_COLORS.get(decan.subsign_ruler, default_text_color),
                    italic=True,
                ),
            )
        )
    plain = RichTextStyle()
    runs.extend(RichTextRun(f"• {keyword}\n", plain) for keyword in decan.keywords)
    return ChartInformationDocument(tuple(runs))


def build_mode_document(
    mode: ModeKeywordModel,
    *,
    highlight_color: str,
    default_text_color: str = DEFAULT_TEXT_COLOR,
) -> ChartInformationDocument:
    """Build the styled keyword and sign sections for one astrological mode."""
    title = RichTextStyle(
        color=MODE_COLORS.get(mode.key, default_text_color),
        bold=True,
        point_size=13,
    )
    header = RichTextStyle(color=highlight_color, bold=True)
    plain = RichTextStyle()
    runs = [RichTextRun(f"{mode.label} Mode\n\n", title)]
    if mode.keywords:
        runs.extend(
            [RichTextRun("Keywords:\n", header)]
            + [RichTextRun(f"• {keyword}\n", plain) for keyword in mode.keywords]
        )
    if mode.signs:
        if mode.keywords:
            runs.append(RichTextRun("\n", plain))
        runs.extend(
            [RichTextRun("Signs:\n", header)]
            + [RichTextRun(f"• {sign}\n", plain) for sign in mode.signs]
        )
    return ChartInformationDocument(tuple(runs))
