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

## User-facing stable-release language

Every update prompt, update settings surface, release dialog, and rollback
screen must use the canonical `STABLE_RELEASE_ASSURANCE` copy from
`ephemeraldaddy/updates/messaging.py`:

> This isn't a new and exciting invasion of privacy or a monetization step. It's
> just a bug fix and/or feature update I'm gonna go ahead and call 'a stable
> release'. With any luck, it will improve function without disrupting anything
> you currently enjoy. If you notice something amiss or yearn for something from
> a prior version, you can roll back safely & communicate with me on Github.

## Security boundary

The shared JSON manifest is discovery metadata, not authority to execute code.
When platform installers are integrated, they must independently validate their
native signatures. The application must only accept an HTTPS production
manifest URL, and release CI must sign/notarize artifacts before publishing the
manifest that refers to them.

## Release acceptance and rollback contract

Discovery alone does **not** make a machine eligible. Before a native updater
is allowed to install, `UpdateAcceptanceCoordinator` runs all adapter-provided
preflight checks. A failed check cancels before backup or installation. The
minimum preflight set is:

- installed version is on a supported update path;
- complete artifact download;
- native signature verification;
- artifact checksum verification;
- sufficient free disk space; and
- application process is closed before replacement.

After preflight passes, the coordinator requires a verified full user-data
backup before invoking the platform adapter. After installation it runs the
adapter's post-install probes. These must cover application launch, bundled
resources, chart creation, database writes, database integrity/migration, and
the survival of settings, photos, and chart data.

If installation raises (including an interrupted download/install), or any
post-install probe fails, the coordinator invokes the platform adapter's native
rollback and restores the pre-update user-data package. The candidate release
is accepted only if every post-install probe passes. Platform adapters must be
atomic and must retain the prior signed application until acceptance completes;
Python never replaces application binaries itself.

### Required release-pipeline scenarios

The shared simulated acceptance suite is in
`tests/test_update_release_acceptance.py`. Native Windows, macOS, and Linux CI
jobs must exercise the same scenarios against real packages before publishing:

- fresh installation;
- update from the immediately preceding and oldest supported releases;
- update with an existing charts database;
- interrupted installation;
- invalid signature and corrupted artifact;
- insufficient disk space and application still running;
- successful launch after upgrade;
- successful database backup and migration;
- failed-migration recovery; and
- unchanged user settings, photos, and databases after rollback.

The Python suite proves the shared cancellation/rollback policy. It does not
claim to verify MSIX, Sparkle, Flatpak, or AppImage behavior: each native release
job remains responsible for real install, signature, interruption, relaunch,
and rollback acceptance tests on its target operating system.

## Next integration steps

1. Select and configure the production HTTPS manifest host.
2. Add a Qt update controller and **Check for Updates…** action outside
   `gui/app.py`; it should call `UpdateChecker` asynchronously.
3. Add platform adapters that hand off to MSIX App Installer, Sparkle, Flatpak,
   or AppImageUpdate rather than replacing files from Python.
4. Connect the existing full-app backup package to `create_backup` and
   `restore_backup`, then provide launch/database/data-survival post-install
   probes.
5. Add signing, manifest publication, and native acceptance jobs to the release
   pipeline. Publishing must remain blocked until every platform job passes.
