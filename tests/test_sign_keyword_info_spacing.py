from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_sign_placement_list_has_two_line_breaks_before_keyword_sections():
    source = (REPO_ROOT / "ephemeraldaddy/gui/app.py").read_text()
    method_start = source.index("    def _show_sign_keyword_info(")
    method_end = source.index("    def _show_element_keyword_info(", method_start)
    method_source = source[method_start:method_end]

    placement_loop = method_source.index("                for segment_text, segment_color")
    at_best_section = method_source.index('            cursor.insertText("At Best:", header_fmt)')

    assert '                cursor.insertText("\\n\\n", plain_fmt)' in method_source[
        placement_loop:at_best_section
    ]
