from pathlib import Path


APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text(encoding="utf-8")
CONTROLLER_SOURCE = Path(
    "ephemeraldaddy/gui/features/import_export/web_profile_controller.py"
).read_text(encoding="utf-8")


def test_app_delegates_wikipedia_fallback_orchestration():
    method_start = APP_SOURCE.index("def _on_import_astrotheme_from_search_panel")
    method_end = APP_SOURCE.index("def _on_get_bio_for_open_chart", method_start)
    import_method = APP_SOURCE[method_start:method_end]

    assert "resolve_wikipedia_import(" in import_method
    assert "resolve_wikipedia_page_options(" not in import_method
    assert "parse_wikipedia_birth_data(" not in import_method
    assert "confirm_manual_wikipedia_import(" not in import_method


def test_controller_owns_wikipedia_fallback_steps():
    assert "def resolve_wikipedia_import(" in CONTROLLER_SOURCE
    assert "resolve_wikipedia_page_options(raw_query)" in CONTROLLER_SOURCE
    assert "parse_wikipedia_birth_data(selected_title)" in CONTROLLER_SOURCE
    assert "confirm_manual_wikipedia_import(parent, selected_title)" in CONTROLLER_SOURCE
