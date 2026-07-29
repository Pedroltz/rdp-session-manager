<div align="center">
  <h1>RDP Session Manager</h1>
  <p>A GTK-based Linux application for managing Remote Desktop Protocol (RDP) users and sessions.</p>
  <img src="imgs/RDPSM.png" alt="RDP Session Manager" width="220">
  <br><br>
  <img src="https://img.shields.io/badge/license-GPL--3.0-blue.svg" alt="GPL-3.0 license">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue.svg" alt="Python 3.9 or later">
  <img src="https://img.shields.io/badge/GTK-4.0-green.svg" alt="GTK 4">
</div>

## Overview

RDP Session Manager provides a graphical interface for administering RDP access through xrdp on supported Linux distributions. It centralizes account management, session configuration, and dependency checks in a native GTK 4 and libadwaita application.

## Features

- Create, remove, enable, and disable RDP user accounts.
- Configure full desktop sessions with supported desktop environments.
- Run Linux applications as RemoteApp sessions.
- Run Windows applications as WineGE RemoteApp sessions.
- Check and install required RDP components when needed.
- Monitor user status and active sessions.

## Technology

- Python 3.9+
- GTK 4 and libadwaita
- xrdp and FreeRDP
- PolicyKit for privileged system operations

## Requirements

Supported distributions:

- Ubuntu 22.04 LTS or later and derivatives
- Debian 12 or later
- Arch Linux and derivatives, including Manjaro, EndeavourOS, and CachyOS

The application requires Python, GTK 4, libadwaita, and PolicyKit. The installer can set up xrdp and FreeRDP; see the installation guide for the complete dependency list.

## Installation

Run the official installer:

```bash
curl -fsSL https://github.com/Pedroltz/rdp-session-manager/releases/latest/download/install.sh | bash
```

For manual installation, installer options, and platform-specific notes, see the [installation guide](docs/INSTALL.md).

## Running the Application

From a development clone with the required dependencies installed:

```bash
./run.sh
```

You can also start the graphical interface directly:

```bash
python3 src/main.py
```

Command-line usage and available commands are documented in the [CLI reference](docs/CLI.md).

## Documentation

- [Installation guide](docs/INSTALL.md)
- [CLI reference](docs/CLI.md)
- [WineGE RemoteApp guide](docs/WINEGE_REMOTEAPP.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Development guide](docs/DEVELOPMENT.md)
- [Continuous integration and release checks](docs/CI.md)
- [Changelog](CHANGELOG.md)

## Contributing

Contributions are welcome. Fork the repository, create a focused branch, and open a pull request describing the change.

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
