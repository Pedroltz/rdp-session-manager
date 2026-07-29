# Changelog - RDP Session Manager

## [0.3.6] - 2026-07-28

### Changed
- On Arch, the installer now automatically prepares `yay` by the official PKGBUILD `yay-bin` when no AUR helper is available
- AUR commands that can renew `sudo` authentication now use the terminal directly
- Installer, application interface, helper output, documentation, and tests are now maintained entirely in English

### Fixed
- Prevent internal `makepkg` prompts from expiring hidden behind the progress bar during xrdp installation

## [0.3.5] - 2026-07-28

### Changed
- Releases now publish only `install.sh` and a verified ZIP bundle with the installer and Debian/Arch packages
- Bootstrap validates the SHA-256 digest provided by GitHub and removes temporary files when finished

### Fixed
- `--release` maintains compatibility with older releases that still use separate assets

## [0.3.4] - 2026-07-28

### Fixed
- The `curl | bash` command now reads interactive commits from the terminal instead of the already consumed pipe
- Non-terminal runs receive a clear message and can still use `--yes` for non-interactive mode

## [0.3.3] - 2026-07-28

### Changed
- Public installer link automatically tracks the latest stable release
- The release workflow validates all artifacts and runs bootstrap tests before publishing

### Fixed
- Bootstrap now accepts `SHA256SUMS` inputs in text (`installer.pyz`) and binary (`*installer.pyz`) formats

## [0.3.2] - 2026-07-28

### Added
- New visual Python installer with rich interface, progress bars and detailed logs
- Secure Bootstrap for direct installation via GitHub stable release, with SHA-256 validation
- Documented support for Ubuntu/Debian and Arch/Manjaro/EndeavourOS/CachyOS
- Optional installation of Wine, 32-bit libraries and `multilib` on Arch
- Transparent fallback to compile `xrdp` and `xorgxrdp` from the AUR without `yay` or `paru`
- CI and release workflows to generate DEB, Arch package, zipapp, bootstrap and `SHA256SUMS`

### Changed
- Organized installation tools in `installer/`
- Local installer executable with `python -m installer --local`
- `apt`, `pacman`, AUR operations and downloads are now recorded in the installation log
- Operation bars use native percentages when managers provide real progress
- Updated installation, local testing, Wine, AUR and uninstallation documentation

### Fixed
- Interactive confirmations are no longer hidden behind the progress bar
- Arch no longer uses isolated `pacman -Sy` and imports PGP keys declared by PKGBUILDs
- Arch dependency tests use a simulated CI distribution

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
