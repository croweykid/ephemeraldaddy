from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "ephemeraldaddy/gui/features/charts/database_analytics.py").read_text(
    encoding="utf-8"
)


def test_trait_rankings_dropdown_defaults_to_inert_prompt():
    assert 'combo.addItem("select a trait!", "")' in SOURCE
    assert 'selected_index = combo.findData(current_name) if current_name else 0' in SOURCE
    assert 'self._traits_distribution_rank_trait_name = ""' in SOURCE


def test_trait_rankings_prompt_skips_database_warm_until_trait_selected():
    render_method = SOURCE[
        SOURCE.index("    def _render_traits_distribution_section")
        : SOURCE.index("    def _render_enneagram_database_analytics")
    ]
    inert_branch = render_method[
        render_method.index('        if rankings_mode and not selected_trait_name:')
        : render_method.index('        database_analytics = self._collect_traits_distribution_analytics')
    ]

    assert '"selected_trait_name": ""' in inert_branch
    assert 'self._clear_layout(chart_layout)' in inert_branch
    assert 'self._analysis_chart_export_rows["traits_distribution"] = []' in inert_branch
    assert "_render_traits_distribution_rankings_html(" in inert_branch
    assert "return" in inert_branch
    assert "_collect_traits_distribution_analytics" not in inert_branch
    assert "Select a trait from the dropdown above" in SOURCE
