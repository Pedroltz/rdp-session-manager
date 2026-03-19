# Changelog - RDP Session Manager

## [0.3.1] - 2026-03-19

### Changed
- Removed icons from user creation and edit dialogs for a cleaner interface
- Refactored `de_installer.py` for improved multi-distro package support
- Refactored `user_manager.py` reducing complexity and removing unused code
- Refactored `main_window.py` with cleaner layout and session management
- Improved `polkit.py` reducing privilege escalation complexity
- Updated `system_deps.py` with better dependency detection

### Fixed
- Fixed `test_get_all_network_ips` test failing when `netifaces` is installed (mock now forces fallback path)
- Fixed sudo privilege creation for new RDP users
- Removed obsolete helper scripts (`change-session-type.sh`, `create-rdp-user.sh`, `create-xsession.sh`)

## [0.3.0] - 2025-10-30

### Added
- WineGE RemoteApp support for running Windows applications via Wine
- Automatic WineGE (GE-Proton8-26) download and installation
- File picker for .exe selection in user creation and settings dialogs
- "List Available" button to show executables without sudo
- Helper script `winege-tools.sh` for managing WineGE users (list-exes, view-logs, copy-files)
- Full 32-bit library support and Wine dependencies in install.sh
- Documentation: `docs/WINEGE_REMOTEAPP.md` and `docs/WINE_DEPENDENCIES.md`

### Changed
- Increased timeout to 1200s for WineGE operations
- Auto-detect installers (PT/EN) and filter Windows default apps
- Better username validation (blocks reserved names)
- Wine performance optimizations (stack size, heap, debug logs)

### Fixed
- GTK4 FileDialog modal stacking issues
- Wine stack overflow errors (ulimit + registry configuration)
- Wine DISPLAY configuration for xrdp sessions
- Application file path issues with symlink and file copying


