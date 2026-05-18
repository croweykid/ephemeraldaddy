from ephemeraldaddy.gui.features.charts.similarities_layout import (
    SIMILARITIES_EXPANDED_MAX_HEIGHT_PROPERTY,
    bounded_similarity_section_height,
    configure_similarity_section_list_height,
    resize_similarity_section_to_contents,
)


class _Size:
    def __init__(self, height: int):
        self._height = height

    def height(self) -> int:
        return self._height


class _Item:
    def __init__(self, height: int):
        self._height = height

    def sizeHint(self) -> _Size:
        return _Size(self._height)


class _SectionList:
    def __init__(
        self, row_heights: list[int], fallback_heights: list[int] | None = None
    ):
        self._items = [_Item(height) for height in row_heights]
        self._fallback_heights = fallback_heights or []
        self._properties: dict[str, int] = {}
        self.fixed_height: int | None = None

    def setProperty(self, key: str, value: int) -> None:
        self._properties[key] = value

    def property(self, key: str) -> int | None:
        return self._properties.get(key)

    def setFixedHeight(self, height: int) -> None:
        self.fixed_height = height

    def count(self) -> int:
        return len(self._items)

    def item(self, index: int) -> _Item:
        return self._items[index]

    def sizeHintForRow(self, index: int) -> int:
        if index < len(self._fallback_heights):
            return self._fallback_heights[index]
        return -1

    def frameWidth(self) -> int:
        return 1


def test_similarity_section_height_shrinks_to_rendered_rows():
    assert bounded_similarity_section_height([34], 100, frame_padding=4) == 38


def test_similarity_section_height_caps_at_configured_expanded_height():
    assert bounded_similarity_section_height([34, 34, 34, 34], 100, frame_padding=4) == 100


def test_similarity_section_height_returns_zero_without_rows():
    assert bounded_similarity_section_height([], 100, frame_padding=4) == 0


def test_configure_similarity_section_list_height_stores_cap_and_applies_initial_height():
    section_list = _SectionList([])

    configure_similarity_section_list_height(section_list, 100)

    assert section_list.property(SIMILARITIES_EXPANDED_MAX_HEIGHT_PROPERTY) == 100
    assert section_list.fixed_height == 100


def test_resize_similarity_section_to_contents_uses_widget_rows_and_cap():
    section_list = _SectionList([34])
    configure_similarity_section_list_height(section_list, 100)

    resized_height = resize_similarity_section_to_contents(section_list)

    assert resized_height == 38
    assert section_list.fixed_height == 38
