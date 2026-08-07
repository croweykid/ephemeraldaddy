import inspect

from ephemeraldaddy.gui import dbv_search_panel


def test_session_catalog_refresh_updates_material_relative_completer():
    source = inspect.getsource(dbv_search_panel.update_tag_completers)

    assert '"_update_material_relatives_completer", None' in source
    assert "update_material_relatives_completer()" in source
