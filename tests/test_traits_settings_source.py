from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_traits_settings_ui_lives_outside_app_py():
    app_source = (ROOT / "ephemeraldaddy" / "gui" / "app.py").read_text(encoding="utf-8")
    settings_source = (ROOT / "ephemeraldaddy" / "gui" / "features" / "settings" / "traits.py").read_text(
        encoding="utf-8"
    )

    assert "populate_traits_settings_layout(self, traits_layout)" in app_source
    assert 'property_tabs.addTab(traits_widget, "Traits")' in app_source
    assert "def _on_trait_upload_clicked" not in app_source
    assert "def add_traits_settings_section" in settings_source
    assert "def populate_traits_settings_layout" in settings_source
    assert "def on_trait_upload_clicked" in settings_source
    assert "Edit JSON…" in settings_source
    assert "def on_trait_edit_clicked" in settings_source
    assert "parse_trait_file(temp_path)" in settings_source
    assert "def _mark_trait_definitions_changed" in settings_source
    assert "clear_likelihoods=False" in settings_source
    assert "_warm_trait_definitions(owner, {clean_name})" in settings_source


def test_traits_settings_list_fills_available_window_height():
    settings_source = (ROOT / "ephemeraldaddy" / "gui" / "features" / "settings" / "traits.py").read_text(
        encoding="utf-8"
    )

    assert '"Traits",\n        fill_available_height=True,' in settings_source
    assert "setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)" in settings_source
    assert "traits_section.addWidget(owner._traits_list_widget, 1)" in settings_source
    assert "_traits_list_widget.setMaximumHeight" not in settings_source


def test_trait_prediction_rendering_lives_outside_app_py():
    app_source = (ROOT / "ephemeraldaddy" / "gui" / "app.py").read_text(encoding="utf-8")
    predictions_source = (
        ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "trait_predictions.py"
    ).read_text(encoding="utf-8")
    snapshot_source = (
        ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "prediction_norms_snapshot.py"
    ).read_text(encoding="utf-8")
    db_source = (ROOT / "ephemeraldaddy" / "core" / "db.py").read_text(encoding="utf-8")
    db_source = (ROOT / "ephemeraldaddy" / "core" / "db.py").read_text(encoding="utf-8")

    assert "def _render_traits_predictions" in app_source
    assert "_render_traits_predictions(self, chart)" in app_source
    assert "def render_traits_predictions" in predictions_source
    assert "calculate_trait_likelihoods" in predictions_source
    assert "def _trait_snapshot_norm_signature" in predictions_source
    assert "Traits panel bypassed unavailable profiles" in predictions_source
    assert "refresh_trait_norms_snapshot(owner, missing_traits)" not in predictions_source
    assert "def missing_trait_norms" in snapshot_source
    assert "TRAIT_DB_NORMS_CACHE_PATH" not in predictions_source


def test_traits_settings_can_reassess_only_unavailable_profiles():
    settings_source = (
        ROOT / "ephemeraldaddy" / "gui" / "features" / "settings" / "traits.py"
    ).read_text(encoding="utf-8")

    assert 'QPushButton("Reassess unavailable traits")' in settings_source
    assert "missing_trait_norms(traits, snapshot)" in settings_source
    assert "trait_norm_unavailability_reasons(missing, snapshot)" in settings_source
    assert "class _TraitNormReassessmentWorker(QObject)" in settings_source
    assert "worker = _TraitNormReassessmentWorker(owner, missing)" in settings_source
    assert "thread.started.connect(worker.run)" in settings_source
    assert "refresh_trait_norms_snapshot(self._owner, self._traits)" in settings_source


def test_prediction_norm_rows_use_full_database_not_displayed_filter_scope():
    app_source = (ROOT / "ephemeraldaddy" / "gui" / "app.py").read_text(encoding="utf-8")
    method = app_source[
        app_source.index("    def _prediction_norm_rows")
        : app_source.index("    def _prediction_norms_render_token")
    ]

    assert 'chart_rows = getattr(self, "_chart_rows", None)' in method
    assert 'getattr(manage_dialog, "_chart_rows", None)' in method
    assert "_displayed_chart_rows_by_id" not in method


def test_database_view_traits_search_lives_in_search_panel_and_uses_metadata():
    app_source = (ROOT / "ephemeraldaddy" / "gui" / "app.py").read_text(encoding="utf-8")
    search_source = (ROOT / "ephemeraldaddy" / "gui" / "dbv_search_panel.py").read_text(encoding="utf-8")
    predictions_source = (
        ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "trait_predictions.py"
    ).read_text(encoding="utf-8")
    db_source = (ROOT / "ephemeraldaddy" / "core" / "db.py").read_text(encoding="utf-8")

    assert 'add_collapsible_section("Traits Present", nested=True)' in search_source
    assert 'add_collapsible_section("Traits Absent", nested=True)' in search_source
    assert "def collect_search_trait_filter_sets" in search_source
    assert "def chart_matches_trait_filters" in search_source
    assert "collect_search_trait_filter_sets(self)" in app_source
    assert "chart_matches_trait_filters(" in app_source
    assert "def trait_metadata_for_chart" in predictions_source
    assert "predicted_traits_above_avg" in predictions_source
    assert "predicted_traits_below_avg" in predictions_source
    assert "CREATE TABLE IF NOT EXISTS chart_trait_metadata" in db_source
    assert "def upsert_chart_trait_metadata" in db_source
    assert "def get_chart_trait_metadata" in db_source
    assert "db.upsert_chart_trait_metadata" in predictions_source
    assert "db.get_chart_trait_metadata" in predictions_source


def test_chart_view_trait_metadata_is_incremental_by_trait_signature():
    predictions_source = (
        ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "trait_predictions.py"
    ).read_text(encoding="utf-8")
    db_source = (ROOT / "ephemeraldaddy" / "core" / "db.py").read_text(encoding="utf-8")

    assert "def _trait_definition_signature" in predictions_source
    assert "cached_rows_by_name" in predictions_source
    assert "missing_traits = [trait for name, trait in traits_by_name.items()" in predictions_source
    assert 'row.get("trait_signature", trait_signature)' in db_source


def test_trait_norms_use_static_snapshot_without_dynamic_refresh_threshold():
    predictions_source = (
        ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "trait_predictions.py"
    ).read_text(encoding="utf-8")

    assert "def _trait_snapshot_norm_signature" in predictions_source
    assert "prospective_trait_snapshot_token" in predictions_source
    assert "_database_norm_state_is_fresh" not in predictions_source
    assert "_database_norm_signature_for_traits" not in predictions_source


def test_trait_uid_source_and_metadata_wiring_are_present():
    traits_source = (ROOT / "ephemeraldaddy" / "analysis" / "traits.py").read_text(encoding="utf-8")
    predictions_source = (
        ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "trait_predictions.py"
    ).read_text(encoding="utf-8")
    db_source = (ROOT / "ephemeraldaddy" / "core" / "db.py").read_text(encoding="utf-8")

    assert "def normalize_trait_uid" in traits_source
    assert "def trait_uid_for_profile" in traits_source
    assert '"uid": trait_uid' in traits_source
    assert "trait_uid         TEXT NOT NULL DEFAULT ''" in db_source
    assert "trait_uid = excluded.trait_uid" in db_source
    assert "traits_by_uid" in predictions_source
    assert '"trait_uid": trait_uids_by_name.get(name, "")' in predictions_source


def test_legacy_trait_signature_and_parenthesized_names_are_preserved():
    predictions_source = (
        ROOT / "ephemeraldaddy" / "gui" / "features" / "charts" / "trait_predictions.py"
    ).read_text(encoding="utf-8")
    settings_source = (ROOT / "ephemeraldaddy" / "gui" / "features" / "settings" / "traits.py").read_text(
        encoding="utf-8"
    )

    assert "def _trait_signature_payload" in predictions_source
    assert "def _trait_display_signature_payload" in predictions_source
    assert "trait_display_signature" in predictions_source
    assert "legacy_trait_signature" in predictions_source
    assert "strip_uids=True" in predictions_source
    assert "item.setData(Qt.UserRole + 5, name)" in settings_source
    assert "raw_name = item.data(Qt.UserRole + 5)" in settings_source
    assert "text.endswith(suffix)" in settings_source


def test_deleted_traits_purge_uid_metadata_from_settings_handler():
    settings_source = (ROOT / "ephemeraldaddy" / "gui" / "features" / "settings" / "traits.py").read_text(
        encoding="utf-8"
    )
    db_source = (ROOT / "ephemeraldaddy" / "core" / "db.py").read_text(encoding="utf-8")

    assert "item.setData(Qt.UserRole + 6" in settings_source
    assert "purge_chart_trait_metadata_for_trait" in settings_source
    assert "def purge_chart_trait_metadata_for_trait" in db_source
    assert "trait_uid = ?" in db_source
