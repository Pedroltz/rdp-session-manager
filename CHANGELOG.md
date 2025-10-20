# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2025-10-18

### Summary

This release adds essential features that make the application fully functional, including intelligent user deletion, complete FreeRDP management, visual credential dialogs, automatic xrdp installation, and comprehensive logging across all modules.

### Added

- **Intelligent User Deletion**
  - Automatic detection of active processes via `get_user_processes()`
  - Graceful process termination (SIGTERM) before deletion
  - Forced termination (SIGKILL) if processes do not respond
  - Special warning dialog when user has active sessions
  - Complete data removal including account, home directory, configurations, and processes

- **Complete FreeRDP Management**
  - Automatic detection of FreeRDP installation status
  - Binary verification using `shutil.which('xfreerdp3')` and `shutil.which('xfreerdp')`
  - Installation dialog when FreeRDP not found
  - Automatic installation of `freerdp3-x11` via pkexec
  - Visual progress feedback during installation
  - Support for both xfreerdp3 and xfreerdp (fallback)

- **Visual Dialog for RDP Credentials**
  - Graphical interface for credential entry
  - Optional domain field for Windows domain authentication
  - Password field with hidden characters
  - Enter key navigation (domain → password → connect)
  - Mandatory password validation
  - Credentials passed via `/d:` and `/p:` command-line parameters

- **xrdp Verification and Installation**
  - Automatic xrdp verification on application startup
  - Warning banner displayed if xrdp not installed
  - One-click installation via "Install Now" button
  - Dialog with real-time progress for installation
  - Automatic installation of `xrdp` and `xorgxrdp` packages
  - Automatic service enablement and startup
  - Periodic status updates every 10 seconds
  - User creation blocked when xrdp is not installed

- **Comprehensive Logging System**
  - ROOT logger configuration to capture all modules
  - Logging from `core.user_manager`, `core.rdp_config`, `core.de_installer`
  - Logging from `core.system_deps`, `core.session_monitor`
  - Logging from `ui.main_window`, `ui.user_dialog`
  - Centralized log file
  - Automatic log rotation (10MB maximum, 5 backups)

- **Dynamic Desktop Environment Detection**
  - Automatic detection by reading `.xsession` file
  - Mapping of startup commands to DE identifiers
  - Support for LXDE, LXQt, XFCE, MATE, Cinnamon, GNOME, KDE
  - Automatic RDP port calculation based on UID
  - Accurate DE display in interface (eliminates hardcoded values)

- **Updated Documentation**
  - Complete README.md rewrite with all features
  - STATUS.md with test results and statistics
  - Structured and detailed CHANGELOG.md
  - Step-by-step usage instructions
  - ASCII art screenshots of dialogs

### Fixed

- **pkexec with Absolute Paths** (Critical)
  - **Issue**: Commands failing with exit code 127 "command not found"
  - **Cause**: pkexec does not include `/usr/sbin` in PATH
  - **Solution**: All system commands now use absolute paths:
    - `/usr/sbin/groupadd`, `/usr/sbin/useradd`, `/usr/sbin/userdel`
    - `/usr/sbin/chpasswd`
    - `/usr/bin/apt-get`, `/usr/bin/systemctl`
    - `/usr/bin/mkdir`, `/usr/bin/chmod`, `/usr/bin/pkill`
    - `/usr/bin/bash`, `/usr/bin/cp`, `/usr/bin/chown`

- **Password Field Focus Issues**
  - **Issue**: Focus automatically returned to password field, preventing domain input
  - **Cause**: `GLib.timeout_add()` continuously stealing focus
  - **Solution**: Removed timeout, added `set_can_focus(True)` to both fields

- **Single Character Password Entry**
  - **Issue**: `Adw.PasswordEntryRow` not functioning within `Adw.MessageDialog`
  - **Solution**: Replaced with `Gtk.Entry()` using `set_visibility(False)`

- **Connected User Deletion Error**
  - **Issue**: "user is currently used by process XXXX" error
  - **Solution**: Implemented automatic process termination before deletion

- **Incorrect Desktop Environment Display**
  - **Issue**: All users displayed as "XFCE • Port 3389" regardless of actual DE
  - **Cause**: Hardcoded values in `list_users()` (`desktop_env="xfce"`, `rdp_port=3389`)
  - **Solution**: Implemented dynamic detection by reading `.xsession` and calculating port from UID

- **Desktop Environment Showing as "Unknown"**
  - **Issue**: DE detection failed even after implementation
  - **Cause**: Home directory permissions (700) prevented `.xsession` file access
  - **Solution**: Home directories now created with 751 permissions (rwxr-x--x) allowing `.xsession` access

### Changed

- **Contextual Deletion Confirmation**
  - Different dialogs based on user state:
    - **Inactive user**: Detailed list of items to be removed
    - **Active user**: Warning about session termination
  - More descriptive buttons: "Terminate and Remove" vs "Remove"

- **Enhanced Visual Feedback**
  - Toast notification "Terminating sessions..." for connected users
  - Toast notification "Removing user..." for inactive users
  - Detailed error dialog on failure
  - Comprehensive logging for each deletion step

- **Simplified RDP Connection**
  - Connection in 3 clicks:
    1. Network button on user card
    2. "Open FreeRDP"
    3. Enter password and click "Connect"
  - Optional domain for users without Active Directory
  - Improved error handling

### Security

- **Process Validation**
  - Active process verification before deletion
  - Use of `pgrep -u` to list PIDs
  - Graceful termination before forcing

- **Absolute Path Commands**
  - Prevents path injection attacks
  - Ensures correct command execution
  - Compatibility across different distributions

### Modified Files

#### Core Modules
- `src/core/user_manager.py`:
  - Added `get_user_processes(username) -> List[int]`
  - Added `kill_user_processes(username, force=False) -> bool`
  - Modified `delete_user()` to accept `kill_processes=True`
  - Added `_detect_desktop_env(home_dir) -> str` for DE detection from `.xsession`
  - Added `_detect_rdp_port(uid) -> int` for UID-based port calculation
  - Modified `list_users()` to use dynamic detection instead of hardcoded values
  - Updated all commands to use absolute paths

- `src/core/system_deps.py`:
  - Added FreeRDP management to `REQUIRED_PACKAGES`
  - Added `is_freerdp_installed() -> bool`
  - Added `get_freerdp_command() -> str`
  - Updated all commands to use absolute paths

- `src/core/rdp_config.py`:
  - Updated commands to use absolute paths

- `src/core/de_installer.py`:
  - Updated commands to use absolute paths

#### UI Modules
- `src/ui/main_window.py`:
  - Modified `on_delete_user()` to check for active processes
  - Modified `confirm_delete_user()` to terminate processes
  - Added `show_password_dialog(user)` for visual credentials
  - Added `on_password_dialog_response()` to process credentials
  - Modified `launch_freerdp_client()` to accept domain parameter
  - Added `handle_connect_response()` to verify FreeRDP
  - Added `on_freerdp_install_response()` to install FreeRDP
  - Added `create_xrdp_warning_banner()` for warning display
  - Added `update_xrdp_status()` for periodic verification
  - Added `on_install_xrdp_clicked()` for xrdp installation

- `src/application.py`:
  - Added `show_xrdp_install_dialog()` for installation with progress
  - Added `install_freerdp_with_progress()` for FreeRDP installation

#### Utilities
- `src/utils/logger.py`:
  - Modified `setup_logger()` to configure ROOT logger
  - Now captures logs from ALL modules

### Testing

- User creation: **PASSED**
- Inactive user deletion: **PASSED**
- Active user deletion (58 processes): **PASSED**
- RDP connection with visual credentials: **PASSED**
- Automatic FreeRDP installation: **PASSED**
- Automatic xrdp installation: **PASSED**
- Comprehensive logging system: **PASSED**

---

## [0.1.0] - 2025-10-17

### Summary

Initial functional release of RDP Session Manager with all base features implemented.

### Added

- GTK4 interface with libadwaita
- RDP user management system
- User creation with validation
- Support for 7 Desktop Environments:
  - LXDE, LXQt, XFCE, MATE, Cinnamon, GNOME, KDE Plasma
- Automatic Desktop Environment installation
- Logging and audit system
- PolicyKit for administrative operations
- Backup and restore system
- Unit tests
- Complete documentation
- Active session monitoring
- Toast notifications for feedback
- Empty state when no users exist
- RDP connection button on each user card
- Automatic IP copying to clipboard

### Fixed

- libadwaita version from '1.0' to '1' (Debian 13 compatibility)
- `Gtk.Widget.get_default_display()` replaced with `Gdk.Display.get_default()`
- `psutil.process_iter(['connections'])` error fixed using `proc.connections()`
- Added `python3-psutil` to dependencies

### Known Issues

- Group `rdp-users` needs manual creation (fixed in v0.2.0)
- GTK warnings about label measurement are cosmetic
- GTK template binding warnings do not affect operation

### Compatibility

Tested on:
- Debian 13 (Trixie)
- GTK 4.18.6
- libadwaita 1.7.6
- Python 3.13

---

## [Unreleased]

### Planned for v0.3.0
- Disk quotas per user
- Resource limits (CPU/RAM) per session with cgroups
- Restrictive AppArmor profiles
- Real-time action auditing
- Automatic daily backup

### Planned for v0.4.0
- Managed RDP port pool
- Async UI for better responsiveness
- Operation caching
- RDP network optimizations
- Resource usage dashboard

### Planned for v1.0.0
- LDAP/Active Directory authentication
- Web administration interface
- REST API
- Clustering/load balancing support
- Configuration templates
- Cockpit integration
- Advanced metrics and dashboards

---

## Changelog Format

### Change Types
- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for removed features
- `Fixed` for bug fixes
- `Security` for vulnerability fixes

---

**Maintainer**: Pedro L. Tunin
**Last Updated**: 2025-10-18
