# Source-contract drift candidates — 2026-08-14 pytest run

## Purpose

This is the review queue requested after examining
`tests/results/test-runs/pytest-20260814T143420Z.xml`. It contains failures in
tests that inspect Python source text, method bodies, labels, or code placement
rather than exercising the behavior through a public interface.

These are **candidates**, not presumed bad tests. For each item we should decide
whether:

1. the implementation lost required behavior (**application regression**);
2. the behavior survived but moved or was equivalently rewritten (**test drift**);
3. the contract is still wanted, but should be covered behaviorally
   (**replace brittle source assertion**); or
4. an in-progress feature was committed only on the test side (**incomplete
   implementation**).

The backup test whose name ends in `custom_charts_source` is deliberately not
included: it is a behavioral test and its failure was the Windows SQLite handle
issue fixed separately. The historical `semantics_formating` failure is also
excluded because it was an import compatibility failure, not a source-contract
assertion, and its typo correction is being handled separately.

## 1. Chart View and Predictions (13)

- [ ] `test_chart_view_right_panel_layout_source::test_dnd_prediction_summary_is_added_after_metric_panel_render_clears_layout`
  - Expected ordering markers could not be found after prediction rendering was reorganized.
- [ ] `test_chart_view_right_panel_layout_source::test_property_managers_button_sits_below_settings_sections_with_padding`
  - Expected app.py placement markers could not be found; likely extraction versus lost layout contract.
- [ ] `test_chart_view_right_panel_layout_source::test_dnd_alignment_popout_is_registered_and_configured`
  - Expected “Official Fantasy RPG alignment” popout registration/configuration text is absent.
- [ ] `test_chart_view_right_panel_layout_source::test_predictions_sections_show_calculate_prompt_instead_of_auto_calculating`
  - Expected manual “No prior data. Calculate…” prompt is absent from the inspected module.
- [ ] `test_chart_view_right_panel_layout_source::test_traits_predictions_default_to_manual_recalculation_with_cached_stale_display`
  - Expected manual-recalculation prompt/stale-display contract is absent.
- [ ] `test_chart_view_right_panel_layout_source::test_traits_prediction_prompt_label_is_reshown_after_table_results`
  - Expected explanatory source marker for a later uncached chart is absent.
- [ ] `test_chart_view_right_panel_layout_source::test_predictions_panel_rerenders_traits_for_each_chart_even_when_content_exists`
  - Expected unconditional per-chart traits render call has changed.
- [ ] `test_chart_view_right_panel_layout_source::test_prediction_calculate_prompts_expand_and_center_contents`
  - Expected expanding size-policy source expression is absent.
- [ ] `test_chart_view_save_integrity_regression_source::test_subjective_only_save_uses_lightweight_update_and_preserves_calculated_payloads`
  - Expected explicit recalculation versus lightweight-update branch has been rewritten or lost.
- [ ] `test_chart_view_session_completers_source::test_chart_view_tag_completers_preserve_session_tags_before_save`
  - Wrapper method no longer contains the expected `list_recognized_tags()` call; likely delegated behavior.
- [ ] `test_prediction_cache_birth_data_signatures_source::test_predictions_manual_recalculation_setting_defaults_to_manual_and_blocks_trait_auto_load`
  - Expected manual-recalculation settings key/default and trait auto-load guard are absent from app.py.
- [ ] `test_prediction_cache_birth_data_signatures_source::test_stale_predictions_show_cached_data_before_optional_auto_refresh`
  - Expected background-refresh explanatory text is absent from the D&D renderer.
- [ ] `test_prediction_norms_snapshot_source::test_chart_view_traits_keep_uid_metadata_visible_when_cache_is_stale_or_incomplete`
  - Expected explicit `metadata["stale"] = True` mutation has changed form or disappeared.

## 2. Database View, Search, and Analytics (14)

- [ ] `test_collapsible_subsection_background_source::test_database_search_top_categories_are_nested_sections`
  - Expected nested Predictions section construction is absent from the search panel source.
- [ ] `test_collapsible_subsection_background_source::test_database_search_subsections_use_standard_section_background`
  - Expected Lifespan section construction marker is absent.
- [ ] `test_database_analytics_demand_refresh_source::test_database_analytics_flushes_pending_metrics_before_close_cache_save`
  - Expected close/save ordering markers could not be found.
- [ ] `test_database_analytics_enneagram_source::test_database_analytics_enneagram_popout_uses_standard_info_html`
  - Expected standard Enneagram popout HTML builder call is absent.
- [ ] `test_database_metrics_persistent_cache_source::test_incremental_refresh_reuses_same_changed_ids_for_every_section_step`
  - Expected changed-ID state clearing point has changed; review for both test drift and incremental-refresh correctness.
- [ ] `test_database_search_subspecies_source::test_clear_and_active_filter_state_include_subspecies`
  - Expected app.py active-filter expression is absent, possibly because search ownership moved.
- [ ] `test_database_view_hidden_chart_context_menu_source::test_show_hidden_setting_names_charts_explicitly`
  - Expected “Show Hidden Charts” checkbox construction is absent from app.py.
- [ ] `test_database_view_hidden_chart_context_menu_source::test_unhide_selected_charts_removes_ids_and_preserves_selection`
  - Expected numeric-ID set update is absent; this may be desirable UID migration rather than regression.
- [ ] `test_database_view_hidden_chart_context_menu_source::test_hidden_charts_filter_is_conditionally_visible_in_search_panel`
  - Expected settings-key reference is absent from the extracted search panel.
- [ ] `test_database_view_hidden_chart_context_menu_source::test_hidden_charts_filter_matches_hidden_id_set_only_when_visible`
  - Expected numeric-ID membership expression is absent; review against UID-first architecture before restoring it.
- [ ] `test_database_view_hydration_source::test_populate_list_skips_per_row_filter_engine_when_no_filters_are_active`
  - Expected fast-path source shape changed; performance behavior should be benchmarked rather than restored textually.
- [ ] `test_traits_settings_source::test_database_view_traits_search_lives_in_search_panel_and_uses_metadata`
  - Expected `🧬Traits` collapsible section marker is absent from the search panel.
- [ ] `test_uid_finalization_source::test_database_view_loads_selected_chart_by_uid_when_available`
  - Expected direct extraction of `Qt.UserRole + 2` UID is absent from `_load_chart_from_item`; likely a real UID-path audit item.
- [ ] `test_similar_charts_hidden_visibility_source::test_trait_rankings_are_moved_to_rankings_panel`
  - Expected `RankingsPanelMixin` inheritance is absent from the legacy Database View class declaration.

## 3. Similarities, Astro Twin, and rankings (9)

- [ ] `test_astro_twin_settings_layout_source::test_placement_weighting_modes_have_item_and_selected_tooltips`
  - Expected tooltip constant/use is absent from the inspected settings method.
- [ ] `test_similar_charts_hidden_visibility_source::test_similar_charts_app_passes_current_hidden_chart_visibility_to_candidates`
  - Expected hidden UID set propagation is absent from the candidate call.
- [ ] `test_similar_charts_hidden_visibility_source::test_chart_view_similar_charts_worker_receives_hidden_chart_visibility`
  - Expected hidden UID set propagation is absent from the worker request.
- [ ] `test_similar_charts_hidden_visibility_source::test_rankings_links_use_chart_uids_for_navigation_targets`
  - Expected UID-first link-target expression changed; implementation already emits UID-only links in some paths, so review test location.
- [ ] `test_similar_charts_hidden_visibility_source::test_trait_rankings_default_to_database_until_manual_rank_selected`
  - Expected selected-chart UID state marker is absent from the inspected handler.
- [ ] `test_similar_charts_hidden_visibility_source::test_hiding_current_trait_ranking_members_refreshes_cached_top_ten`
  - Expected ranked-chart UID state marker is absent from the inspected method.
- [ ] `test_similarity_algorithm_accuracy_refresh_source::test_manage_presets_navigates_to_property_manager_preset_field`
  - Test expects singular “Property Manager”; source currently uses plural “Property Managers.”
- [ ] `test_user_facing_terminology_source::test_similarity_modules_and_rectification_visible_labels_are_canonical`
  - Expected Astro Twin window title expression is absent.
- [ ] `test_user_facing_terminology_source::test_astro_twin_calculator_and_similarities_analysis_remain_distinct`
  - Expected settings explanation distinguishing the calculator algorithm is absent.

## 4. Settings, panels, and appwide UI (6)

- [ ] `test_chart_info_token_formatting_source::test_chart_info_ambiguous_short_tokens_require_uppercase_word_matches`
  - Expected exact uppercase-only token set is absent from style.py.
- [ ] `test_demo_mode_privacy_source::test_demo_mode_restores_saved_predictability_visibility_instead_of_forcing_visible`
  - Expected saved-visibility lookup is absent from app.py; likely a privacy regression candidate.
- [ ] `test_galaxy_explainer_intro_source::test_guide_bottom_panels_are_controlled_by_button_panel`
  - Expected minimum button-panel height is absent from the guide window method.
- [ ] `test_predictions_settings_source::test_gender_guesser_render_routes_through_predictions_panel`
  - Expected gender-guesser visibility-routing expression is absent from app.py.
- [ ] `test_property_manager_settings_height_source::test_property_manager_tab_fills_the_available_settings_height`
  - Expected settings-method boundaries/markers could not be found after layout changes.
- [ ] `test_chart_view_tag_crash_diagnostics_source::test_startup_debug_installs_persistent_native_crash_diagnostics`
  - Expected `faulthandler.register(... chain=True)` source form is absent; verify behavior and platform safety.

## 5. Tags, rectification, and data presentation (4)

- [ ] `test_tag_chip_pill_style_source::test_chart_tags_live_in_chart_info_stack_not_subjective_notes_panel`
  - Expected chart-info stack index marker is absent from app.py.
- [ ] `test_tag_manager_parent_counts_source::test_tag_manager_parent_node_counts_include_exact_parent_tag_rows`
  - Expected exact-parent path count branch is absent from the tag manager method.
- [ ] `test_rectification_engine_views_source::test_house_refinement_is_scoped_to_current_results`
  - Expected removal of prior refinement-angle widgets is absent from the extracted dialog.
- [ ] `test_enneagram_database_norm_predictions_source::test_enneagram_predictor_uses_analysis_enneagrams_reference_source`
  - Expected direct import of `analysis.enneagram.ENNEAGRAMS` is absent from app.py; likely ownership/import relocation.
## Suggested review order

1. **UID integrity and privacy:** UID load path, hidden-chart propagation, demo-mode visibility.
2. **Data-loss/recalculation risks:** subjective-only saves, prediction cache staleness, analytics close-cache flush.
3. **Performance contracts:** hydration fast path and incremental refresh state.
4. **User-visible behavior:** prompts, labels, section placement, and popout titles.
5. **Pure source-location drift:** delegated wrappers, extracted imports, and renamed settings sections.

When resolving an item as test drift, prefer replacing exact-string assertions
with a focused behavioral/unit test at the new owner. Keep source assertions
only for architectural prohibitions or wiring that cannot reasonably be tested
through an interface.
