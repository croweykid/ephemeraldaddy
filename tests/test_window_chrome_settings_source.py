from pathlib import Path


SOURCE_PATH = Path("ephemeraldaddy/gui/window_chrome.py")


def test_ephemeral_daddy_menu_has_settings_in_both_window_chrome_builders():
    source = SOURCE_PATH.read_text()

    main_start = source.index("def configure_main_window_chrome")
    manage_start = source.index("def configure_manage_dialog_chrome")
    main_source = source[main_start:manage_start]
    manage_source = source[manage_start:]

    assert 'app_menu = menu_bar.addMenu(APP_DISPLAY_NAME)' in main_source
    assert '_bind_settings_menu_action(app_menu, window)' in main_source
    assert 'app_menu = menu_bar.addMenu(APP_DISPLAY_NAME)' in manage_source
    assert '_bind_settings_menu_action(app_menu, dialog)' in manage_source


def test_settings_menu_action_can_resolve_database_view_owner_handlers():
    source = SOURCE_PATH.read_text()
    resolver_start = source.index("def _resolve_menu_handler")
    binder_start = source.index("def _bind_menu_action", resolver_start)
    resolver_source = source[resolver_start:binder_start]

    assert 'getattr(window, "_app_owner", None)' in resolver_source
    assert 'getattr(window, "_owner_window", None)' in resolver_source
    assert '"_on_open_settings", "on_open_settings"' in source
