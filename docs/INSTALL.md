# Installation Guide

Complete installation instructions for RDP Session Manager on Ubuntu/Debian and Arch Linux.

## Table of Contents

- [System Requirements](#system-requirements)
- [Automated Installation](#automated-installation)
- [Manual Installation](#manual-installation)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Uninstallation](#uninstallation)

## System Requirements

### Supported Operating Systems
- Ubuntu 22.04 LTS or later and derivados
- Debian 12 or later
- Arch Linux, Manjaro, EndeavourOS and CachyOS

### Minimum Hardware Requirements
- CPU: 1 GHz processor or faster
- RAM: 2 GB (4 GB recommended)
- Disk Space: 500 MB for application
- Network: Internet connection for downloads

### Software Prerequisites
- Python 3.8 or higher
- systemd or sysvinit (service management)

## Automated Installation (recommended)

```bash
curl -fsSL https://github.com/Pedroltz/rdp-session-manager/releases/latest/download/install.sh | bash
```

The installer shows the exact plan, downloads the correct package, validates
its SHA-256 checksum, installs dependencies in one transaction and enables
xrdp. Before authentication, the visual assistant asks whether xrdp and the
optional WineGE support should be installed. It is safe to run again.

```bash
# Plan only, without changing the system
curl -fsSL https://github.com/Pedroltz/rdp-session-manager/releases/latest/download/install.sh | bash -s -- --dry-run

# Optional WineGE dependencies
curl -fsSL https://github.com/Pedroltz/rdp-session-manager/releases/latest/download/install.sh | bash -s -- --with-wine

# A specific stable release
curl -fsSL https://github.com/Pedroltz/rdp-session-manager/releases/latest/download/install.sh | bash -s -- --release v0.4.0
```

The complete log is written to `~/.local/state/rdp-session-manager/install.log`.
The published installer bundles the Rich terminal interface inside
`installer.pyz`; no separate `pip install` is required for end users.

On Arch, xrdp and xorgxrdp come from the AUR. The installer uses `yay` or
`paru` when available; otherwise it displays the AUR sources and asks for
confirmation before compiling them. On a clean Arch installation it also
installs `base-devel`, Git and GnuPG, imports the full PGP fingerprints declared
by the PKGBUILDs and lets `makepkg` resolve the remaining build dependencies.

When WineGE support is selected on Arch, the installer transparently enables
the official `[multilib]` repository when needed, preserving the original
configuration as `/etc/pacman.conf.rdpsm.bak`. It then installs both 64-bit and
32-bit Wine runtime libraries in the same synchronized package transaction.

To inspect the bootstrap before executing it:

```bash
curl -fL https://github.com/Pedroltz/rdp-session-manager/releases/latest/download/install.sh -o install.sh
less install.sh
bash install.sh
```

### Test from a local clone

```bash
python3 -m venv .venv-installer
. .venv-installer/bin/activate
python -m pip install -r installer/requirements.txt
python -m installer --dry-run
```

Add `--verbose` to preview the detailed command-output view.

For a real installation of the code in the current clone:

```bash
./installer/build_packages.sh
python -m installer --local
```

## Manual Installation

See the project documentation for manual dependency installation and troubleshooting.

Oracle Instant Client is no longer installed automatically. Its licensed
packages must be installed separately according to Oracle's instructions.

---

Copyright (C) 2025 - RDP Session Manager Contributors
