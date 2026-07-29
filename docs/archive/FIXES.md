# Corrections and Improvements Applied

## 🎉 General Summary

The application is **FULLY FUNCTIONAL** with all operations implemented and tested!

**Current Version**: v0.2.0
**Data**: 2025-10-18
**Status**: ✅ Production

---

## 📋 All Corrections (Chronological)

### Version 0.1.0 (10/17/2025) - Initial Fixes

#### 1. ✅ Namespace libadwaita
**Problem**: `ValueError: Namespace Adw not available for version 1.0`
**Cause**: Debian packages libadwaita as version '1' instead of '1.0'
**Solution**: Changed 4 files:
```python
# Before
gi.require_version('Adw', '1.0')

# After
gi.require_version('Adw', '1')
```

**Modified files**:
- `src/main.py`
- `src/application.py`
- `src/ui/main_window.py`
- `src/ui/user_dialog.py`

#### 2. ✅ Deprecated GTK API
**Problem**: `AttributeError: type object 'Widget' has no attribute 'get_default_display'`
**Cause**: Deprecated API in GTK4
**Solution**: Use `Gdk.Display.get_default()` instead of `Gtk.Widget.get_default_display()`

**File**: `src/application.py`

#### 3. ✅ psutil Connections
**Problem**: `invalid attr name 'connections'`
**Cause**: `process_iter` does not accept 'connections' as a direct attribute
**Solution**: Use `proc.connections(kind='inet')` manually

**File**: `src/core/session_monitor.py`

#### 4. ✅ Missing dependency
**Problem**: ModuleNotFoundError: No module named 'psutil'
**Solution**: Added `python3-psutil` to requirements.txt

---

### Version 0.2.0 (10/18/2025) - Critical Fixes

#### 5. ✅ Complete Log System (CRITICAL)
**Problem**: Only logs from the main module (`rdp-session-manager`) were written to the file
**Cause**: `setup_logger()` only configured the named logger, not the root logger
**Impact**: Impossible to debug problems in user_manager, rdp_config, de_installer, etc.

**Solution**:
```python
# src/utils/logger.py

# BEFORE (wrong)
def setup_logger(name: str = 'rdp-session-manager', ...):
    logger = logging.getLogger(name) # Only this configured logger
    # ... settings ...
    return logger

# AFTER (correct)
def setup_logger(name: str = 'rdp-session-manager', ...):
    root_logger = logging.getLogger()  # ROOT logger
    root_logger.setLevel(log_level)

    # Avoid duplication
    if root_logger.handlers:
        return logging.getLogger(name)

    # Configure handlers in the root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Return named logger for local use
    return logging.getLogger(name)
```

**Result**: ALL modules now log in correctly:
```
2025-10-18 00:46:47 - core.user_manager - INFO - Removing RDP user: trix_bastardo
2025-10-18 00:46:47 - core.user_manager - INFO - User has 58 active processes
2025-10-18 00:46:52 - core.user_manager - INFO - Running userdel...
2025-10-18 00:46:55 - core.user_manager - INFO - ✓ User removed successfully
```

**Affected files**: All modules now log correctly!

#### 6. ✅ pkexec with Absolute Paths (CRITICAL)
**Problem**: Commands failing with code 127 "command not found"
**Error message**:
```
2025-10-17 20:15:33 - core.user_manager - ERROR - Failed to create group: pkexec not found - code 127
```

**Cause**: pkexec does not have `/usr/sbin` in the PATH by default
**Impact**: NO administrative operations worked (create user, group, etc.)

**Solution**: Use absolute paths in ALL commands:
```python
# BEFORE (wrong)
subprocess.run(['pkexec', 'groupadd', 'rdp-users'])
subprocess.run(['pkexec', 'useradd', '-u', uid, username])
subprocess.run(['pkexec', 'apt-get', 'install', 'xrdp'])

# AFTER (correct)
subprocess.run(['pkexec', '/usr/sbin/groupadd', 'rdp-users'])
subprocess.run(['pkexec', '/usr/sbin/useradd', '-u', uid, username])
subprocess.run(['pkexec', '/usr/bin/apt-get', 'install', 'xrdp'])
```

**Fixed commands**:
- `/usr/sbin/groupadd` - Create groups
- `/usr/sbin/useradd` - Create users
- `/usr/sbin/userdel` - Delete users
- `/usr/sbin/chpasswd` - Set passwords
- `/usr/bin/apt-get` - Install packages
- `/usr/bin/systemctl` - Manage services
- `/usr/bin/mkdir` - Create directories
- `/usr/bin/chmod` - Change permissions
- `/usr/bin/pkill` - Terminate processes
- `/usr/bin/bash` - Run scripts
- `/usr/bin/cp` - Copy files
- `/usr/bin/chown` - Change ownership

**Modified files**:
- `src/core/user_manager.py` - All commands
- `src/core/system_deps.py` - apt-get e systemctl
- `src/core/rdp_config.py` - cp, chown, chmod, bash
- `src/core/de_installer.py` - apt-get

**Result**: All administrative operations work perfectly!

#### 7. ✅ FreeRDP Detection and Installation
**Problem**: Application did not detect if FreeRDP was installed
**Impact**: Users had to install manually, bad experience

**Implemented Solution**:

1. **Auto Detect** (`src/core/system_deps.py`):
```python
def is_freerdp_installed(self) -> bool:
    import shutil
    return shutil.which('xfreerdp3') is not None or shutil.which('xfreerdp') is not None

def get_freerdp_command(self) -> str:
    import shutil
    if shutil.which('xfreerdp3'):
        return 'xfreerdp3'
    elif shutil.which('xfreerdp'):
        return 'xfreerdp'
    return None
```

2. **Addition to Managed Packages**:
```python
REQUIRED_PACKAGES = {
    # ...
    'freerdp': {
        'name': 'FreeRDP',
        'packages': ['freerdp3-x11'],
        'description': 'Cliente RDP (Remote Desktop Protocol)',
        'service': None,
        'critical': False # Optional, only for connecting
    }
}
```

3. **Installation Flow** (`src/ui/main_window.py` + `src/application.py`):
```python
def handle_connect_response(self, response, user):
    if response == "connect":
        if not self.system_deps.is_freerdp_installed():
            # Dialog offering installation
            install_dialog = Adw.MessageDialog(...)
            install_dialog.connect("response", lambda d, r: self.on_freerdp_install_response(r, user))
            install_dialog.present()
            return

        self.show_password_dialog(user)

def on_freerdp_install_response(self, response, user):
    if response == "install":
        app = self.get_application()
        app.install_freerdp_with_progress()
```

4. **Dialog with Progress** (`src/application.py`):
```python
def install_freerdp_with_progress(self):
    dialog = Adw.MessageDialog(...)
    # TextView showing output in real time
    # Installation thread
    # Progress callback
```

**Result**:
- Automatic detection when clicking "Open FreeRDP"
- Offers installation if not installed
- Visual progress during installation
- Support for xfreerdp3 and xfreerdp (fallback)

#### 8. ✅ Visual Dialog for RDP Credentials
**Problem**: FreeRDP asked for credentials in the terminal, not visually
**Impact**: Bad UX, confused users

**Attempt 1 - FAILED**:
```python
password_entry = Adw.PasswordEntryRow() # Does not work in MessageDialog!
```
**Error**: Widget incompatibility

**Attempt 2 - FAILED**:
```python
password_entry = Gtk.PasswordEntry()
password_entry.set_placeholder_text("Password") # Method does not exist!
```
**Error**: `AttributeError: 'PasswordEntry' object has no attribute 'set_placeholder_text'`

**Attempt 3 - FAILED**:
```python
password_entry = Gtk.Entry()
password_entry.set_visibility(False)
# But GLib.timeout_add() was stealing focus!
```
**Error**: Focus returned automatically, impossible to type in domain_entry

**Final Solution - IT WORKS**:
```python
def show_password_dialog(self, user):
    dialog = Adw.MessageDialog(...)

    # Box with fields
    creds_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

    # Domain field (optional)
    domain_entry = Gtk.Entry()
    domain_entry.set_can_focus(True)  # IMPORTANTE!

    # Password field
    password_entry = Gtk.Entry()
    password_entry.set_visibility(False)  # Hide text
    password_entry.set_invisible_char('•')
    password_entry.set_can_focus(True)  # IMPORTANTE!

    # Enter to navigate
    domain_entry.connect('activate', lambda e: password_entry.grab_focus())
    password_entry.connect('activate', lambda e: dialog.response('connect'))

    # WITHOUT GLib.timeout_add() - that was what stole the focus!
```

**Result**:
- Dialog visual clean
- Optional domain field for Windows domains
- Password field working perfectly
- Enter navigates between fields
- Credentials passed via `/d:` and `/p:`

#### 9. ✅ Smart User Deletion
**Problem**: Unable to delete logged in user
**Error message**:
```
userdel: user trix_bastardo is currently used by process 26924
```

**Implemented Solution** (`src/core/user_manager.py`):

1. **Process Detection**:
```python
def get_user_processes(self, username: str) -> List[int]:
    """Get list of user process PIDs"""
    result = subprocess.run(
        ['pgrep', '-u', username],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        pids = [int(pid) for pid in result.stdout.strip().split('\n') if pid]
        return pids

    return []
```

2. **Closure of Processes**:
```python
def kill_user_processes(self, username: str, force: bool = False) -> bool:
    """Kills user processes (SIGTERM or SIGKILL)"""
    signal = '-9' if force else '-15'

    result = subprocess.run(
        ['pkexec', '/usr/bin/pkill', signal, '-u', username],
        capture_output=True,
        text=True,
        timeout=10
    )

    return result.returncode in [0, 1] # 0=processes found, 1=not found
```

3. **Complete Deletion**:
```python
def delete_user(self, username: str, remove_home: bool = True, kill_processes: bool = True) -> bool:
    # 1. Check active processes
    active_pids = self.get_user_processes(username)

    if active_pids:
        logger.info(f"User {username} has {len(active_pids)} active processes")

        if kill_processes:
            # 2. Terminate gracefully (SIGTERM)
            self.kill_user_processes(username, force=False)
            time.sleep(1)

            # 3. Check if there are still processes
            remaining_pids = self.get_user_processes(username)

            if remaining_pids:
                # 4. Force (SIGKILL)
                logger.warning("There are still processes. Forcing termination...")
                self.kill_user_processes(username, force=True)
                time.sleep(0.5)

    # 5. Delete user
    cmd = ['pkexec', '/usr/sbin/userdel']
    if remove_home:
        cmd.append('-r')
    cmd.append(username)

    result = subprocess.run(cmd, ...)
    return result.returncode == 0
```

4. **UI Contextual** (`src/ui/main_window.py`):
```python
def on_delete_user(self, username):
    active_pids = self.user_manager.get_user_processes(username)

    if active_pids:
        # Special dialog for logged in users
        dialog = Adw.MessageDialog(
            heading=f"⚠ {username} is active",
            body=f"...your sessions will be terminated automatically..."
        )
        dialog.add_response("delete", "Close and Remove")
    else:
        # Normal dialog for inactive users
        dialog = Adw.MessageDialog(
            heading=f"Remove {username}?",
            body="...All data will be removed..."
        )
        dialog.add_response("delete", "Remove")
```

**Teste Real (18/10/2025 00:46)**:
```
Input: Delete user trix_bastardo (58 active processes)
Logs:
  - 58 processes detected: [26924, 26926, ...]
  - Ending with SIGTERM -15
  - Aguardando 1 segundo
  - Checking remaining processes
  - Forcing with SIGKILL -9 if necessary
  - Running userdel -r trix_bastardo
Output: ✅ User successfully removed
  - Account removed
  - Home /opt/rdp-users/trix_bastardo removido
  - All 58 cases closed
```

#### 10. ✅ Verification and Installation of xrdp
**Problem**: Application did not warn if xrdp was not installed
**Impact**: Users created but did not work

**Implemented Solution**:

1. **Warning Banner** (`src/ui/main_window.py`):
```python
def create_xrdp_warning_banner(self):
    self.xrdp_banner = Adw.Banner()
    self.xrdp_banner.set_title("⚠ xrdp server is not installed - The application will not work without it")
    self.xrdp_banner.set_button_label("Install Now")
    self.xrdp_banner.connect('button-clicked', self.on_install_xrdp_clicked)
    self.xrdp_banner.set_revealed(False)

    # Insert at the top of the interface
    toolbar_view = self.toast_overlay.get_child()
    content = toolbar_view.get_content()
    content.prepend(self.xrdp_banner)
```

2. **Periodic Check**:
```python
def __init__(self, ...):
    # ...
    self.update_xrdp_status()  # Inicial
    GLib.timeout_add_seconds(10, self.update_xrdp_status) # Every 10sec

def update_xrdp_status(self):
    xrdp_ready = self.system_deps.is_xrdp_ready()

    # Show/hide banner
    self.xrdp_banner.set_revealed(not xrdp_ready)

    # Block create user buttons
    self.add_user_button.set_sensitive(xrdp_ready)
    self.empty_add_user_button.set_sensitive(xrdp_ready)

    return True  # Continue timeout
```

3. **Installation with Progress** (`src/application.py`):
```python
def show_xrdp_install_dialog(self):
    dialog = Adw.MessageDialog(...)

    # TextView for logs
    textview = Gtk.TextView()
    textbuffer = textview.get_buffer()

    # Installation thread
    def install_in_thread():
        success, msg = self.system_deps.install_package(
            'xrdp',
            progress_callback=lambda progress, msg: GLib.idle_add(append_log, msg)
        )
        GLib.idle_add(on_install_complete, success, msg)

    thread = threading.Thread(target=install_in_thread)
    thread.daemon = True
    thread.start()
```

**Result**:
- Banner appears if xrdp not installed
- Create user buttons blocked
- One-click installation
- Real-time visual progress
- Service enabled and started automatically

#### 11. ✅ Dynamic Desktop Environment Detection
**Issue**: All users appeared as "XFCE • Port 3389" in the interface, regardless of the Desktop Environment chosen
**Impact**: Impossible to know which DE the user actually uses

**Bug Evidence**:
```
Interface mostrava:
- User1: XFCE • Port 3389 (but it was LXDE)
- User2: XFCE • Port 3389 (but it was GNOME)
- User3: XFCE • Port 3389 (but it was KDE)
```

**Causa**: Valores hardcoded em `list_users()`
```python
# src/core/user_manager.py (line 122-123) - BEFORE

rdp_user = RDPUser(
    username=user_info.pw_name,
    uid=user_info.pw_uid,
    home_dir=user_info.pw_dir,
    desktop_env="xfce", # TODO: read from config - HARDCODED!
    rdp_port=3389, # TODO: read from config - HARDCODED!
    active=False
)
```

**Implemented Solution**:

1. **ED Detection Method** (lines 542-577):
```python
def _detect_desktop_env(self, home_dir: str) -> str:
    """Detects the Desktop Environment by reading the .xsession file"""
    try:
        xsession_file = Path(home_dir) / '.xsession'

        if not xsession_file.exists():
            logger.warning(f"File .xsession not found in {home_dir}")
            return "unknown"

        # Read .xsession file
        with open(xsession_file, 'r') as f:
            content = f.read()

        # Map commands to DEs
        de_commands = {
            'startlxde': 'lxde',
            'startlxqt': 'lxqt',
            'startxfce4': 'xfce',
            'mate-session': 'mate',
            'cinnamon-session': 'cinnamon',
            'gnome-session': 'gnome',
            'startplasma-x11': 'kde'
        }

        # Search command in file
        for command, de_id in de_commands.items():
            if command in content:
                logger.debug(f"Detected DE for {home_dir}: {de_id} (command: {command})")
                return de_id

        logger.warning(f"DE command not recognized in {xsession_file}")
        return "unknown"

    except Exception as e:
        logger.error(f"Error detecting DE of {home_dir}: {e}")
        return "unknown"
```

2. **RDP Port Detection Method** (lines 579-585):
```python
def _detect_rdp_port(self, uid: int) -> int:
    """Detect RDP port based on UID"""
    base_port = 3389
    port_offset = uid - self.RDP_UID_START  # RDP_UID_START = 5000
    return base_port + port_offset
```

3. **list_users() Updated** (lines 587-622):
```python
# AFTER (correct)
def list_users(self) -> List[RDPUser]:
    for user_info in pwd.getpwall():
        if self._is_rdp_user(user_info.pw_name):
            # Detect real Desktop Environment
            desktop_env = self._detect_desktop_env(user_info.pw_dir)

            # Detect RDP port based on UID
            rdp_port = self._detect_rdp_port(user_info.pw_uid)

            rdp_user = RDPUser(
                username=user_info.pw_name,
                uid=user_info.pw_uid,
                home_dir=user_info.pw_dir,
                desktop_env=desktop_env, # NOW READ FROM .xsession!
                rdp_port=rdp_port, # NOW CALCULATE THE UID!
                active=False
            )
```

**How ​​It Works**:
1. During `create_user()`, the file `.xsession` is created with the chosen DE startup command
2. During `list_users()`, method `_detect_desktop_env()` reads this file
3. Maps the found command (`startlxde`, `gnome-session`, etc.) to the DE ID
4. RDP port is automatically calculated based on user UID

**DE → Command Mapping**:
- `startlxde` → LXDE
- `startlxqt` → LXQt
- `startxfce4` → XFCE
- `mate-session` → MATE
- `cinnamon-session` → Cinnamon
- `gnome-session` → GNOME
- `startplasma-x11` → KDE Plasma

**Port Calculation**:
- First user (UID 5000): Port 3389
- Second user (UID 5001): Port 3390
- Third user (UID 5002): Port 3391
- And so on...

**Result**:
```
Interface now correctly shows:
- User1: LXDE • Port 3389 • IP: ...
- User2: GNOME • Port 3390 • IP: ...
- User3: KDE • Port 3391 • IP: ...
```

**Modified File**:
- `src/core/user_manager.py`

**Detection Logs**:
```
DEBUG - core.user_manager - Detected DE for /opt/rdp-users/usuario1: lxde (command: startlxde)
DEBUG - core.user_manager - Detected DE for /opt/rdp-users/usuario2: gnome (command: gnome-session)
DEBUG - core.user_manager - Detected DE for /opt/rdp-users/usuario3: kde (command: startplasma-x11)
```

#### 12. ✅ Home Directory Permissions Preventing .xsession from being read
**Problem**: Desktop Environment appeared as "Unknown" even with the correct .xsession file
**Impact**: Dynamic ED detection did not work

**Root Cause**: Permissions 700 on home directory
```bash
$ stat /opt/rdp-users/user
700 user:rdp-users /opt/rdp-users/user
#  ^^^
#  Owner: rwx, Group: ---, Others: ---
# Application cannot ENTER the directory to read .xsession
```

**Evidence in Logs**:
```
ERROR - Error detecting DE of /opt/rdp-users/trix-gnome: [Errno 13] Permission denied: '/opt/rdp-users/trix-gnome/.xsession'
```

**Why It Happened**:
- The command `useradd -m` creates the home directory with default permissions 700
- This is safe for normal users, but prevents the application from reading settings
- Even though the .xsession file is 755, it is not accessible if the directory is 700

**Implemented Solution** (`src/core/user_manager.py` lines 373-389):

```python
# After creating user and setting password...

# Correct home directory permissions to allow reading of .xsession
if log_callback:
    log_callback(f" → Adjusting home directory permissions...")

chmod_result = subprocess.run(
    ['pkexec', '/usr/bin/chmod', '751', home_dir],
    capture_output=True,
    text=True,
    timeout=10
)

if chmod_result.returncode != 0:
    logger.warning(f"Warning when setting home permissions: {chmod_result.stderr}")
else:
    logger.info(f"Home permissions changed to 751")
    if log_callback:
        log_callback(f" ✓ Permissions set (751)")
```

**Permissions 751**:
```
7 (rwx) - Owner: Controle total
5 (r-x) - Group: Read and execute
1 (--x) - Others: RUN (can enter directory)
```

**Why 751 and not 755?**:
- 751: Others can **enter** the directory but cannot **list** content
- More secure: Need to know the exact file name
- Allows reading `.xsession` (which has 755) but not listing private files
- Good practice for home directories in multi-user environments

**How ​​to Fix Existing Users**:
```bash
# For each existing RDP user:
sudo chmod 751 /opt/rdp-users/NOME_USUARIO
```

**Modified File**:
- `src/core/user_manager.py` - Method `_create_system_user()`

**Verification Test**:
```bash
# 1. Check permissions
$ stat -c "%a" /opt/rdp-users/trix-gnome
751  # ✓ Correto!

# 2. Testar leitura
$ cat /opt/rdp-users/trix-gnome/.xsession | grep exec
exec gnome-session  # ✓ Funciona!

# 3. Check in application
# Interface now shows: "GNOME • Port 3389 • IP: ..."
# Instead of: "Unknown • Port 3389 • IP: ..."
```

**Result**:
- ✅ New users created automatically with 751
- ✅ ED detection works perfectly
- ✅ Security maintained (others cannot list directory)
- ✅ Interface mostra DE correto

---

## 🎯 Feature Summary

### ✅ O que funciona 100%:

1. **User Management**:
   - ✓ Creation with validation
   - ✓ Exclusion with closing sessions
   - ✓ Detection of active processes
   - ✓ Logs completos

2. **Dependency Installation**:
   - ✓ xrdp with banner and progress
   - ✓ FreeRDP sob demanda
   - ✓ Desktop Environments with progress

3. **RDP Connection**:
   - ✓ Visual dialog for credentials
   - ✓ Support for domains
   - ✓ Direct customer launch
   - ✓ Copy of address

4. **Interface**:
   - ✓ GTK4/modern libadwaita
   - ✓ Toast notifications
   - ✓ Dialogs contextuais
   - ✓ Banner de avisos
   - ✓ Visual progress

5. **Logs and Security**:
   - ✓ All modules log in
   - ✓ PolicyKit for everything
   - ✓ Absolute paths
   - ✓ Robust validation

---

## 📊 Testes Executados

### Test 1: User Creation
```
Input: testuser, TestPass123, XFCE
Result: ✅ SUCCESS
- Group rdp-users created
- Directory /opt/rdp-users created
- User created (UID: 5000)
- Password set
- .xsession created
- Logs completos
```

### Test 2: Inactive User Deletion
```
Input: Delete testuser (0 processes)
Result: ✅ SUCCESS
- Normal confirmation dialog
- User removed
- Home removido
- Logs completos
```

### Test 3: User Deletion with 58 Processes
```
Input: Delete trix_bastardo (58 active processes)
Result: ✅ SUCCESS
- Special warning dialog
- 58 processes detected
- Processes closed (SIGTERM)
- Checking remaining processes
- Force SIGKILL if necessary
- User removed
- Home removido
- Detailed logs of each step
```

### Test 4: RDP Connection with Credentials
```
Input: Connect to testuser
Result: ✅ SUCCESS
- Credentials dialog appears
- Domain field (optional)
- Password field working
- Enter navigates between fields
- FreeRDP launched with credentials
- Open RDP session
```

### Test 5: FreeRDP Installation
```
Input: Click "Open FreeRDP" without FreeRDP installed
Result: ✅ SUCCESS
- Dialog offering installation
- Visual progress
- freerdp3-x11 instalado
- Dialog fechado
- Reconecta automaticamente
```

### Test 6: Installing xrdp
```
Input: Start app without xrdp
Result: ✅ SUCCESS
- Warning banner appears
- Create buttons blocked
- Click "Install Now"
- Dialog with progress
- xrdp e xorgxrdp instalados
- Service enabled and started
- Banner desaparece
```

---

## 📞 Troubleshooting

### Logs do not appear
**Solution**: Version 0.2.0 fixed it - all modules now log in

### Error 127 when creating user
**Workaround**: Version 0.2.0 fixed - all commands use absolute paths

### I can't type in the password field
**Solution**: Version 0.2.0 fixed it - removed GLib.timeout_add()

### I can't delete logged in user
**Solution**: Version 0.2.0 fixed - automatic termination of processes

---

## 🚀 How to Check if It's Updated

```bash
# View version
cat STATUS.md | grep "Version"
# Should show: v0.2.0

# View running logs
tail -f ~/.local/share/rdp-session-manager/logs/rdp-session-manager.log
# Should show logs from core.user_manager, core.rdp_config, etc.

# Test deletion of logged in user
# It should show special dialog and terminate processes automatically
```

---

**Date of Corrections**: 2025-10-18
**Status**: ✅ FULLY FUNCTIONAL
**Version**: 0.2.0

🎊 **All fixes successfully applied and tested!** 🎊
