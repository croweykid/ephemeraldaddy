from ephemeraldaddy.gui.features.chart_information.keyword_models import (
    DecanInformationModel,
    ModeKeywordModel,
)
from ephemeraldaddy.gui.features.chart_information.rich_text import (
    build_decan_document,
    build_mode_document,
)


def test_decan_document_preserves_title_description_and_keyword_styles():
    decan = DecanInformationModel(
        sign_name="Aries",
        decan_number=1,
        ordinal_label="1st",
        subsign_ruler="Mars",
        description="The opening fire.",
        keywords=("initiative", "courage"),
    )

    document = build_decan_document(
        decan,
        body_name="Sun",
        display_body="☉ Sun",
    )

    assert document.runs[0].text == "☉ Sun: 1st decan of Aries\n\n"
    assert document.runs[0].style.bold
    assert document.runs[1].text == "The opening fire.\n\n"
    assert document.runs[1].style.italic
    assert [run.text for run in document.runs[2:]] == [
        "• initiative\n",
        "• courage\n",
    ]


def test_mode_document_preserves_section_order_and_styles():
    mode = ModeKeywordModel(
        key="cardinal",
        label="Cardinal",
        keywords=("initiating", "direct"),
        signs=("Aries", "Cancer"),
    )

    document = build_mode_document(mode, highlight_color="#123456")

    assert document.runs[0].text == "Cardinal Mode\n\n"
    assert document.runs[0].style.bold
    assert document.runs[0].style.point_size == 13
    assert [run.text for run in document.runs] == [
        "Cardinal Mode\n\n",
        "Keywords:\n",
        "• initiating\n",
        "• direct\n",
        "\n",
        "Signs:\n",
        "• Aries\n",
        "• Cancer\n",
    ]
    assert document.runs[1].style.color == "#123456"
    assert document.runs[5].style.color == "#123456"
