# Development Documentation

## Project Progress

### Phase 1: Base Structure (100% Complete)

- [x] Directory structure created
- [x] Build system configured (Meson + setuptools)
- [x] Application metadata (Desktop file, AppData, GSchema)
- [x] PolicyKit configured for administrative actions

### Phase 2: Core Backend (100% Complete)

- [x] User management module (`user_manager.py`)
  - Creation, deletion, listing of RDP users
  - Username validation
  - Automatic UID and port generation

- [x] FreeRDP configuration system (`rdp_config.py`)
  - xrdp configuration generation
  - Session startup scripts
  - Support for multiple Desktop Environments

- [x] Automatic Desktop Environment installer (`de_installer.py`)
  - Support for GNOME, XFCE, KDE, MATE, Cinnamon, LXDE, LXQt
  - Disk space verification
  - Detection of installed DEs

- [x] Session monitoring (`session_monitor.py`)
  - Active session detection
  - System resource monitoring
  - IP and port retrieval

### Phase 3: GTK4 Interface (100% Complete)

- [x] Main window (`main-window.ui`)
  - RDP user list
  - Server information
  - User search

- [x] User creation dialog (`user-dialog.ui`)
  - Complete form
  - Real-time validation
  - DE selection

- [x] Python UI implementation
  - `MainWindow` with real-time updates
  - `UserDialog` with validation
  - Backend integration

### Phase 4: Integration and Security (100% Complete)

- [x] PolicyKit Helper (`rdp-session-helper.py`)
  - User creation/deletion
  - Package installation
  - Session management

- [x] Validation system (`validator.py`)
  - Username, password, port validation
  - Input sanitization

- [x] Logging system (`logger.py`)
  - Rotating logs
  - JSON audit
  - Multiple log levels

- [x] Backup system (`backup.py`)
  - Configuration backup
  - Restoration
  - Automatic cleanup

### Phase 5: Testing and Documentation (100% Complete)

- [x] Unit tests
  - `test_validator.py`
  - `test_user_manager.py`

- [x] Complete documentation
  - README.md with instructions
  - Development documentation
  - Known issues guide

## System Architecture

### Main Components

```
┌─────────────────────────────────────────────┐
│          GTK4 Interface (UI)                │
│  ┌──────────────┐      ┌─────────────────┐ │
│  │ MainWindow   │      │  UserDialog     │ │
│  └──────────────┘      └─────────────────┘ │
└─────────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────┐
│         Core Modules (Backend)              │
│  ┌──────────────┐  ┌──────────────────────┐│
│  │UserManager   │  │  RDPConfig           ││
│  └──────────────┘  └──────────────────────┘│
│  ┌──────────────┐  ┌──────────────────────┐│
│  │DEInstaller   │  │  SessionMonitor      ││
│  └──────────────┘  └──────────────────────┘│
└─────────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────┐
│      Utilities & Security                   │
│  ┌──────────────┐  ┌──────────────────────┐│
│  │PolicyKit     │  │  Validator           ││
│  │Helper        │  │                      ││
│  └──────────────┘  └──────────────────────┘│
│  ┌──────────────┐  ┌──────────────────────┐│
│  │Logger        │  │  Backup              ││
│  └──────────────┘  └──────────────────────┘│
└─────────────────────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────┐
│         Operating System                    │
│    Linux Users, xrdp, Desktop Environments  │
└─────────────────────────────────────────────┘
```

### User Creation Flow

1. **UI**: User fills form
2. **Validation**: Validator verifies data
3. **UserManager**: Creates user structure
4. **PolicyKit**: Requests admin privileges
5. **Helper**: Executes `useradd` with privileges
6. **RDPConfig**: Configures xrdp session
7. **DEInstaller**: Installs DE if necessary
8. **Audit**: Records action in logs
9. **Backup**: Creates configuration backup
10. **UI**: Updates user list

## Internal API

### UserManager

```python
# Create user
user = user_manager.create_user(
    username="john",
    password="StrongPass123",
    desktop_env="xfce",
    full_name="John Doe"
)

# List users
users = user_manager.list_users()

# Get specific user
user = user_manager.get_user("john")

# Delete user
success = user_manager.delete_user("john", remove_home=True)
```

### RDPConfig

```python
# Create session configuration
rdp_config.create_user_session(
    username="john",
    uid=5000,
    desktop_env="xfce",
    rdp_port=3389
)

# Get session status
status = rdp_config.get_session_status("john")

# Available ports
ports = rdp_config.get_available_ports(start_port=3389, count=10)
```

### SessionMonitor

```python
# Get active sessions
sessions = session_monitor.get_active_sessions()

# Check if user is connected
is_connected = session_monitor.is_user_connected("john")

# Get server IP
ip = session_monitor.get_ip_address()

# System statistics
stats = session_monitor.get_system_stats()
```

## Development

### Environment Setup

```bash
# Clone and enter directory
git clone <repo>
cd RemoteApps-RDP

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pytest

# Run in development mode
python3 src/main.py
```

### Adding a New Desktop Environment

1. Edit `src/core/de_installer.py`
2. Add entry in `DE_PACKAGES`:

```python
'budgie': {
    'name': 'Budgie',
    'packages': ['budgie-desktop', 'budgie-extras'],
    'size_mb': 500,
    'startup_cmd': 'budgie-desktop'
}
```

3. Test the installation

### Adding New Validation

1. Edit `src/utils/validator.py`
2. Add static method:

```python
@staticmethod
def validate_something(value: str) -> Tuple[bool, str]:
    if not value:
        return False, "Value cannot be empty"
    return True, ""
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_validator.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

## Code Standards

### Python

- **PEP 8**: Follow style guide
- **Type Hints**: Use when possible
- **Docstrings**: Document all public functions
- **Logging**: Use logger instead of print

### GTK/UI

- **Templates**: Use Gtk.Template for UI
- **Signals**: Connect via `connect()`
- **CSS Classes**: Use Adwaita classes when possible

### Git

- **Commits**: Clear and descriptive messages
- **Branches**: `feature/`, `bugfix/`, `hotfix/`
- **Pull Requests**: One feature per PR

## Debugging

### Enable Debug Logs

```bash
# Environment variable
export G_MESSAGES_DEBUG=all
export GTK_DEBUG=interactive

# Run application
python3 src/main.py
```

### System Logs

```bash
# Application logs
tail -f ~/.local/share/rdp-session-manager/logs/rdp-session-manager.log

# Audit logs
tail -f ~/.local/share/rdp-session-manager/logs/audit.log

# xrdp logs
sudo tail -f /var/log/xrdp/xrdp.log
```

### PolicyKit Debug

```bash
# Check installed policy
pkaction --verbose --action-id com.rdp.SessionManager.create-user

# Test authorization
pkcheck --action-id com.rdp.SessionManager.create-user --process $$
```

## Build and Distribution

### Build with Meson

```bash
# Configure
meson setup builddir --prefix=/usr

# Compile
meson compile -C builddir

# Install
sudo meson install -C builddir

# Uninstall
sudo ninja -C builddir uninstall
```

### Create Debian Package

```bash
# TODO: Add support for dpkg-buildpackage
```

### Create Flatpak

```bash
# TODO: Add flatpak manifest
```

## Additional Resources

- [GTK4 Documentation](https://docs.gtk.org/gtk4/)
- [libadwaita Documentation](https://gnome.pages.gitlab.gnome.org/libadwaita/)
- [Python GObject Introspection](https://pygobject.readthedocs.io/)
- [PolicyKit Documentation](https://www.freedesktop.org/software/polkit/docs/)
- [xrdp Documentation](https://github.com/neutrinolabs/xrdp)
