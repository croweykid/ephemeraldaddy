from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_photo_gallery_persists_profile_pic_metadata_and_defaults_first_upload():
    db_source = (REPO_ROOT / "ephemeraldaddy/core/db.py").read_text()
    gallery_source = (REPO_ROOT / "ephemeraldaddy/core/photo_gallery.py").read_text()

    assert "profile_pic       TEXT" in db_source
    assert "def get_chart_profile_pic" in db_source
    assert "def set_chart_profile_pic" in db_source
    assert "existing_profile_pic = get_chart_profile_pic(chart_uid)" in gallery_source
    assert "if not existing_profile_pic:" in gallery_source
    assert "set_chart_profile_pic(chart_uid, photo_id)" in gallery_source


def test_photo_gallery_thumbnail_context_menu_and_profile_star():
    source = (REPO_ROOT / "ephemeraldaddy/gui/features/controllers/chart_view_window.py").read_text()

    assert 'self.profile_star_label = QLabel("⭐️", self)' in source
    assert 'profile_action.setText("Set as profile pic (current profile pic)")' in source
    assert "profile_action.setEnabled(False)" in source
    assert 'delete_action = QAction("Delete", menu)' in source
    assert "owner._set_photo_gallery_profile_pic = MethodType" in source
    assert 'self.delete_button = QPushButton("×", self)' in source
    assert "font-size: 16px; font-weight: 900; padding: 0px;" in source
