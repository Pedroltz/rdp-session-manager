# Windows applications: automated installation and validation

RDP Session Manager supports isolated Windows applications through a maintained
UMU/Proton runner or the legacy WineGE runner. WineGE itself is archived, so new
installations prefer `umu-run` when it is available. Existing WineGE profiles
continue to work until explicitly migrated.

## How it works

Each application has its own compatibility prefix, manifest, state and logs
under:

```text
~/.local/share/rdp-session-manager/windows-apps/APP_ID/
```

An application moves through staging, prefix creation, installation,
executable discovery, local validation and real RDP validation. It is only
marked `ready` after the application remains running and opens through the RDP
launcher.

Windows programs are not a security sandbox. Use a dedicated RDP user for
untrusted or unrelated applications.

## Install a local application

An MSI uses standard unattended options by default:

```bash
rdpsm windows-app install USERNAME \
  --source /path/to/application.msi \
  --name "Application"
```

For an installer with known silent arguments:

```bash
rdpsm windows-app install USERNAME \
  --source /path/to/setup.exe \
  --installer-arg /S \
  --executable-pattern '*/Application.exe'
```

Unknown EXE installers automatically enter assisted mode. Connect using the
new RDP profile, complete the installer, and close it. RDPSM then compares the
prefix before and after installation and selects the installed program when
there is one unambiguous candidate.

Use `--mode portable` for a directory containing an unpacked application, or
select a catalog recipe:

```bash
rdpsm windows-app catalog list
rdpsm windows-app install USERNAME \
  --recipe generic-nsis \
  --source /path/to/setup.exe
```

Catalog downloads must use HTTPS and include a SHA-256 checksum. Installer
arguments are JSON arrays and are never evaluated as shell code.

The bundled `notepad-plus-plus` recipe is a pinned, validated MSI example:

```bash
rdpsm windows-app install USERNAME --recipe notepad-plus-plus
```

## Inspect and finish an installation

```bash
rdpsm windows-app status USERNAME
rdpsm windows-app status USERNAME APP_ID --format json
rdpsm windows-app select USERNAME APP_ID
rdpsm windows-app validate USERNAME APP_ID
rdpsm windows-app logs USERNAME APP_ID
rdpsm windows-app retry USERNAME APP_ID
```

On a server without a desktop session, `rdpsm` requests administrator
credentials through terminal `sudo`. Local graphical validation uses Xvfb.
After it passes, connect through RDP once to complete window validation.

## Migrate a legacy WineGE profile

```bash
rdpsm windows-app migrate USERNAME PROFILE_ID
```

Migration clones the shared legacy `.wine` prefix with reflink support when the
filesystem provides it. The original prefix is not deleted. This matters when
multiple old profiles still share the same prefix.

The deprecated commands `rdpsm user winege list` and `select` remain available
for profiles that have not been migrated.

## Recipe schema

Recipes live in `data/windows-app-recipes` and use schema version 1:

```json
{
  "schema_version": 1,
  "id": "example",
  "name": "Example",
  "source": {
    "url": "https://publisher.example/application.exe",
    "sha256": "64-lowercase-hex-characters",
    "filename": "application.exe"
  },
  "installer": {
    "type": "exe",
    "silent_args": ["/S"],
    "success_codes": [0],
    "timeout": 900
  },
  "runtime": {
    "runner": "umu-proton",
    "architecture": "win64"
  },
  "winetricks": [],
  "executable": {
    "patterns": ["*/Application.exe"],
    "args": []
  }
}
```

Do not add click automation or guessed silent flags to recipes. If an
installer does not document an unattended mode, use assisted installation.
