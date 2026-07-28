# Installer tooling

This directory contains everything used to install, package and remove
RDP Session Manager.

## Files

- `core.py`: visual Python installer and distribution-specific logic.
- `install.sh`: small bootstrap published as the stable GitHub installation link.
- `build_packages.sh`: builds the Debian and Arch application packages.
- `uninstall.sh`: removes an installed application.
- `requirements.txt`: dependencies used only by the development copy of the installer.
- `__main__.py`: allows the installer to run with `python -m installer`.

## Local development

```bash
python3 -m venv .venv-installer
. .venv-installer/bin/activate
python -m pip install -r installer/requirements.txt
python -m installer --dry-run
```

Build and install the current checkout:

```bash
./installer/build_packages.sh
python -m installer --local
```

The release workflow publishes `install.sh`, `installer.py`, the bundled
`installer.pyz`, both native packages and `SHA256SUMS` using stable asset names.
