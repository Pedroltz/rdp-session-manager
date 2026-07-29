# Changelog

All notable changes to this project will be documented in this file.

---

## [0.3.0] - 2025-10-30

### Summary

Major release introducing user configuration management and RemoteApp support, allowing administrators to modify user settings and run single applications instead of full desktop environments through RDP connections.

### Added

#### User Configuration Management
- **Settings Dialog** accessible via user context menu ("...")
  - Change username with automatic home directory migration
  - Update full name (GECOS field)
  - Reset password with confirmation
  - Real-time input validation
  - Requires pkexec authentication

- **New UserManager Methods**:
  - `rename_user(old_username, new_username)` - Atomic username change with home directory move
  - `change_user_fullname(username, new_fullname)` - Update display name
  - `change_password(username, new_password)` - Password reset (already implemented, enhanced)

- **Helper Scripts**:
  - `helpers/rename-user.sh` - System-level username changes with process termination
  - `helpers/change-user-fullname.sh` - GECOS field updates
  - `helpers/change-session-type.sh` - Switch between desktop/RemoteApp modes

#### RemoteApp Support
- **Single Application Mode** - Launch individual apps instead of full desktop
  - Custom application command input (no predefined list)
  - Optional command arguments field
  - Session type selection during user creation
  - Switch between desktop/RemoteApp in settings dialog

- **Window Management**:
  - Uses OpenBox window manager for RemoteApp sessions
  - Automatic window maximization on launch
  - Borderless windows for clean appearance
  - Dynamic resolution adjustment with `/dynamic-resolution`

- **Backend Implementation**:
  - New RDPUser fields: `session_type`, `app_command`, `app_args`
  - Modified `create_user()` to support RemoteApp parameters
  - `change_user_session_type()` method for mode switching
  - Enhanced `_detect_session_info()` to identify RemoteApp sessions

- **Session Configuration**:
  - Generates `.xsession` with OpenBox + application command
  - Separate configurations for desktop vs RemoteApp modes
  - D-Bus session support for both modes

### Changed

- **UI Simplifications**:
  - Removed predefined application list (COMMON_REMOTE_APPS)
  - Single text field for custom application commands
  - Cleaner RemoteApp configuration interface

- **Code Optimizations**:
  - Moved `import time` to module top-level
  - Simplified password masking in command logging (list comprehension)
  - Refactored `launch_freerdp_client()` for better readability
  - Improved `_detect_session_info()` to detect OpenBox sessions
  - Extracted `is_remoteapp` variable to avoid duplicate checks

- **FreeRDP Integration**:
  - Removed unused `/app:` parameter (incompatible with xrdp)
  - Session type controlled server-side via `.xsession` configuration
  - Consistent `/dynamic-resolution` for all connection types

### Fixed

- **Session Detection**: Enhanced to recognize OpenBox-based RemoteApp sessions
- **Code Cleanup**: Removed 17-line unused COMMON_REMOTE_APPS constant
- **Import Organization**: Eliminated inline imports in function bodies

### Dependencies

- Added `openbox` - Lightweight window manager for RemoteApp
- Added `wmctrl` - Window control utility (optional, for debugging)

### Technical Details

**Modified Files**:
- `src/core/user_manager.py` - Enhanced with RemoteApp support and rename functionality
- `src/ui/main_window.py` - Settings dialog, RemoteApp display, optimized FreeRDP launcher
- `src/ui/user_dialog.py` - Session type selection, simplified app input
- `data/ui/user-dialog.ui` - RemoteApp UI elements with visibility toggle
- `helpers/create-rdp-user.sh` - OpenBox integration for RemoteApp sessions
- `helpers/change-session-type.sh` - Mode switching between desktop/RemoteApp

**Session File Example** (RemoteApp):
```bash
#!/bin/bash
export HOME=/opt/rdp-users/username
export USER=username

eval $(dbus-launch --sh-syntax --exit-with-session)

# OpenBox config for fullscreen windows
mkdir -p $HOME/.config/openbox
cat > $HOME/.config/openbox/rc.xml <<EOF
<openbox_config>
  <applications>
    <application class="*">
      <maximized>yes</maximized>
      <decor>no</decor>
    </application>
  </applications>
</openbox_config>
EOF

openbox --config-file $HOME/.config/openbox/rc.xml &
sleep 1

exec firefox
```

### Testing

All 109 unit tests passing:
- `test_user_manager.py` - 12 tests
- `test_validator.py` - 19 tests
- `test_session_monitor.py` - 19 tests
- `test_config.py` - 16 tests
- `test_logger.py` - 23 tests
- `test_backup.py` - 20 tests

**Manual Testing**:
- User creation with RemoteApp (firefox)
- Session type switching (desktop ↔ RemoteApp)
- Username rename with active sessions
- Full name modification
- Password reset with confirmation
- RemoteApp window maximization
- FreeRDP connection to RemoteApp users

### Security

- All user modifications require pkexec authentication
- Password changes with confirmation to prevent typos
- Username validation prevents conflicts
- Safe atomic operations with rollback on failure
- Session termination before critical changes (username rename)

### Example Usage

**Create RemoteApp User**:
1. Click "New User"
2. Select "RemoteApp (Single App)"
3. Enter command: `firefox`
4. Optional args: `--private-window`
5. Create user

**Change User Settings**:
1. Click "..." menu next to user
2. Select "User Settings"
3. Modify username, full name, or password
4. Click "Save Changes"
5. Authenticate with pkexec

**Switch Session Type**:
1. Open user settings
2. Change "Session Type" dropdown
3. For RemoteApp: enter application command
4. Save changes (will terminate active sessions)

---

**Version**: 0.3.0
**Release Date**: 2025-10-30
**Maintainer**: Pedro L. Tunin
