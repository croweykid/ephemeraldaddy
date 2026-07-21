from pathlib import Path


SOURCE_PATH = Path("ephemeraldaddy/gui/window_chrome.py")


def test_ephemeral_daddy_menu_has_settings_in_both_window_chrome_builders():
    source = SOURCE_PATH.read_text()

    main_start = source.index("def configure_main_window_chrome")
    manage_start = source.index("def configure_manage_dialog_chrome")
    main_source = source[main_start:manage_start]
    manage_source = source[manage_start:]

    assert 'app_menu = menu_bar.addMenu(APP_DISPLAY_NAME)' in main_source
    assert '_add_settings_action(app_menu, window)' in main_source
    assert 'app_menu = menu_bar.addMenu(APP_DISPLAY_NAME)' in manage_source
    assert '_add_settings_action(app_menu, dialog)' in manage_source


def test_settings_menu_action_can_resolve_database_view_owner_handlers():
    source = SOURCE_PATH.read_text()
    resolver_start = source.index("def _resolve_menu_handler")
    binder_start = source.index("def _keep_action_in_window_menu", resolver_start)
    resolver_source = source[resolver_start:binder_start]

    assert 'getattr(window, "_app_owner", None)' in resolver_source
    assert 'getattr(window, "_owner_window", None)' in resolver_source
    assert '"_on_open_settings", "on_open_settings"' in source


def test_settings_is_direct_action_not_preferences_submenu():
    source = SOURCE_PATH.read_text()
    helper_start = source.index("def _add_settings_action")
    helper_end = source.index("def _configure_menu_bar_visibility", helper_start)
    helper_source = source[helper_start:helper_end]

    assert '_bind_menu_action(app_menu, "Settings", owner' in helper_source
    assert 'addMenu("Preferences")' not in source


def test_terminal_macos_uses_in_window_menubar_by_default():
    source = SOURCE_PATH.read_text()
    visibility_start = source.index("def _configure_menu_bar_visibility")
    visibility_end = source.index("def _is_human_design_menu_enabled", visibility_start)
    visibility_source = source[visibility_start:visibility_end]

    assert 'sys.platform == "darwin"' in visibility_source
    assert 'EPHEMERALDADDY_USE_NATIVE_MENUBAR' in visibility_source
    assert 'menu_bar.setNativeMenuBar(False)' in visibility_source


def test_window_chrome_actions_disable_qt_macos_menu_relocation_roles():
    source = SOURCE_PATH.read_text()
    keep_start = source.index("def _keep_action_in_window_menu")
    bind_start = source.index("def _bind_menu_action", keep_start)
    keep_source = source[keep_start:bind_start]

    assert 'setMenuRole' in keep_source
    assert 'NoRole' in keep_source
    assert '_keep_action_in_window_menu(action)' in source
