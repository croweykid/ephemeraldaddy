from pathlib import Path

APP_SOURCE = Path("ephemeraldaddy/gui/app.py").read_text()


def test_reset_new_chart_form_clears_time_sensitivity_render_token_before_refresh():
    method = APP_SOURCE.split("    def _reset_new_chart_form", 1)[1].split("    def ", 1)[0]
    token_clear = 'self._time_sensitivity_last_refresh_token = None'
    refresh_call = 'time_sensitivity_panel.refresh_for_current_chart()'

    assert token_clear in method
    assert refresh_call in method
    assert method.index(token_clear) < method.index(refresh_call)
