from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_bootstrap_sets_identity_before_qapplication_and_splash() -> None:
    source = (ROOT / "ephemeraldaddy/gui/bootstrap.py").read_text(encoding="utf-8")

    identity = source.index("configure_pre_qapplication_identity()")
    application = source.index("app = QApplication(")
    splash = source.index("loading = StartupLoadingWidget()")

    assert identity < application < splash
    assert "QApplication([APP_DISPLAY_NAME, *sys.argv[1:]])" in source


def test_qsettings_application_namespace_remains_backward_compatible() -> None:
    identity_source = (ROOT / "ephemeraldaddy/gui/application_identity.py").read_text(
        encoding="utf-8"
    )

    assert 'APP_DISPLAY_NAME = "Ephemeral Daddy"' in identity_source
    assert "QCoreApplication.setApplicationName(APP_DISPLAY_NAME)" in identity_source
    assert "app.setApplicationName(APP_DISPLAY_NAME)" in identity_source
    assert "setApplicationName(APP_SHELL_DISPLAY_NAME)" not in identity_source
    assert "app.setApplicationDisplayName(APP_SHELL_DISPLAY_NAME)" in identity_source


def test_linux_desktop_identity_matches_qt_desktop_file_name() -> None:
    identity_source = (ROOT / "ephemeraldaddy/gui/application_identity.py").read_text(
        encoding="utf-8"
    )
    desktop_source = (
        ROOT / "packaging/linux/io.github.ephemeraldaddy.EphemeralDaddy.desktop"
    ).read_text(encoding="utf-8")

    desktop_id = "io.github.ephemeraldaddy.EphemeralDaddy"
    assert f'APP_DESKTOP_ID = "{desktop_id}"' in identity_source
    assert f"StartupWMClass={desktop_id}" in desktop_source


def test_macos_bundle_has_stable_identity_and_icon() -> None:
    source = (ROOT / "tools/build_desktop_app.py").read_text(encoding="utf-8")

    assert source.count("bundle_identifier='io.github.ephemeraldaddy.EphemeralDaddy'") == 2
    assert "BUNDLE(exe, name='EphemeralDaddy.app'" in source
    assert "BUNDLE(coll, name='EphemeralDaddy.app'" in source
