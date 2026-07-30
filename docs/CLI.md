# CLI Reference - RDP Session Manager

Command-line interface for RDP Session Manager. All operations available in the GUI can be performed via terminal.

## Table of Contents

- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [User Management](#user-management)
- [Session Management](#session-management)
- [Desktop Environments](#desktop-environments)
- [Server Information](#server-information)
- [Configuration](#configuration)
- [Dependencies](#dependencies)
- [Output Formats](#output-formats)
- [GUI to CLI Equivalents](#gui-to-cli-equivalents)
- [Exit Codes](#exit-codes)
- [RemoteApp Mode](#remoteapp-mode)
- [Scripting Examples](#scripting-examples)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)
- [Testing the CLI](#testing-the-cli)

## Installation

When installed via the Debian package, the CLI is automatically available system-wide:

```bash
# After installing the .deb package
rdpsm --version

# Use from anywhere
rdpsm user list
```

## Basic Usage

```bash
# Show help
rdpsm --help

# Show version
rdpsm --version

# Verbose output
rdpsm -v <command>

# Command structure
rdpsm <command> <subcommand> [options]
```

## User Management

### Create User

Create a new RDP user with automatic configuration. Supports both full desktop sessions and RemoteApp (single application) mode.

#### Desktop Session (Full DE)

```bash
# Interactive (prompts for password)
rdpsm user create USERNAME

# With options
rdpsm user create USERNAME -f "Full Name" -d xfce

# Non-interactive (for scripts)
rdpsm user create USERNAME -p "password123" -d gnome -f "John Doe"

# Verbose output
rdpsm -v user create USERNAME
```

#### RemoteApp Session (Single Application)

```bash
# Create RemoteApp user with Firefox
rdpsm user create USERNAME -s remoteapp --app-command firefox

# RemoteApp with application arguments
rdpsm user create USERNAME -s remoteapp --app-command firefox --app-args "--private-window"

# RemoteApp with full options
rdpsm user create USERNAME -f "Full Name" -p "password123" \
  -s remoteapp --app-command thunderbird --app-args "--safe-mode"
```

**Options:**
- `-f, --fullname` - User's full name
- `-d, --desktop` - Desktop environment (default: xfce, used for desktop sessions)
- `-p, --password` - Password (prompts if not provided)
- `-s, --session-type` - Session type: `desktop` or `remoteapp` (default: desktop)
- `--app-command` - Application command for RemoteApp (e.g., firefox, thunderbird, libreoffice)
- `--app-args` - Application arguments for RemoteApp (e.g., --private-window)

**Desktop environments:** xfce, gnome, kde

**Example 1: Desktop Session**
```bash
# Create user 'john' with XFCE desktop
rdpsm user create john -f "John Smith" -d xfce

# Output:
# → Creating user 'john' with XFCE desktop...
# ✓ User 'john' created successfully
# → UID: 5000
# → Home: /opt/rdp-users/john
# → RDP Port: 3389
# → Session Type: Desktop (XFCE)
```

**Example 2: RemoteApp Session**
```bash
# Create RemoteApp user for Firefox
rdpsm user create webuser -f "Web User" -s remoteapp --app-command firefox

# Output:
# → Creating RemoteApp user 'webuser' with application: firefox
# ✓ User 'webuser' created successfully
# → UID: 5001
# → Home: /opt/rdp-users/webuser
# → RDP Port: 3390
# → Session Type: RemoteApp
# → Application: firefox
```

**Example 3: RemoteApp with Arguments**
```bash
# Create RemoteApp user for LibreOffice Writer
rdpsm user create docuser -f "Document User" -p "password123" \
  -s remoteapp --app-command libreoffice --app-args "--writer"

# Output:
# → Creating RemoteApp user 'docuser' with application: libreoffice --writer
# ✓ User 'docuser' created successfully
# → UID: 5002
# → Home: /opt/rdp-users/docuser
# → RDP Port: 3391
# → Session Type: RemoteApp
# → Application: libreoffice --writer
```

**GUI Equivalent:** Click "+" button → Fill form → Select session type → Click "Create"

---

### Delete User

Delete an RDP user and all associated data.

```bash
# Interactive (asks for confirmation)
rdpsm user delete USERNAME

# Force delete without confirmation
rdpsm user delete USERNAME --force
```

**Example:**
```bash
# Delete user 'john'
rdpsm user delete john

# Output:
# Delete user 'john' and all data? (yes/no): yes
# → Deleting user 'john'...
# ✓ User 'john' deleted successfully
```

**GUI Equivalent:** Click trash icon → Confirm deletion

---

### List Users

Display all RDP users.

```bash
# Table format (default)
rdpsm user list

# JSON format
rdpsm user list --format json
```

**Example output (table):**
```
RDP Users (3 total)
====================

Username             UID      Desktop    Port     Status
----------------------------------------------------------------------
john                 5000     XFCE       3389     Enabled
mary                 5001     GNOME      3389     Enabled
bob                  5002     KDE        3389     Disabled
```

**Example output (JSON):**
```json
[
  {
    "username": "john",
    "uid": 5000,
    "home_dir": "/opt/rdp-users/john",
    "desktop_env": "xfce",
    "rdp_port": 3389,
    "active": false,
    "enabled": true,
    "is_superuser": false
  }
]
```

**GUI Equivalent:** View main window user list

---

### User Information

Show detailed information about a specific user.

```bash
# Table format
rdpsm user info USERNAME

# JSON format
rdpsm user info USERNAME --format json
```

**Example:**
```bash
rdpsm user info john

# Output:
# User Information: john
# =======================
#   Username:     john
#   UID:          5000
#   Home:         /opt/rdp-users/john
#   Desktop:      XFCE
#   RDP Port:     3389
#   Status:       Enabled
#   Connected:    Yes (from 192.168.1.100)
#   Processes:    15
```

**GUI Equivalent:** View user card details

---

### Enable User

Enable a disabled user account.

```bash
rdpsm user enable USERNAME
```

**Example:**
```bash
rdpsm user enable john

# Output:
# → Enabling user 'john'...
# ✓ User 'john' enabled
```

**GUI Equivalent:** Toggle switch ON

---

### Disable User

Disable a user account (prevents RDP login).

```bash
rdpsm user disable USERNAME
```

**Example:**
```bash
rdpsm user disable john

# Output:
# → Disabling user 'john'...
# ✓ User 'john' disabled
```

**GUI Equivalent:** Toggle switch OFF

---

### Change Password

Change user password.

```bash
# Interactive (prompts for password)
rdpsm user password USERNAME

# Non-interactive
rdpsm user password USERNAME -p "newpassword"
```

**Example:**
```bash
rdpsm user password john

# Output:
# New password for john:
# Confirm password:
# → Changing password for 'john'...
# ✓ Password changed for 'john'
```

**GUI Equivalent:** User management → Change password

---

### List User Processes

Show all running processes for a user.

```bash
rdpsm user processes USERNAME
```

**Example:**
```bash
rdpsm user processes john

# Output:
# Processes for john (15 total)
# ==============================
#   PID: 1234
#   PID: 1235
#   PID: 1236
#   ...
```

**GUI Equivalent:** View user card → Process count

---

### Grant Sudo Privileges

Grant superuser (sudo) privileges to a user.

```bash
rdpsm user sudo grant USERNAME
```

**Example:**
```bash
rdpsm user sudo grant john

# Output:
# → Granting sudo privileges to 'john'...
# ✓ Sudo privileges granted to 'john'
# → User can now execute commands with sudo
```

**What this does:**
- Adds user to the 'sudo' group
- User can execute commands with `sudo` after entering their password
- Useful for installing applications and performing system maintenance

**GUI Equivalent:** Click "..." → Toggle "Superuser" switch ON

---

### Revoke Sudo Privileges

Revoke superuser (sudo) privileges from a user.

```bash
rdpsm user sudo revoke USERNAME
```

**Example:**
```bash
rdpsm user sudo revoke john

# Output:
# → Revoking sudo privileges from 'john'...
# ✓ Sudo privileges revoked from 'john'
# → User can no longer execute commands with sudo
```

**What this does:**
- Removes user from the 'sudo' group
- User can no longer execute commands with `sudo`
- Increases security by limiting user permissions

**GUI Equivalent:** Click "..." → Toggle "Superuser" switch OFF

---

## Session Management

### List Active Sessions

Display all active RDP sessions.

```bash
# Table format
rdpsm session list

# JSON format
rdpsm session list --format json
```

**Example:**
```bash
rdpsm session list

# Output:
# Active Sessions (2 total)
# ==========================
#
# Username             IP Address           Port
# --------------------------------------------------
# john                 192.168.1.100        3389
# mary                 192.168.1.101        3389
```

**GUI Equivalent:** View "Active Sessions" count in header

---

### Session Information

Show detailed session information for a user.

```bash
# Table format
rdpsm session info USERNAME

# JSON format
rdpsm session info USERNAME --format json
```

**Example:**
```bash
rdpsm session info john

# Output:
# Session Information: john
# ==========================
#   Username:     john
#   IP Address:   192.168.1.100
#   Port:         3389
#   Duration:     3600 seconds
```

**GUI Equivalent:** View user card when connected

---

### Kill Session

Terminate a user's active RDP session.

```bash
# Interactive (asks for confirmation)
rdpsm session kill USERNAME

# Force kill without confirmation
rdpsm session kill USERNAME --force
```

**How it works:**
- **Step 1:** Sends SIGTERM (-15) for graceful shutdown
- **Step 2:** Waits 2 seconds for processes to terminate
- **Step 3:** If processes remain, sends SIGKILL (-9) to force termination
- **Privileges:** Requires elevated privileges (uses `pkexec`)

**Example:**
```bash
rdpsm session kill john --force

# Output:
# → Killing session for 'john'...
# ℹ Some processes still running, forcing termination...
# ✓ Session killed for 'john'
```

**Note:** You will be prompted for your password via PolicyKit to authorize the session termination.

**GUI Equivalent:** Delete user with active session → "Terminate and Remove"

---

## Desktop Environments

### List Desktop Environments

Show all available desktop environments.

```bash
# Table format
rdpsm de list

# JSON format
rdpsm de list --format json
```

**Example:**
```bash
rdpsm de list

# Output:
# Available Desktop Environments
# ================================
#
# ID           Name                 Size       Installed
# ------------------------------------------------------------
# xfce         XFCE                 400MB      Yes
# gnome        GNOME                1200MB     Yes
# kde          KDE Plasma           1500MB     No
```

**GUI Equivalent:** Desktop Environment selector in user creation dialog

---

### Install Desktop Environment

Install a desktop environment.

```bash
# Install DE
rdpsm de install DE_ID

# Reinstall if already installed
rdpsm de install DE_ID --force

# Verbose output
rdpsm -v de install DE_ID
```

**Example:**
```bash
rdpsm de install xfce

# Output:
# → Installing XFCE desktop environment...
#   Checking disk space...
#   Downloading packages...
#   Installing packages...
# ✓ Desktop environment 'xfce' installed successfully
```

**GUI Equivalent:** User creation → Check "Install desktop environment" → Create

---

### Check Desktop Environment

Check if a desktop environment is installed.

```bash
rdpsm de check DE_ID
```

**Example:**
```bash
rdpsm de check xfce

# Output (if installed):
# ✓ Desktop environment 'xfce' is installed
# Exit code: 0

# Output (if not installed):
# → Desktop environment 'xfce' is not installed
# Exit code: 1
```

**GUI Equivalent:** Desktop environment list in user creation

---

## Server Information

### Server Info

Display server IP, port, and session count.

```bash
# Table format
rdpsm server info

# JSON format
rdpsm server info --format json
```

**Example:**
```bash
rdpsm server info

# Output:
# Server Information
# ===================
#   IP Address:       192.168.1.50
#   Default RDP Port: 3389
#   Active Sessions:  2
```

**GUI Equivalent:** View header information

---

### Server Status

Check if xrdp server is installed and running.

```bash
rdpsm server status
```

**Example:**
```bash
rdpsm server status

# Output (if running):
# ✓ xrdp server is installed and running
# Exit code: 0

# Output (if not running):
# ! xrdp server is not installed or not running
# Exit code: 1
```

**GUI Equivalent:** Check for xrdp warning banner

---

## Configuration

### Get Configuration

Retrieve configuration values.

```bash
rdpsm config get KEY
```

**Available keys:** port

**Example:**
```bash
rdpsm config get port

# Output:
# 3389
```

**GUI Equivalent:** Hamburger menu → Settings → View port

---

### Set Configuration

Change configuration values.

```bash
rdpsm config set KEY VALUE
```

**Example:**
```bash
rdpsm config set port 3390

# Output:
# ✓ Default RDP port set to 3390
```

**GUI Equivalent:** Hamburger menu → Settings → Change port → Save

---

## Dependencies

### Check Dependencies

Verify system dependencies installation status.

```bash
# Table format
rdpsm deps check

# JSON format
rdpsm deps check --format json
```

**Example:**
```bash
rdpsm deps check

# Output:
# System Dependencies
# ====================
#
# Installed:
#   ✓ xrdp
#   ✓ python3
#   ✓ gtk4
#
# Missing:
#   ✗ freerdp
#
# ! Some dependencies are missing
# Exit code: 1
```

**GUI Equivalent:** View warning banners and dependency dialogs

---

### Install Dependency

Install a system dependency.

```bash
# Install package
rdpsm deps install PACKAGE

# Verbose output
rdpsm -v deps install PACKAGE
```

**Available packages:** xrdp, freerdp

**Example:**
```bash
rdpsm deps install xrdp

# Output:
# → Installing xrdp...
#   Updating package lists...
#   Installing xrdp...
#   Configuring xrdp...
# ✓ Package 'xrdp' installed successfully
```

**GUI Equivalent:** Click "Install Now" in banner or dependency dialog

---

## Output Formats

Most commands support multiple output formats:

### Table Format (Default)

Human-readable table output with colors.

```bash
rdpsm user list
rdpsm user list --format table
```

### JSON Format

Machine-readable JSON output (useful for scripts).

```bash
rdpsm user list --format json
rdpsm session list --format json
rdpsm server info --format json
```

**Parsing JSON in scripts:**
```bash
# Get all usernames
rdpsm user list --format json | jq -r '.[].username'

# Count enabled users
rdpsm user list --format json | jq '[.[] | select(.enabled==true)] | length'

# Get server IP
rdpsm server info --format json | jq -r '.ip'
```

---

## GUI to CLI Equivalents

Complete mapping of GUI operations to CLI commands:

| GUI Operation | CLI Command |
|---------------|-------------|
| Click "+" to add user | `rdpsm user create USERNAME` |
| Delete user (trash icon) | `rdpsm user delete USERNAME` |
| View user list | `rdpsm user list` |
| Toggle user enabled/disabled | `rdpsm user enable/disable USERNAME` |
| Grant sudo privileges (... menu) | `rdpsm user sudo grant USERNAME` |
| Revoke sudo privileges (... menu) | `rdpsm user sudo revoke USERNAME` |
| View server info in header | `rdpsm server info` |
| Hamburger → Settings → Get port | `rdpsm config get port` |
| Hamburger → Settings → Set port | `rdpsm config set port VALUE` |
| Install xrdp banner | `rdpsm deps install xrdp` |
| Install FreeRDP dialog | `rdpsm deps install freerdp` |
| Install DE during user creation | `rdpsm de install DE_ID` |
| View available DEs | `rdpsm de list` |
| Check active sessions count | `rdpsm session list` |
| Terminate session | `rdpsm session kill USERNAME` |
| Change user password | `rdpsm user password USERNAME` |

---

## Exit Codes

The CLI uses standard exit codes:

- **0** - Success
- **1** - Error or failure

**Example in scripts:**
```bash
#!/bin/bash

if rdpsm user create testuser -p "password123"; then
    echo "User created successfully"
else
    echo "Failed to create user"
    exit 1
fi
```

---

## RemoteApp Mode

RDP Session Manager supports RemoteApp mode, which allows users to run a single application instead of a full desktop environment. This is useful for:
- Providing access to specific applications only
- Reducing resource usage (no full DE required)
- Simplified user experience
- Application isolation

### Creating RemoteApp Users

```bash
# Basic RemoteApp user
rdpsm user create appuser -s remoteapp --app-command firefox

# With full options
rdpsm user create appuser -f "Application User" -p "SecurePass123" \
  -s remoteapp --app-command firefox --app-args "--private-window"
```

### Supported Applications

RemoteApp works with any GUI application installed on the server:

**Web Browsers:**
```bash
rdpsm user create webuser -s remoteapp --app-command firefox
rdpsm user create chromeuser -s remoteapp --app-command chromium
```

**Office Applications:**
```bash
rdpsm user create writeruser -s remoteapp --app-command libreoffice --app-args "--writer"
rdpsm user create calcuser -s remoteapp --app-command libreoffice --app-args "--calc"
```

**Email Clients:**
```bash
rdpsm user create mailuser -s remoteapp --app-command thunderbird
```

**Other Applications:**
```bash
rdpsm user create termuser -s remoteapp --app-command gnome-terminal
rdpsm user create edituser -s remoteapp --app-command gedit
```

### RemoteApp Features

- **Fullscreen Mode**: Applications automatically open in fullscreen/maximized mode
- **Dynamic Resolution**: Applications adapt to client screen size
- **OpenBox Window Manager**: Lightweight WM provides better fullscreen experience
- **Custom Commands**: Any installed application can be used

### Connecting to RemoteApp

Connect the same way as desktop sessions:

```bash
# From Linux
xfreerdp /v:SERVER_IP:PORT /u:USERNAME /cert:ignore

# From Windows
# Use Remote Desktop Connection with SERVER_IP:PORT
```

The application will launch automatically in fullscreen when connected.

---

## Scripting Examples

### Batch User Creation

**Desktop Users:**
```bash
#!/bin/bash
# Create multiple desktop users from a file

while IFS=',' read -r username fullname; do
    rdpsm user create "$username" -f "$fullname" -p "ChangeMe123"
    if [ $? -eq 0 ]; then
        echo "Created: $username"
    else
        echo "Failed: $username"
    fi
done < users.csv
```

**RemoteApp Users:**
```bash
#!/bin/bash
# Create multiple RemoteApp users with different applications

# Array of users: username,fullname,app_command,app_args
declare -a users=(
    "webuser1,Web User 1,firefox,"
    "webuser2,Web User 2,firefox,--private-window"
    "officeuser,Office User,libreoffice,--writer"
    "mailuser,Mail User,thunderbird,"
)

for user_data in "${users[@]}"; do
    IFS=',' read -r username fullname app_cmd app_args <<< "$user_data"

    echo "Creating RemoteApp user: $username ($app_cmd)"
    if [ -z "$app_args" ]; then
        rdpsm user create "$username" -f "$fullname" -p "ChangeMe123" \
            -s remoteapp --app-command "$app_cmd"
    else
        rdpsm user create "$username" -f "$fullname" -p "ChangeMe123" \
            -s remoteapp --app-command "$app_cmd" --app-args "$app_args"
    fi
done
```

### Monitor Sessions

```bash
#!/bin/bash
# Monitor active sessions every 5 seconds

while true; do
    clear
    rdpsm session list
    sleep 5
done
```

### Automated Cleanup

```bash
#!/bin/bash
# Disable inactive users

rdpsm user list --format json | jq -r '.[] | select(.active==false) | .username' | while read username; do
    echo "Disabling inactive user: $username"
    rdpsm user disable "$username"
done
```

### System Health Check

```bash
#!/bin/bash
# Check system health

echo "=== RDP Session Manager Health Check ==="
echo ""

# Check xrdp
if rdpsm server status > /dev/null 2>&1; then
    echo "✓ xrdp server: OK"
else
    echo "✗ xrdp server: NOT RUNNING"
fi

# Check dependencies
if rdpsm deps check > /dev/null 2>&1; then
    echo "✓ Dependencies: OK"
else
    echo "! Dependencies: MISSING"
fi

# Show server info
echo ""
rdpsm server info
```

---

## Troubleshooting

### Command Not Found

If `rdpsm` is not found, ensure the .deb package is properly installed:

```bash
# Check if rdpsm is installed
which rdpsm

# Reinstall if necessary
sudo dpkg -i rdp-session-manager_*.deb
```

### Permission Errors

Most operations require elevated privileges. You'll be prompted for authentication via pkexec.

```bash
# If pkexec is not working
sudo apt-get install policykit-1
```

### Module Import Errors

```bash
# Ensure you're in the project directory
cd /path/to/rdp-session-manager

# Or set PYTHONPATH
export PYTHONPATH=/path/to/rdp-session-manager/src:$PYTHONPATH
```

### Colors Not Showing

Colors are automatically disabled when output is piped. To force colors:

```bash
# Currently not supported, but output is still readable without colors
```

---

## Advanced Usage

### Quiet Mode for Scripts

Redirect stderr to suppress prompts:

```bash
rdpsm user create testuser -p "password" 2>/dev/null
```

### Combining Commands

```bash
# Create user and immediately connect
rdpsm user create john -p "pass123" && xfreerdp /v:localhost:3389 /u:john /p:pass123
```

### Using with jq

```bash
# Get enabled users count
rdpsm user list --format json | jq '[.[] | select(.enabled==true)] | length'

# Find users on port 3389
rdpsm user list --format json | jq '.[] | select(.rdp_port==3389) | .username'

# Get all session IPs
rdpsm session list --format json | jq -r '.[].ip_address' | sort -u
```

---

## Testing the CLI

After installing the .deb package, you can test the CLI functionality:

### Running Automated Tests

```bash
# Run the automated test suite (safe read-only commands only)
bash tests/test_cli.sh

# The test script will verify:
# - Version and help commands
# - User listing
# - Session listing
# - Server information
# - Desktop environment listing
# - Dependency checking
```

### Manual Testing Checklist

**Safe Commands (No system changes):**
- [ ] `rdpsm --version` - Show version
- [ ] `rdpsm --help` - Show help
- [ ] `rdpsm user list` - List users
- [ ] `rdpsm user list --format json` - List users (JSON)
- [ ] `rdpsm session list` - List sessions
- [ ] `rdpsm de list` - List desktop environments
- [ ] `rdpsm server info` - Show server information
- [ ] `rdpsm server status` - Check xrdp status
- [ ] `rdpsm deps check` - Check dependencies
- [ ] `rdpsm config get port` - Get RDP port

**Unsafe Commands (Require admin privileges, make system changes):**
- [ ] `rdpsm user create testuser` - Create user
- [ ] `rdpsm user delete testuser` - Delete user
- [ ] `rdpsm user enable testuser` - Enable user
- [ ] `rdpsm user disable testuser` - Disable user
- [ ] `rdpsm user password testuser` - Change password
- [ ] `rdpsm user sudo grant testuser` - Grant sudo privileges
- [ ] `rdpsm user sudo revoke testuser` - Revoke sudo privileges
- [ ] `rdpsm session kill testuser` - Kill session
- [ ] `rdpsm de install xfce` - Install desktop environment
- [ ] `rdpsm deps install xrdp` - Install xrdp
- [ ] `rdpsm deps install freerdp` - Install FreeRDP
- [ ] `rdpsm config set port 3390` - Set RDP port

### Expected Output Examples

**Version Command:**
```bash
$ rdpsm --version
RDPSM 0.2.1
```

**User List (Table):**
```bash
$ rdpsm user list
RDP Users (2 total)
===================

Username             UID      Desktop    Port     Status
----------------------------------------------------------------------
john                 5000     XFCE       3389     Enabled
mary                 5001     GNOME      3390     Disabled
```

**User List (JSON):**
```bash
$ rdpsm user list --format json
[
  {
    "username": "john",
    "uid": 5000,
    "home_dir": "/opt/rdp-users/john",
    "desktop_env": "xfce",
    "rdp_port": 3389,
    "active": false,
    "enabled": true,
    "is_superuser": false
  }
]
```

**Server Info:**
```bash
$ rdpsm server info
Server Information
===================
  IP Address:       192.168.1.50
  Default RDP Port: 3389
  Active Sessions:  1
```

**Desktop Environments:**
```bash
$ rdpsm de list
Available Desktop Environments
================================

ID           Name                 Size       Installed
------------------------------------------------------------
xfce         XFCE                 400MB      Yes
gnome        GNOME                1200MB     Yes
kde          KDE Plasma           1500MB     No
```

---

## Support

For issues or questions:
- Documentation: [README.md](README.md)
- Installation: [INSTALL.md](INSTALL.md)
- Troubleshooting: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- Bug Reports: GitHub Issues

---

Copyright (C) 2025 - RDP Session Manager Contributors
