# Update service architecture

EphemeralDaddy's update service separates **discovery** from **installation**.
The Python application may parse a release manifest and tell the user that an
update exists, but it must not overwrite its own executable. Signed native
updaters own installation:

| Platform | Manifest artifact | Installer/updater |
| --- | --- | --- |
| Windows | `appinstaller` | MSIX App Installer |
| macOS | `sparkle-appcast` | Sparkle 2 |
| Linux (installed) | `flatpak` | Flatpak/OSTree |
| Linux (portable) | `appimage-zsync` | AppImageUpdate |

## Version source of truth

`ephemeraldaddy/version.py` is the only file in which a release version is
manually changed. `pyproject.toml` reads it as dynamic package metadata.

Windows Inno Setup cannot import a Python module, so its small include file is
generated rather than maintained manually:

```bash
python tools/sync_release_version.py
python tools/sync_release_version.py --check
```

The PyInstaller build helper runs the synchronization command automatically.
CI should run the `--check` command to reject a release commit with stale
generated metadata.

## Manifest contract

The initial schema is deliberately small and platform-neutral:

```json
{
  "schema_version": 1,
  "channel": "stable",
  "version": "3.1.0",
  "minimum_supported_version": "3.0.0",
  "published_at": "2026-09-01T00:00:00Z",
  "release_notes_url": "https://example.invalid/releases/3.1.0",
  "artifacts": {
    "windows-x86_64": {
      "type": "appinstaller",
      "url": "https://example.invalid/windows/EphemeralDaddy.appinstaller"
    },
    "macos-universal": {
      "type": "sparkle-appcast",
      "url": "https://example.invalid/macos/appcast.xml"
    },
    "linux-x86_64": {
      "type": "flatpak",
      "ref": "app/io.github.ephemeraldaddy.EphemeralDaddy/x86_64/stable"
    }
  }
}
```

`UpdateChecker` does no I/O until its explicit `check()` method is called. Its
fetcher is injectable so tests and future offline behavior never depend on the
network. The result distinguishes:

- the current release;
- a normal update;
- a release that requires a complete package because the installed base is too
  old for the supported patch path; and
- a platform for which the manifest has no artifact.

## Security boundary

The shared JSON manifest is discovery metadata, not authority to execute code.
When platform installers are integrated, they must independently validate their
native signatures. The application must only accept an HTTPS production
manifest URL, and release CI must sign/notarize artifacts before publishing the
manifest that refers to them.

## Next integration steps

1. Select and configure the production HTTPS manifest host.
2. Add a Qt update controller and **Check for Updates…** action outside
   `gui/app.py`; it should call `UpdateChecker` asynchronously.
3. Add platform adapters that hand off to MSIX App Installer, Sparkle, Flatpak,
   or AppImageUpdate rather than replacing files from Python.
4. Add signing, manifest publication, and upgrade-from-previous-version jobs to
   the release pipeline.
5. Back up user data before database migrations that accompany an update.

