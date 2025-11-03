# Changelog - RDP Session Manager

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


