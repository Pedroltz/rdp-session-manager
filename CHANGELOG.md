# Changelog - RDP Session Manager

## [0.5.2] - 2026-08-02

### Added
- **Fullscreen RDP Connection Launch**: Configured FreeRDP client launcher in the GTK4 GUI to launch RDP sessions directly in full screen mode (`/f`) with native resolution negotiation.

### Fixed
- **Connection Sources UI Glitch**: Resolved UI duplication/cloning rendering glitch when adding new connection sources in `ConnectionSourcesDialog` by implementing explicit `_added_rows` tracking.
- **Connection Sources Actions**: Added "Make Default" action button directly in the profile management list and automatic real-time parent window UI synchronization.

## [0.5.1] - 2026-08-01

### Fixed
- **Arch Linux Desktop Package Detection**: Fixed DE package detection in `DEInstaller.is_de_installed()` on Arch Linux by adding support for `pacman -Qg` package groups and system PATH binary checks (`shutil.which`).
- **Arch Linux Session Initialization**: Added automatic `.xinitrc` symlink creation pointing to `.xsession` in all session helper scripts and `UserManager._detect_session_info()` fallback, preventing Arch Linux `/etc/xrdp/startwm.sh` from crashing on missing `xterm`/`xclock`.
- **GNOME & KDE Session Compatibility**: Improved GNOME session launch logic to detect `gnome-flashback` vs standard `gnome-session` and export proper X11 desktop variables (`XDG_CURRENT_DESKTOP`, `XDG_SESSION_DESKTOP`, `KDE_SESSION_VERSION=6`).
- **RemoteApp Lifecycle & Instant Disconnect**: Implemented EWMH window tracking (`xprop -root _NET_CLIENT_LIST`) in RemoteApp launcher scripts, ensuring forking/Electron applications (Visual Studio Code, Chrome, etc.) remain open during use and **instantly disconnect the RDP session when the window is closed**.

## [0.5.0] - 2026-07-31

### Added
- **Multi-Connection Sources**: Support for configuring multiple connection profiles per RDP user (Full Desktop, RemoteApp Linux, and WineGE Windows applications)
- **Interactive Session Launcher**: Modern GTK4/Libadwaita fullscreen launcher GUI presented upon RDP login to select connection sources
- **Profile Management GUI**: New `Connection Sources` dialog allowing users to add, manage, default, and export `.rdp` shortcut files
- **CLI Parity**: Subcommands under `rdpsm profile` (`list`, `add`, `remove`, `set-default`, `export`) providing 100% feature parity with the GUI
- **Elevated Profile Helper**: `helpers/update-rdp-user-profiles.sh` script using `pkexec`/`sudo` for reliable system-level profile persistence and `.xsession` updates

### Fixed
- Fixed X11 window geometry negotiation by embedding a light Openbox configuration in `.xsession` to force 100% fullscreen presentation across all RDP clients (including Windows MSTSC)
- Fixed session type detection in `UserManager._detect_session_info` to read `~/.rdp_profiles.json` directly and prevent false positive WineGE profile duplication

## [0.4.7] - 2026-07-31

### Added
- RemoteApp support for Snap and Flatpak applications alongside APT packages
- Automated RemoteApp E2E test battery `tests/e2e/test_remoteapps.sh` for APT, Snap, and Flatpak apps
- Automatic `/snap/bin` and `/var/lib/flatpak/exports/bin` environment injection in `.xsession` scripts

## [0.4.6] - 2026-07-31

### Added
- Multi-desktop end-to-end test script `tests/e2e/test_all_desktops.sh` for XFCE, GNOME, and KDE Plasma

### Fixed
- Fixed GNOME session startup on RDP by utilizing `gnome-session-flashback` under X11
- Fixed KDE Plasma session startup on Debian/Ubuntu by adding `plasma-session-x11` package requirement
- Injected XDG environment variables (`XDG_CURRENT_DESKTOP`, `XDG_SESSION_TYPE=x11`, `DESKTOP_SESSION`) into `.xsession` generation scripts for all desktop environments

## [0.4.5] - 2026-07-30

### Fixed
- The release installer now authenticates with `sudo` before starting live progress, keeping password prompts visible in headless terminals
- Interactive terminals take precedence over graphical askpass even when stale or forwarded display variables are present

## [0.4.4] - 2026-07-30

### Changed
- Headless and CLI sessions now request administrative passwords through interactive terminal `sudo`
- Graphical PolicyKit authentication now requires both a display and a desktop D-Bus session
- The release installer uses graphical askpass only inside a real desktop D-Bus session

### Fixed
- Forwarded or stale `DISPLAY` values no longer cause `pkexec` authentication attempts on CLI-only servers
- User creation reports the privilege method that is actually being used

## [0.4.3] - 2026-07-30

### Changed
- Limited new desktop sessions and installation to KDE Plasma, GNOME, and XFCE
- Added distribution-specific desktop package installation for Ubuntu, Debian, Arch, and supported derivatives
- Added the Plasma X11 session and GNOME Flashback requirements used by xorgxrdp on current Arch Linux

### Fixed
- Desktop installation now uses `pacman -Syu --needed` on Arch instead of Debian-only APT and DPKG commands
- Unsupported desktop IDs are rejected instead of silently creating an XFCE session

## [0.4.2] - 2026-07-29

### Added
- Real end-to-end RDP test that creates an XFCE user through `rdpsm` and authenticates with FreeRDP
- Independent checks for the desktop process, an in-session autostart marker, and rendered screenshot content
- Automatic FreeRDP, xrdp, xrdp-sesman, and Xorg diagnostics for failed desktop sessions

### Changed
- Ubuntu 24.04 quality and pre-publish installation jobs now require a successful rendered RDP desktop
- RDP test artifacts are retained for inspection and the temporary account is always removed

## [0.4.1] - 2026-07-29

### Changed
- Renamed the continuous integration workflows to `Quality Checks` and `Publish Release`
- Replaced installer smoke tests with real package installations across Ubuntu, Debian, and Arch Linux
- Added prerelease validation through the public GitHub installer before stable release promotion

### Fixed
- Enabled the i386 architecture before installing Wine dependencies on Debian-based x86_64 systems

## [0.4.0] - 2026-07-29

### Changed
- Standardized the installer, application interface, command-line output, and package metadata in English
- Kept the verified release bundle and interactive terminal behavior introduced in the 0.3.x series

## [0.3.5] - 2026-07-28

### Changed
- Releases agora publicam somente `install.sh` e um bundle ZIP verificado com o instalador e os pacotes Debian/Arch
- O bootstrap valida o digest SHA-256 fornecido pelo GitHub e remove os arquivos temporários ao finalizar

### Fixed
- `--release` mantém compatibilidade com releases antigas que ainda usam assets separados

## [0.3.4] - 2026-07-28

### Fixed
- O comando `curl | bash` agora lê confirmações interativas pelo terminal em vez do pipe já consumido
- Execuções sem terminal recebem uma mensagem clara e ainda podem usar `--yes` para o modo não interativo

## [0.3.3] - 2026-07-28

### Changed
- O link público do instalador acompanha automaticamente a release estável mais recente
- O workflow de release valida todos os artefatos e executa os testes do bootstrap antes da publicação

### Fixed
- O bootstrap agora aceita entradas `SHA256SUMS` nos formatos texto (`installer.pyz`) e binário (`*installer.pyz`)

## [0.3.2] - 2026-07-28

### Added
- Novo instalador visual em Python com interface Rich, barras de progresso e logs detalhados
- Bootstrap seguro para instalação direta pela release estável do GitHub, com validação SHA-256
- Suporte documentado a Ubuntu/Debian e Arch/Manjaro/EndeavourOS/CachyOS
- Instalação opcional de Wine, bibliotecas de 32 bits e `multilib` no Arch
- Fallback transparente para compilar `xrdp` e `xorgxrdp` pelo AUR sem `yay` ou `paru`
- Workflows de CI e release para gerar DEB, pacote Arch, zipapp, bootstrap e `SHA256SUMS`

### Changed
- Organizadas as ferramentas de instalação em `installer/`
- Instalador local executável com `python -m installer --local`
- Operações do `apt`, `pacman`, AUR e downloads agora ficam registradas no log de instalação
- Barras de operação usam percentuais nativos quando os gerenciadores fornecem progresso real
- Atualizada a documentação de instalação, teste local, Wine, AUR e desinstalação

### Fixed
- Confirmações interativas não ficam mais escondidas atrás da barra de progresso
- Arch não usa mais `pacman -Sy` isolado e importa as chaves PGP declaradas pelos PKGBUILDs
- Testes de dependências Arch usam uma distribuição simulada em CI

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
