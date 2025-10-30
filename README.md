# RDP Session Manager

A professional GTK4-based application for managing Remote Desktop Protocol (RDP) sessions on Linux systems.

![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![GTK](https://img.shields.io/badge/GTK-4.0-green.svg)

## Overview

RDP Session Manager is a comprehensive desktop application designed for GNOME environments, providing centralized management of RDP user accounts and sessions. Built with GTK4 and libadwaita, it offers a native Linux experience for administering remote desktop access through the xrdp server.

## Key Features

### User Management
- Create RDP user accounts with automated configuration
- Delete users with complete data removal
- Enable/disable user accounts via graphical toggle
- Automatic termination of active sessions during deletion
- Real-time input validation
- Active process detection per user
- Status monitoring (Connected/Enabled/Disabled)

### Desktop Environment Support
The application supports seven desktop environments with automatic installation:
- LXDE (250MB) - Lightweight
- LXQt (350MB) - Modern and lightweight
- XFCE (400MB) - Recommended for balance
- MATE (600MB) - Traditional desktop
- Cinnamon (800MB) - Feature-rich
- GNOME (1.2GB) - Complete desktop
- KDE Plasma (1.5GB) - Advanced features

Features include:
- Automated desktop environment installation
- Disk space verification before installation
- Detection of pre-installed environments

### RDP Connectivity
- Automatic FreeRDP client detection
- On-demand FreeRDP installation with progress tracking
- Graphical credential input dialog
- Support for Windows domain authentication
- Direct RDP client launching
- Automatic clipboard integration
- Connection string auto-copy

### System Dependencies
- Automatic xrdp server verification on startup
- Warning banner for missing dependencies
- One-click dependency installation
- Real-time installation progress
- On-demand dependency resolution

### Monitoring and Logging
- Real-time session monitoring
- Server IP and port visualization
- Comprehensive structured logging
- Centralized log management
- Automatic log rotation

### Security Features
- PolicyKit integration for administrative operations
- User isolation via dedicated group (rdp-users)
- UID allocation starting at 5000
- Isolated home directories (/opt/rdp-users)
- Strong password validation
- Absolute path usage for all system commands
- Reduced privilege escalation prompts through helper scripts

## System Requirements

### Supported Platforms
- Ubuntu 20.04 LTS or later
- Debian 11 (Bullseye) or later
- Windows Subsystem for Linux (WSL) with Ubuntu/Debian

### Runtime Dependencies
- Python 3.8 or higher
- GTK 4.0
- libadwaita 1.0
- PolicyKit (policykit-1)
- xrdp server (installable via application)
- FreeRDP client (installable via application)

## Installation

### Quick Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/rdp-session-manager.git
cd rdp-session-manager

# Run the installation script
./install.sh
```

The installation script will:
- Detect your system (Ubuntu/Debian/WSL)
- Install system dependencies (GTK4, libadwaita, etc.)
- Install Python dependencies (PyGObject, psutil)
- Configure necessary permissions
- Optionally install xrdp and FreeRDP
- Create Python virtual environment (optional)

### Manual Installation

For detailed manual installation instructions, refer to [INSTALL.md](INSTALL.md).

#### System Dependencies (Debian/Ubuntu)
```bash
sudo apt-get install -y \
    python3 python3-pip python3-venv python3-dev \
    libgtk-4-1 libgtk-4-dev \
    libadwaita-1-0 libadwaita-1-dev \
    gir1.2-gtk-4.0 gir1.2-adw-1 \
    python3-gi python3-gi-cairo \
    policykit-1
```

#### Python Dependencies
```bash
pip install -r requirements.txt
```

## Usage

RDP Session Manager can be used via graphical interface (GUI) or command line (CLI).

### Running the Graphical Interface

```bash
# With virtual environment
source venv/bin/activate
python3 src/main.py

# Without virtual environment
python3 src/main.py
```

### Running the Command Line Interface

```bash
# Show all available commands
rdpsm --help

# Example: Create a user
rdpsm user create john -f "John Doe" -d xfce

# Example: List all users
rdpsm user list

# Example: View server information
rdpsm server info
```

For complete CLI documentation, see [CLI.md](CLI.md).

### Basic Operations (GUI)

#### Creating an RDP User
1. Click the "+" button in the header bar
2. Enter user details:
   - Username (lowercase letters, numbers, hyphens, underscores)
   - Full name
   - Password (minimum 8 characters)
   - Confirm password
3. Select desktop environment
4. Optionally enable desktop environment installation
5. Authenticate when prompted
6. Wait for user creation to complete

#### Connecting to RDP Session
1. Click the network icon on the user card
2. Select "Open FreeRDP"
3. Enter credentials:
   - Domain (optional, for Windows domains)
   - Password
4. Click "Connect"

Alternative connection methods:
```bash
# Linux (FreeRDP)
xfreerdp /v:SERVER_IP:3389 /u:USERNAME /cert:ignore

# Windows (Remote Desktop Connection)
# Enter in client: SERVER_IP:3389
```

#### Deleting a User
1. Click the trash icon on the user card
2. Confirm deletion
3. Authenticate when prompted

Note: All user data including home directory, configuration files, and active processes will be removed.

#### Enabling/Disabling Users
1. Toggle the switch next to the user status
2. Authenticate when prompted
3. Status will update to reflect the change

Disabled users cannot authenticate via RDP until re-enabled.

## Command Line Interface

RDP Session Manager includes a comprehensive CLI that provides access to all GUI functionality via terminal.

### Installation

The CLI is automatically available after installing the .deb package. The `rdpsm` command will be available system-wide.

### Quick Reference

**User Management:**
```bash
rdpsm user create USERNAME              # Create user
rdpsm user delete USERNAME              # Delete user
rdpsm user list                         # List all users
rdpsm user info USERNAME                # User details
rdpsm user enable USERNAME              # Enable user
rdpsm user disable USERNAME             # Disable user
rdpsm user password USERNAME            # Change password
```

**Session Management:**
```bash
rdpsm session list                      # Active sessions
rdpsm session info USERNAME             # Session details
rdpsm session kill USERNAME             # Kill session
```

**Desktop Environments:**
```bash
rdpsm de list                           # Available DEs
rdpsm de install DE_ID                  # Install DE
rdpsm de check DE_ID                    # Check if installed
```

**Server & Configuration:**
```bash
rdpsm server info                       # Server information
rdpsm server status                     # Check xrdp status
rdpsm config get port                   # Get RDP port
rdpsm config set port 3390              # Set RDP port
```

**Dependencies:**
```bash
rdpsm deps check                        # Check dependencies
rdpsm deps install xrdp                 # Install xrdp
rdpsm deps install freerdp              # Install freerdp
```

### Output Formats

Most commands support JSON output for scripting:

```bash
# Table format (default)
rdpsm user list

# JSON format
rdpsm user list --format json

# Use with jq for parsing
rdpsm user list --format json | jq -r '.[].username'
```

### Scripting Examples

**Batch user creation:**
```bash
for user in alice bob charlie; do
    rdpsm user create "$user" -p "TempPass123" -d xfce
done
```

**Monitor sessions:**
```bash
watch -n 5 'rdpsm session list'
```

**System health check:**
```bash
rdpsm server status && rdpsm deps check
```

### Testing CLI Commands

Test all CLI commands after installing the application:

```bash
# Run automated test suite (tests all safe read-only commands)
bash tests/test_cli.sh

# Manual testing
rdpsm --version
rdpsm user list
rdpsm server info
```

For complete CLI documentation, testing guide, and GUI-to-CLI equivalents, see:
- [CLI.md](CLI.md) - Complete CLI reference and usage guide
- [CLI_TESTING.md](CLI_TESTING.md) - Comprehensive testing guide with all commands and expected outputs

## Architecture

```
RemoteApps-RDP/
├── src/
│   ├── core/                    # Core functionality modules
│   │   ├── user_manager.py      # User account management
│   │   ├── rdp_config.py        # RDP configuration
│   │   ├── de_installer.py      # Desktop environment installer
│   │   ├── system_deps.py       # System dependency management
│   │   ├── session_monitor.py   # Session monitoring
│   │   └── config.py            # Application configuration
│   ├── ui/                      # GTK4 interface
│   │   ├── main_window.py       # Main application window
│   │   ├── user_dialog.py       # User creation dialog
│   │   └── preferences_dialog.py # Settings dialog
│   ├── utils/                   # Utility modules
│   │   ├── logger.py            # Logging system
│   │   ├── validator.py         # Input validation
│   │   └── polkit.py            # PolicyKit integration
│   ├── cli.py                   # Command-line interface
│   ├── application.py           # Main application class
│   └── main.py                  # GUI entry point
├── data/
│   ├── ui/                      # GTK Builder UI files
│   └── icons/                   # Application icons
├── helpers/                     # Privileged helper scripts
│   ├── install-packages.sh      # Package installation
│   ├── create-rdp-user.sh       # User creation
│   ├── delete-rdp-user.sh       # User deletion
│   ├── toggle-user-lock.sh      # User enable/disable
│   └── set-user-password.sh     # Password management
├── docs/                        # Documentation
├── tests/                       # Unit tests
│   └── test_cli.sh              # CLI test suite
├── CLI.md                       # CLI documentation
├── CLI_TESTING.md               # CLI testing guide
└── requirements.txt             # Python dependencies
```

## Security

### Privilege Escalation
The application uses PolicyKit (pkexec) for secure privilege escalation:
- User creation: `pkexec useradd`
- User deletion: `pkexec userdel`
- User lock/unlock: `pkexec usermod`
- Package installation: `pkexec apt-get`
- Process termination: `pkexec pkill`

Helper scripts in the `helpers/` directory group multiple privileged operations to minimize authentication prompts while maintaining security.

### User Isolation
- RDP users are created in a dedicated group (rdp-users)
- UIDs start at 5000, outside the normal user range
- Home directories are isolated in /opt/rdp-users/
- Each user operates on a dedicated RDP port

### Input Validation
- Username pattern: `^[a-z][a-z0-9_-]{2,31}$`
- Password requirements: minimum 8 characters, alphanumeric
- Port validation: range 1-65535, availability check
- All system commands use absolute paths

## Logging

### Log Locations
```bash
# Application logs
~/.local/share/rdp-session-manager/logs/rdp-session-manager.log

# xrdp logs
/var/log/xrdp/

# Monitor logs in real-time
tail -f ~/.local/share/rdp-session-manager/logs/rdp-session-manager.log
```

### Log Contents
- User creation and deletion operations
- Package and desktop environment installations
- RDP connections and disconnections
- Error messages and warnings
- Process terminations
- System dependency checks

## Troubleshooting

### xrdp Not Installed
**Symptom**: Warning banner displayed in application window

**Solution**:
- Click "Install Now" in the banner, or
- Manual installation: `sudo apt install xrdp xorgxrdp`

### FreeRDP Not Available
**Symptom**: Installation prompt when attempting to connect

**Solution**:
- Click "Install FreeRDP" in the dialog, or
- Manual installation: `sudo apt install freerdp2-x11`

### Desktop Environment Not Starting
**Symptom**: Black screen after RDP connection

**Solution**:
1. Check xrdp logs: `tail /var/log/xrdp/xrdp.log`
2. Test desktop environment: `su - username -c "startxfce4"`
3. Reinstall desktop environment via application

### Port Conflicts
**Symptom**: Error during user creation

**Solution**: The application automatically detects and assigns available ports. Check firewall rules if issues persist.

## Development

### Running Tests
```bash
# Using pytest
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Code Style
The project follows PEP 8 guidelines. Use the following tools:
```bash
# Format code
black src/

# Check style
flake8 src/

# Type checking
mypy src/
```

## Contributing

Contributions are welcome. Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/description`)
3. Commit your changes (`git commit -m 'Add feature description'`)
4. Push to the branch (`git push origin feature/description`)
5. Open a Pull Request

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.

## Support

- Documentation: [docs/](docs/)
- Bug Reports: GitHub Issues
- Discussions: GitHub Discussions

## Version Information

**Current Version**: 0.3.0
**Status**: Production Ready
**Last Updated**: 2025-10-30

---

Copyright (C) 2025 - RDP Session Manager Contributors
