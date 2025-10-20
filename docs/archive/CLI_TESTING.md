# CLI Testing Guide - RDP Session Manager

Complete guide for testing all CLI commands without installing the application.

## Prerequisites

You can test the CLI directly from the project directory without installation:

```bash
# Navigate to project directory
cd /path/to/rdp-session-manager

# Make the CLI executable (one time only)
chmod +x rdpsm

# Test any command
./rdpsm --help
```

**Note**: The `rdpsm` script automatically adds the `src/` directory to Python path, so no installation is needed.

---

## Table of Contents

- [Basic Commands](#basic-commands)
- [User Management Commands](#user-management-commands)
- [Session Management Commands](#session-management-commands)
- [Desktop Environment Commands](#desktop-environment-commands)
- [Server Commands](#server-commands)
- [Configuration Commands](#configuration-commands)
- [Dependency Commands](#dependency-commands)
- [Output Format Testing](#output-format-testing)
- [Safe vs Unsafe Commands](#safe-vs-unsafe-commands)

---

## Basic Commands

### Show Version
```bash
./rdpsm --version
```
**Expected output:**
```
RDPSM 0.2.0
```
**Safe to test:** ✓ Yes

---

### Show Help
```bash
./rdpsm --help
```
**Expected output:**
```
usage: rdpsm [-h] [-v] [--version] {user,session,de,server,config,deps} ...

RDP Session Manager CLI

positional arguments:
  {user,session,de,server,config,deps}
    user                User management
    session             Session management
    de                  Desktop environments
    server              Server information
    config              Configuration
    deps                Dependencies

options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose output
  --version             Show version
```
**Safe to test:** ✓ Yes

---

## User Management Commands

### List All Users
```bash
# Table format (default)
./rdpsm user list

# JSON format
./rdpsm user list --format json
```
**Expected output (table):**
```
RDP Users (1 total)
===================

Username             UID      Desktop    Port     Status
----------------------------------------------------------------------
trix_segundo         5000     GNOME      3389     Disabled
```
**Expected output (JSON):**
```json
[
  {
    "username": "trix_segundo",
    "uid": 5000,
    "home_dir": "/opt/rdp-users/trix_segundo",
    "desktop_env": "gnome",
    "rdp_port": 3389,
    "active": false,
    "enabled": false
  }
]
```
**Safe to test:** ✓ Yes (read-only)

---

### Show User Information
```bash
# Table format
./rdpsm user info USERNAME

# JSON format
./rdpsm user info USERNAME --format json

# Example with existing user
./rdpsm user info trix_segundo
```
**Expected output:**
```
User Information: trix_segundo
==============================
  Username:     trix_segundo
  UID:          5000
  Home:         /opt/rdp-users/trix_segundo
  Desktop:      GNOME
  RDP Port:     3389
  Status:       Disabled
  Connected:    No
  Processes:    0
```
**Safe to test:** ✓ Yes (read-only)

---

### Show User Processes
```bash
./rdpsm user processes USERNAME

# Example
./rdpsm user processes trix_segundo
```
**Expected output (if no processes):**
```
→ No processes found for user 'trix_segundo'
```
**Expected output (if has processes):**
```
Processes for USERNAME (15 total)
==================================
  PID: 1234
  PID: 1235
  PID: 1236
  ...
```
**Safe to test:** ✓ Yes (read-only)

---

### Create User
```bash
# Interactive (prompts for password)
./rdpsm user create USERNAME

# With all options
./rdpsm user create USERNAME -f "Full Name" -d xfce -p "password123"

# Example
./rdpsm user create testuser -f "Test User" -d xfce -p "Test1234"
```
**Expected output:**
```
→ Creating user 'testuser' with XFCE desktop...
✓ User 'testuser' created successfully
→ UID: 5001
→ Home: /opt/rdp-users/testuser
→ RDP Port: 3389
```
**Safe to test:** ⚠️ NO - Creates system user (requires sudo)

**Testing alternative:** Use `--help` to verify command structure:
```bash
./rdpsm user create --help
```

---

### Delete User
```bash
# Interactive (asks for confirmation)
./rdpsm user delete USERNAME

# Force delete without confirmation
./rdpsm user delete USERNAME --force

# Example
./rdpsm user delete testuser
```
**Expected output:**
```
Delete user 'testuser' and all data? (yes/no): yes
→ Deleting user 'testuser'...
✓ User 'testuser' deleted successfully
```
**Safe to test:** ⚠️ NO - Deletes system user (requires sudo)

**Testing alternative:**
```bash
./rdpsm user delete --help
```

---

### Enable User
```bash
./rdpsm user enable USERNAME

# Example
./rdpsm user enable trix_segundo
```
**Expected output:**
```
→ Enabling user 'trix_segundo'...
✓ User 'trix_segundo' enabled
```
**Safe to test:** ⚠️ NO - Modifies system user (requires sudo)

**Testing alternative:**
```bash
./rdpsm user enable --help
```

---

### Disable User
```bash
./rdpsm user disable USERNAME

# Example
./rdpsm user disable trix_segundo
```
**Expected output:**
```
→ Disabling user 'trix_segundo'...
✓ User 'trix_segundo' disabled
```
**Safe to test:** ⚠️ NO - Modifies system user (requires sudo)

**Testing alternative:**
```bash
./rdpsm user disable --help
```

---

### Change User Password
```bash
# Interactive (prompts for password)
./rdpsm user password USERNAME

# Non-interactive
./rdpsm user password USERNAME -p "newpassword"

# Example
./rdpsm user password trix_segundo
```
**Expected output:**
```
New password for trix_segundo:
Confirm password:
→ Changing password for 'trix_segundo'...
✓ Password changed for 'trix_segundo'
```
**Safe to test:** ⚠️ NO - Modifies system user (requires sudo)

**Testing alternative:**
```bash
./rdpsm user password --help
```

---

### Show User Command Help
```bash
./rdpsm user --help
```
**Expected output:**
```
usage: rdpsm user [-h] {create,delete,list,info,enable,disable,password,processes} ...

positional arguments:
  {create,delete,list,info,enable,disable,password,processes}
    create              Create new RDP user
    delete              Delete RDP user
    list                List RDP users
    info                Show user information
    enable              Enable user account
    disable             Disable user account
    password            Change user password
    processes           List user processes

options:
  -h, --help            show this help message and exit
```
**Safe to test:** ✓ Yes

---

## Session Management Commands

### List Active Sessions
```bash
# Table format
./rdpsm session list

# JSON format
./rdpsm session list --format json
```
**Expected output (if no sessions):**
```
→ No active sessions
```
**Expected output (if has sessions):**
```
Active Sessions (2 total)
==========================

Username             IP Address           Port
--------------------------------------------------
john                 192.168.1.100        3389
mary                 192.168.1.101        3389
```
**Safe to test:** ✓ Yes (read-only)

---

### Show Session Information
```bash
# Table format
./rdpsm session info USERNAME

# JSON format
./rdpsm session info USERNAME --format json

# Example
./rdpsm session info trix_segundo
```
**Expected output (if no active session):**
```
→ No active session for user 'trix_segundo'
```
**Expected output (if has session):**
```
Session Information: USERNAME
============================
  Username:     USERNAME
  IP Address:   192.168.1.100
  Port:         3389
  Duration:     3600 seconds
```
**Safe to test:** ✓ Yes (read-only)

---

### Kill Session
```bash
# Interactive (asks for confirmation)
./rdpsm session kill USERNAME

# Force kill without confirmation
./rdpsm session kill USERNAME --force

# Example
./rdpsm session kill testuser --force
```
**Expected output:**
```
→ Killing session for 'testuser'...
✓ Session killed for 'testuser'
```
**Safe to test:** ⚠️ NO - Terminates user processes (requires sudo)

**Testing alternative:**
```bash
./rdpsm session kill --help
```

---

### Show Session Command Help
```bash
./rdpsm session --help
```
**Expected output:**
```
usage: rdpsm session [-h] {list,info,kill} ...

positional arguments:
  {list,info,kill}
    list            List active sessions
    info            Show session information
    kill            Kill user session

options:
  -h, --help        show this help message and exit
```
**Safe to test:** ✓ Yes

---

## Desktop Environment Commands

### List Desktop Environments
```bash
# Table format
./rdpsm de list

# JSON format
./rdpsm de list --format json
```
**Expected output (table):**
```
Available Desktop Environments
================================

ID           Name                 Size       Installed
------------------------------------------------------------
lxde         LXDE                 250MB      No
lxqt         LXQt                 350MB      No
xfce         XFCE                 400MB      No
mate         MATE                 600MB      No
cinnamon     Cinnamon             800MB      Yes
gnome        GNOME                1200MB     Yes
kde          KDE Plasma           1500MB     No
```
**Expected output (JSON):**
```json
[
  {
    "id": "lxde",
    "name": "LXDE",
    "size_mb": 250,
    "installed": false
  },
  {
    "id": "gnome",
    "name": "GNOME",
    "size_mb": 1200,
    "installed": true
  }
]
```
**Safe to test:** ✓ Yes (read-only)

---

### Check Desktop Environment
```bash
./rdpsm de check DE_ID

# Examples
./rdpsm de check gnome
./rdpsm de check xfce
```
**Expected output (if installed):**
```
✓ Desktop environment 'gnome' is installed
```
**Expected output (if not installed):**
```
→ Desktop environment 'xfce' is not installed
```
**Exit codes:**
- 0 = Installed
- 1 = Not installed

**Safe to test:** ✓ Yes (read-only)

---

### Install Desktop Environment
```bash
# Install DE
./rdpsm de install DE_ID

# Reinstall if already installed
./rdpsm de install DE_ID --force

# Verbose output
./rdpsm -v de install DE_ID

# Example
./rdpsm de install xfce
```
**Expected output:**
```
→ Installing XFCE desktop environment...
  Checking disk space...
  Downloading packages...
  Installing packages...
✓ Desktop environment 'xfce' installed successfully
```
**Safe to test:** ⚠️ NO - Installs system packages (requires sudo, downloads ~400MB+)

**Testing alternative:**
```bash
./rdpsm de install --help
```

---

### Show DE Command Help
```bash
./rdpsm de --help
```
**Expected output:**
```
usage: rdpsm de [-h] {list,install,check} ...

positional arguments:
  {list,install,check}
    list                List available desktop environments
    install             Install desktop environment
    check               Check if DE is installed

options:
  -h, --help            show this help message and exit
```
**Safe to test:** ✓ Yes

---

## Server Commands

### Show Server Information
```bash
# Table format
./rdpsm server info

# JSON format
./rdpsm server info --format json

# Verbose mode
./rdpsm -v server info
```
**Expected output (table):**
```
Server Information
==================
  IP Address:       192.168.15.12
  Default RDP Port: 3389
  Active Sessions:  0
```
**Expected output (JSON):**
```json
{
  "ip": "192.168.15.12",
  "port": 3389,
  "active_sessions": 0
}
```
**Safe to test:** ✓ Yes (read-only)

---

### Check Server Status
```bash
./rdpsm server status
```
**Expected output (if running):**
```
✓ xrdp server is installed and running
```
**Expected output (if not running):**
```
! xrdp server is not installed or not running
```
**Exit codes:**
- 0 = Running
- 1 = Not running

**Safe to test:** ✓ Yes (read-only)

---

### Show Server Command Help
```bash
./rdpsm server --help
```
**Safe to test:** ✓ Yes

---

## Configuration Commands

### Get Configuration
```bash
./rdpsm config get KEY

# Available keys: port

# Example
./rdpsm config get port
```
**Expected output:**
```
3389
```
**Safe to test:** ✓ Yes (read-only)

---

### Set Configuration
```bash
./rdpsm config set KEY VALUE

# Example
./rdpsm config set port 3390
```
**Expected output:**
```
✓ Default RDP port set to 3390
```
**Safe to test:** ⚠️ CAUTION - Modifies configuration file

**Note:** This modifies `~/.config/rdp-session-manager/config.json`. Safe to test if you're okay with changing the default port.

**Restore original value:**
```bash
./rdpsm config set port 3389
```

---

### Show Config Command Help
```bash
./rdpsm config --help
```
**Expected output:**
```
usage: rdpsm config [-h] {get,set} ...

positional arguments:
  {get,set}
    get       Get configuration value
    set       Set configuration value

options:
  -h, --help  show this help message and exit
```
**Safe to test:** ✓ Yes

---

## Dependency Commands

### Check Dependencies
```bash
# Table format
./rdpsm deps check

# JSON format
./rdpsm deps check --format json
```
**Expected output (all installed):**
```
System Dependencies
===================

Installed:
  ✓ xrdp
  ✓ freerdp
  ✓ x11

All dependencies are installed
```
**Expected output (JSON):**
```json
{
  "all_ok": true,
  "missing": [],
  "installed": [
    "xrdp",
    "freerdp",
    "x11"
  ]
}
```
**Expected output (missing dependencies):**
```
System Dependencies
===================

Installed:
  ✓ xrdp

Missing:
  ✗ freerdp
  ✗ x11

! Some dependencies are missing
```
**Exit codes:**
- 0 = All installed
- 1 = Some missing

**Safe to test:** ✓ Yes (read-only)

---

### Install Dependency
```bash
# Install package
./rdpsm deps install PACKAGE

# Verbose output
./rdpsm -v deps install PACKAGE

# Available packages: xrdp, freerdp

# Examples
./rdpsm deps install xrdp
./rdpsm deps install freerdp
```
**Expected output:**
```
→ Installing xrdp...
  Updating package lists...
  Installing xrdp...
  Configuring xrdp...
✓ Package 'xrdp' installed successfully
```
**Safe to test:** ⚠️ NO - Installs system packages (requires sudo)

**Testing alternative:**
```bash
./rdpsm deps install --help
```

---

### Show Deps Command Help
```bash
./rdpsm deps --help
```
**Expected output:**
```
usage: rdpsm deps [-h] {check,install} ...

positional arguments:
  {check,install}
    check          Check system dependencies
    install        Install dependency

options:
  -h, --help       show this help message and exit
```
**Safe to test:** ✓ Yes

---

## Output Format Testing

### Test JSON Format on All List Commands
```bash
# Users
./rdpsm user list --format json

# Sessions
./rdpsm session list --format json

# Desktop Environments
./rdpsm de list --format json

# Server Info
./rdpsm server info --format json

# Dependencies
./rdpsm deps check --format json
```
**Safe to test:** ✓ Yes (all read-only)

---

### Test Piping JSON to jq
```bash
# Get all usernames
./rdpsm user list --format json | jq -r '.[].username'

# Count enabled users
./rdpsm user list --format json | jq '[.[] | select(.enabled==true)] | length'

# Get server IP
./rdpsm server info --format json | jq -r '.ip'

# List installed DEs
./rdpsm de list --format json | jq -r '.[] | select(.installed==true) | .name'

# Get missing dependencies
./rdpsm deps check --format json | jq -r '.missing[]'
```
**Safe to test:** ✓ Yes (requires `jq` to be installed)

---

### Test Verbose Mode
```bash
# Verbose mode adds extra output
./rdpsm -v server info
./rdpsm -v user list
./rdpsm -v de list
```
**Safe to test:** ✓ Yes

---

## Safe vs Unsafe Commands

### ✓ Safe Commands (Read-Only)

These commands only read data and don't modify the system:

```bash
# General
./rdpsm --version
./rdpsm --help
./rdpsm <command> --help

# User Management
./rdpsm user list
./rdpsm user list --format json
./rdpsm user info USERNAME
./rdpsm user processes USERNAME

# Sessions
./rdpsm session list
./rdpsm session info USERNAME

# Desktop Environments
./rdpsm de list
./rdpsm de check DE_ID

# Server
./rdpsm server info
./rdpsm server status

# Configuration
./rdpsm config get port

# Dependencies
./rdpsm deps check
```

---

### ⚠️ Unsafe Commands (Modify System)

These commands modify the system and should be tested carefully:

```bash
# User Management (require sudo)
./rdpsm user create USERNAME       # Creates system user
./rdpsm user delete USERNAME       # Deletes system user
./rdpsm user enable USERNAME       # Modifies user account
./rdpsm user disable USERNAME      # Modifies user account
./rdpsm user password USERNAME     # Changes user password

# Sessions (require sudo)
./rdpsm session kill USERNAME      # Terminates user processes

# Desktop Environments (require sudo, large downloads)
./rdpsm de install DE_ID           # Installs 250MB-1500MB of packages

# Dependencies (require sudo)
./rdpsm deps install PACKAGE       # Installs system packages
```

---

### 🔄 Configuration Commands (Modify Config Files)

These modify configuration files but don't require sudo:

```bash
./rdpsm config set port 3390       # Modifies config.json
```

**Note:** Safe to test, but will change the default RDP port. You can restore it with:
```bash
./rdpsm config set port 3389
```

---

## Error Handling Testing

### Test Non-Existent User
```bash
./rdpsm user info nonexistent_user
```
**Expected output:**
```
✗ User 'nonexistent_user' not found
```
**Exit code:** 1

---

### Test Invalid Desktop Environment
```bash
./rdpsm de check invalid_de
```
**Expected behavior:** Should handle gracefully

---

### Test Invalid Command
```bash
./rdpsm invalid_command
```
**Expected output:**
```
usage: rdpsm [-h] [-v] [--version] {user,session,de,server,config,deps} ...
rdpsm: error: invalid choice: 'invalid_command'
```
**Exit code:** 2

---

## Quick Test Script

Here's a script to test all safe read-only commands:

```bash
#!/bin/bash
# test_cli.sh - Test all safe CLI commands

echo "=== Testing RDP Session Manager CLI ==="
echo ""

echo "1. Version:"
./rdpsm --version
echo ""

echo "2. User List:"
./rdpsm user list
echo ""

echo "3. User List (JSON):"
./rdpsm user list --format json
echo ""

echo "4. Session List:"
./rdpsm session list
echo ""

echo "5. Desktop Environments:"
./rdpsm de list
echo ""

echo "6. Server Info:"
./rdpsm server info
echo ""

echo "7. Server Status:"
./rdpsm server status
echo ""

echo "8. Config Get Port:"
./rdpsm config get port
echo ""

echo "9. Dependencies Check:"
./rdpsm deps check
echo ""

echo "=== All safe commands tested ==="
```

**Usage:**
```bash
chmod +x test_cli.sh
./test_cli.sh
```

---

## Exit Codes

All commands follow standard exit code conventions:

- **0** - Success
- **1** - Error or failure
- **2** - Invalid command syntax

**Test exit codes:**
```bash
# Success (exit 0)
./rdpsm server info && echo "Success" || echo "Failed"

# Failure (exit 1)
./rdpsm user info nonexistent && echo "Success" || echo "Failed"

# Check last exit code
./rdpsm server info
echo $?
```

---

## Summary

### Commands You Can Safely Test Now

```bash
# Information commands (no system changes)
./rdpsm --version
./rdpsm --help
./rdpsm user list
./rdpsm user list --format json
./rdpsm session list
./rdpsm de list
./rdpsm de check gnome
./rdpsm server info
./rdpsm server status
./rdpsm config get port
./rdpsm deps check

# With jq (if installed)
./rdpsm user list --format json | jq
./rdpsm server info --format json | jq
```

### Commands to Avoid Without Installation

```bash
# These require sudo and modify the system
./rdpsm user create/delete/enable/disable
./rdpsm session kill
./rdpsm de install
./rdpsm deps install
```

---

## Notes

1. **No Installation Required**: All commands work directly from the project directory
2. **Help is Your Friend**: Every command and subcommand has `--help`
3. **JSON + jq**: Use `--format json` with `jq` for advanced filtering
4. **Exit Codes**: Check with `echo $?` after any command
5. **Verbose Mode**: Add `-v` before any command for extra output

---

Copyright (C) 2025 - RDP Session Manager Contributors
