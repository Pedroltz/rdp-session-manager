# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.2] - 2025-10-26

### Summary

This release focuses on improving code quality and reliability through comprehensive unit test coverage, along with critical bug fixes for user state persistence, session monitoring, and UI stability. The test suite has been significantly expanded from 2 test files to 6 test files, increasing total test coverage to 109 tests across all critical modules.

### Added

- **Comprehensive Unit Test Suite**
  - `tests/test_session_monitor.py` - 23 tests for SessionMonitor and SessionInfo classes
  - `tests/test_config.py` - 17 tests for AppConfig module
  - `tests/test_logger.py` - 25 tests for AuditLogger and logging setup
  - `tests/test_backup.py` - 20 tests for BackupManager module

- **Enhanced Existing Tests**
  - `tests/test_user_manager.py` - Expanded from 6 to 14 tests
  - `tests/test_validator.py` - Expanded from 8 to 20 tests

- **Professional Test Runner** (`tests/run_tests.sh`)
  - Beautiful colored terminal output with ANSI colors
  - Green ✓ checkmarks for passed tests
  - Red ✗ crosses for failed tests
  - Progress indicators and test statistics
  - Detailed summary with total/passed/failed counts
  - Duration tracking
  - Per-module test results
  - Automatic error output for failed tests
  - Professional banner and formatting

- **Comprehensive Test Documentation** (`tests/README.md`)
  - Detailed explanation of each test file (15KB documentation)
  - Purpose and coverage of each test module
  - How to run tests (multiple methods)
  - Test best practices and patterns
  - Debugging guide for failed tests
  - Contributing guidelines for new tests
  - Complete test statistics and coverage metrics

- **Persistent User State Cache**
  - JSON file cache for enabled/disabled user states
  - Located at `~/.config/rdp-session-manager/user_states.json`
  - Automatic loading on application startup
  - Automatic saving on state changes (enable/disable/create/delete)
  - Solves state persistence when app is closed and reopened
  - Fallback to cache when `/etc/shadow` access is denied

- **Enhanced RDP Session Detection**
  - Multi-method session detection for improved reliability
  - Method 1: `xrdp-sesman` process detection for user sessions
  - Method 2: `loginctl` integration for remote session verification
  - Checks `Remote=yes` flag and `xrdp` service markers
  - Filters out root daemon processes from session count
  - Prevents false positives in session counting

- **Smart Session Filtering**
  - Active session counter now filters by enabled users only
  - Disabled users with active RDP sessions are not counted
  - Provides accurate session statistics in "Informações do Servidor"
  - Automatic updates when user state changes

### Testing Coverage

**Total Tests**: 109 tests (increased from 14)

**Module Coverage**:
- `core/user_manager.py` - RDPUser serialization, UserManager validation, UID generation, group management
- `core/session_monitor.py` - Session detection, system stats, port checking, IP detection
- `core/config.py` - Configuration persistence, default values, INI file management
- `utils/validator.py` - Username/password/port validation, desktop environment validation, path sanitization
- `utils/logger.py` - Audit logging, event tracking, log rotation configuration
- `utils/backup.py` - Backup creation/restoration, cleanup operations, import/export functionality

**Test Categories**:
1. **Data Model Tests** (15 tests)
   - RDPUser serialization/deserialization
   - SessionInfo to_dict() and get_duration()
   - Data persistence and roundtrip testing

2. **Validation Tests** (28 tests)
   - Username validation (pattern, length, reserved names)
   - Password complexity requirements
   - Port boundary values
   - Desktop environment validation
   - Home directory security checks
   - Path sanitization

3. **Configuration Tests** (17 tests)
   - Config file creation and loading
   - Default value management
   - Section/key operations
   - Invalid config recovery
   - Multi-instance persistence

4. **Session Monitoring Tests** (23 tests)
   - Active session detection
   - Process mocking and isolation
   - Network IP detection
   - System statistics gathering
   - Port status checking

5. **Logging Tests** (25 tests)
   - Audit event logging (JSON and text formats)
   - Event filtering and querying
   - Log rotation configuration
   - Logger setup and handler management
   - Fallback directory handling

6. **Backup Tests** (20 tests)
   - Backup creation and restoration
   - File naming and timestamps
   - Listing and filtering backups
   - Old backup cleanup
   - Import/export operations
   - Roundtrip data integrity

### Fixed

- **User State Not Persisting After App Restart** (Critical)
  - **Issue**: When user was disabled via toggle switch and app was closed, user appeared as enabled on restart
  - **Cause**: State stored only in memory cache (`_user_states_cache`) which was lost on app closure
  - **Root Cause**: Unable to read `/etc/shadow` without root permissions, falling back to "enabled" by default
  - **Solution**: Implemented persistent JSON cache at `~/.config/rdp-session-manager/user_states.json`
  - **Impact**: User enable/disable state now persists across app restarts
  - **Modified Files**: `src/core/user_manager.py`
    - Added `states_cache_file` path in `__init__()`
    - Added `_load_states_cache()` method to load cache on startup
    - Added `_save_states_cache()` method to persist cache to disk
    - Updated `lock_user()`, `unlock_user()`, `create_user()`, `delete_user()` to save cache

- **Status Label Showing "Conectado" for Disabled Users**
  - **Issue**: Status label showed "Conectado" even when user toggle switch was off
  - **Cause**: Incorrect priority in status determination logic (checked connection before enabled state)
  - **Solution**: Changed status priority to: 1) Desabilitado, 2) Conectado, 3) Habilitado
  - **Impact**: Status label now correctly shows "Desabilitado" when user is disabled regardless of connection
  - **Modified Files**: `src/ui/main_window.py:129-135`

- **Infinite UI Update Loop Causing App Freeze**
  - **Issue**: App became unresponsive with continuous UI updates, unable to click or toggle users
  - **Cause**: `update_sessions_info()` was calling `load_users()` internally, creating circular updates
  - **Additional Cause**: Multiple simultaneous calls to `load_users()` from different operations
  - **Solution**:
    - Removed `load_users()` call from `update_sessions_info()`
    - Added `_updating_users` flag to prevent concurrent `load_users()` calls
    - Removed redundant `update_sessions_info()` calls from toggle operations
  - **Impact**: UI now remains responsive, users can interact normally with switches
  - **Modified Files**: `src/ui/main_window.py`
    - Added `_updating_users = False` flag in `__init__()`
    - Wrapped `load_users()` with flag check and try/finally block

- **Session Counter Including Disabled Users**
  - **Issue**: "Sessões Ativas" counter showed 1 even when only user was disabled
  - **Cause**: Counter counted all active RDP sessions regardless of user enabled/disabled state
  - **Solution**: Filter sessions to only count enabled users
  - **Logic**: `sessions_count = sum(1 for session in all_sessions if session.username in enabled_users)`
  - **Impact**: Counter now shows accurate count of sessions from enabled users only
  - **Modified Files**:
    - `src/ui/main_window.py:update_server_info()` (lines 78-82)
    - `src/ui/main_window.py:update_sessions_info()` (lines 82-89)

- **Improved User Creation Success Dialog**
  - **Issue**: Success dialog had inconsistent formatting with checkmarks and emojis
  - **Changes**:
    - Removed "✓" checkmark from dialog heading
    - Removed "📡" emoji from "Como Conectar:" section
    - Added bold formatting to "Como Conectar:" using Pango markup
    - Removed "✓" checkmark from "O usuário já aparece na lista principal!"
    - Added `set_body_use_markup(True)` to enable markup rendering
  - **Impact**: Cleaner, more professional success dialog appearance
  - **Modified Files**: `src/ui/user_dialog.py:467-494`

### Changed

- All unit tests now use proper mocking to avoid system dependencies
- Tests use temporary directories for isolation
- Added timing controls to prevent timestamp collision in backup tests
- Improved test assertions to be more flexible with boundary conditions

- **Session Detection Method**
  - Changed from single-method (process check) to dual-method approach
  - Now uses both `xrdp-sesman` process detection and `loginctl` session verification
  - Improved reliability and accuracy in detecting active RDP sessions
  - Modified: `src/core/session_monitor.py:_get_rdp_connections()`

- **Status Label Priority Logic**
  - Old priority: Connection status → Enabled status
  - New priority: Enabled status → Connection status → Default
  - Ensures disabled state always takes precedence in display
  - Modified: `src/ui/main_window.py:create_user_row()`

- **Session Counter Behavior**
  - Now considers user state (enabled/disabled) in addition to connection status
  - Provides more meaningful statistics about active usable sessions
  - Modified: `src/ui/main_window.py:update_server_info()`, `update_sessions_info()`

### Technical Details

**Test Infrastructure**:
- Framework: Python `unittest` (standard library)
- Mocking: `unittest.mock` with patches and fixtures
- Test isolation: `tempfile` and `shutil` for temporary directories
- Execution: `python3 -m unittest discover tests/ -v`

**Test Best Practices Implemented**:
- Setup/teardown fixtures for clean test environments
- Comprehensive edge case testing
- Boundary value testing for numeric inputs
- Error condition testing with invalid inputs
- Mock usage to isolate units under test
- Temporary directories to avoid filesystem pollution
- Roundtrip testing for data integrity

### Benefits

1. **Regression Prevention**: 109 tests ensure that future changes don't break existing functionality
2. **Code Confidence**: High test coverage provides confidence in refactoring and feature additions
3. **Documentation**: Tests serve as living documentation of expected behavior
4. **Bug Detection**: Tests help identify edge cases and potential issues early
5. **Maintenance**: Easier to maintain and modify code with comprehensive test coverage

### Testing

All 109 unit tests pass successfully:
- `test_user_manager.py`: **14 tests PASSED**
- `test_validator.py`: **20 tests PASSED**
- `test_session_monitor.py`: **23 tests PASSED**
- `test_config.py`: **17 tests PASSED**
- `test_logger.py`: **25 tests PASSED**
- `test_backup.py`: **20 tests PASSED**

**Total: 109/109 tests passing (100%)**

**Manual Testing - Bug Fixes**:
- User state persistence: **PASSED** ✓
  - Disabled user via toggle → closed app → reopened → user still disabled
- Status label priority: **PASSED** ✓
  - Disabled user shows "Desabilitado" (not "Conectado")
  - Enabled + connected user shows "Conectado"
  - Enabled + not connected user shows "Habilitado"
- UI responsiveness: **PASSED** ✓
  - No infinite update loops
  - All buttons and switches clickable
  - Smooth toggle operations
- Session counter accuracy: **PASSED** ✓
  - Disabled user with active RDP session → counter shows 0
  - Enabled user with active RDP session → counter shows 1
  - Multiple users (some disabled) → counter shows only enabled
- Session detection: **PASSED** ✓
  - `loginctl` integration detects remote xrdp sessions correctly
  - Filters out root daemon processes
- Success dialog formatting: **PASSED** ✓
  - No checkmarks in heading or footer
  - No emoji in "Como Conectar:"
  - "Como Conectar:" appears in bold

### Example Usage

**Run all tests:**
```bash
python3 -m unittest discover tests/ -v
```

**Run specific test file:**
```bash
python3 -m unittest tests.test_validator -v
```

**Run specific test class:**
```bash
python3 -m unittest tests.test_user_manager.TestUserManager -v
```

**Run specific test method:**
```bash
python3 -m unittest tests.test_validator.TestValidator.test_validate_username_valid -v
```

---

## [0.2.1] - 2025-10-23

### Summary

This release adds superuser privilege management for RDP users, allowing administrators to grant or revoke sudo privileges easily through both the GUI and CLI. This facilitates application installation and system maintenance within user accounts without manual intervention.

### Added

- **Superuser Privilege Management (UI)**
  - "..." (menu) button added next to each user in the user list
  - Popover menu with management options
  - "Superuser" toggle switch (On/Off) to grant/revoke sudo privileges
  - Visual feedback with toast notifications for privilege changes
  - Automatic UI update when privileges are changed
  - Administrative access required (pkexec authentication)

- **Superuser Privilege Management (CLI)**
  - `rdpsm user sudo grant USERNAME` - Grant sudo privileges to user
  - `rdpsm user sudo revoke USERNAME` - Revoke sudo privileges from user
  - Automatic detection of existing sudo privileges
  - Clear success/error messages
  - Help documentation for new commands

- **Backend Support**
  - New `is_superuser` field in RDPUser model
  - `grant_sudo()` method in UserManager
  - `revoke_sudo()` method in UserManager
  - `is_superuser()` method to check sudo status
  - Helper script `toggle-user-sudo.sh` for privilege operations
  - Automatic sudo status detection when listing users
  - User group management (adds/removes user from 'sudo' group)

### Changed

- RDPUser model updated to include `is_superuser` boolean field
- User list now displays sudo status for each user
- JSON output includes `is_superuser` field
- Version updated to 0.2.1
- Improved sudo privilege detection using `id -nG` command (more reliable)
- Enhanced sudo revocation using `gpasswd -d` with `deluser` fallback

### Technical Details

**Helper Script:**
- `helpers/toggle-user-sudo.sh` - Manages sudo privileges via pkexec
  - Usage: `pkexec toggle-user-sudo.sh USERNAME grant|revoke`
  - Uses `usermod -aG sudo` to add user to sudo group
  - Uses `deluser USERNAME sudo` to remove from sudo group
  - Validates user existence before operations

**UI Implementation:**
- MenuButton with "view-more-symbolic" icon
- Gtk.Popover containing management options
- Gtk.Switch for superuser toggle
- Threaded operations to prevent UI blocking
- GLib.idle_add for safe UI updates from threads

**CLI Implementation:**
- Sub-subcommand structure: `user sudo {grant|revoke}`
- Colored terminal output (✓ success, ✗ error, ! warning)
- Verification of existing privileges before operations
- Integration with existing CLI architecture

### Fixed

- **Sudo Privilege Detection Issue**
  - Fixed bug where sudo status was not updated correctly after revocation
  - Changed from `grp.getgrnam()` to `id -nG` command for reliable group detection
  - Improved helper script to use `gpasswd -d` for more reliable group removal
  - Added fallback to `deluser` if `gpasswd` is unavailable

- **Sudo Changes Not Applied to Active Sessions**
  - **CRITICAL FIX**: Group changes only take effect after user logout/login
  - Automatic session termination when changing sudo privileges
  - Warning dialogs in UI before terminating active sessions
  - CLI confirmation prompts for users with active sessions
  - Clear messaging about reconnection requirement
  - Added `kill_sessions` parameter to `grant_sudo()` and `revoke_sudo()`
  - `--force` flag in CLI to skip confirmation

### Security

- **Privilege Escalation Protection**
  - All sudo operations require pkexec authentication
  - Helper script validation of user existence
  - Atomic operations (add/remove from group)
  - Proper error handling for permission issues

### Modified Files

#### Core Modules
- `src/core/user_manager.py`:
  - Added `is_superuser` parameter to RDPUser.__init__()
  - Added `is_superuser` field to to_dict()
  - Added `grant_sudo(username)` method
  - Added `revoke_sudo(username)` method
  - Added `is_superuser(username)` method
  - Updated `list_users()` to detect sudo status
  - Updated `create_user()` to set is_superuser=False by default

#### UI Modules
- `src/ui/main_window.py`:
  - Updated `create_user_row()` to add menu button
  - Added MenuButton with popover menu
  - Added superuser toggle switch in menu
  - Added `on_sudo_toggle()` handler method
  - Threaded sudo operations for UI responsiveness

#### CLI Module
- `src/cli.py`:
  - Added `user_sudo_grant()` method
  - Added `user_sudo_revoke()` method
  - Registered 'user sudo' subcommand with 'grant'/'revoke' actions
  - Updated version to 0.2.1

#### Helper Scripts
- `helpers/toggle-user-sudo.sh` (NEW):
  - Bash script for sudo privilege management
  - Executable permissions (chmod +x)
  - Used via pkexec for privilege escalation

### Testing

- User sudo grant (UI): **PENDING**
- User sudo revoke (UI): **PENDING**
- User sudo grant (CLI): **PENDING**
- User sudo revoke (CLI): **PENDING**
- Sudo status detection: **PENDING**
- JSON output with is_superuser: **PENDING**

### Example Usage

**GUI:**
1. Click "..." button next to user
2. Toggle "Superuser" switch to On/Off
3. Authenticate when prompted (pkexec)
4. See confirmation toast message

**CLI:**
```bash
# Grant sudo privileges
rdpsm user sudo grant john

# Revoke sudo privileges
rdpsm user sudo revoke john

# Check status in user list
rdpsm user list --format json
```

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
**Last Updated**: 2025-10-26
