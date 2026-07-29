# WineGE RemoteApp - Guia de Uso

This document explains how to create RemoteApps that run Windows applications using **WineGE** (Wine-GE Custom) in RDP Session Manager.

## What is WineGE RemoteApp?

WineGE RemoteApp allows you to run Windows applications (.exe) as RemoteApps via RDP, using Wine-GE (an improved version of Wine maintained by GloriousEggroll) instead of conventional Wine.

### Why WineGE Instead of Wine?

- **Best compatibility** with modern games and apps
- **Additional patches** for DirectX, DXVK, VKD3D
- **Better performance** in many cases
- **Support for recent technologies** (FSR, Ray Tracing via VKD3D, etc.)
- **Frequent updates** with bug fixes

## Requisitos

- Windows application (.exe) - can be:
  - Installer (setup.exe, installer.exe)
  - Portable executable (app.exe)
- Enough disk space (~2-3GB for WineGE + app)
- Internet connection (to download WineGE the first time)

## How to Create a WineGE RemoteApp User

### Via Graphical Interface (GUI)

1. Abra o RDP Session Manager
2. Click "Add User"
3. Fill in user data
4. Em "Session Type", selecione **"WineGE RemoteApp"**
5. In "Application Command", click "Browse" and select the .exe file
6. (Optional) Add arguments in "Application Arguments"
7. Click "Create User"

The system will:
- Create the user
- Download and install WineGE (~1.5GB)
- Create a Wine Prefix
- Install the application (if it is an installer)
- Configure RemoteApp

### Via Command Line (CLI)

#### Create new user with WineGE RemoteApp:

```bash
# Example with portable application
rdpsm user create winuser1 \
    --session-type winege-remoteapp \
    --app-command /path/to/MyApp.exe \
    --fullname "Windows App User"

# Example with installer
rdpsm user create winuser2 \
    --session-type winege-remoteapp \
    --app-command /path/to/MyAppSetup.exe \
    --fullname "Windows Game User"

# With arguments
rdpsm user create winuser3 \
    --session-type winege-remoteapp \
    --app-command /path/to/MyApp.exe \
    --app-args "--windowed --no-intro" \
    --fullname "Windows App User"
```

## Manage WineGE Executables via CLI

### List available executables

List all .exe executables found in the user's Wine Prefix and WindowsApps:

```bash
rdpsm user winege list USERNAME
```

This shows:
- Portable executables in `WindowsApps/`
- Applications installed on `Program Files/` and `Program Files (x86)/`
- Path of the current executable

### Select executable interactively

Select an executable interactively and update automatically:

```bash
rdpsm user winege select USERNAME
```

This command:
1. List all available executables
2. Allows you to select one by number
3. Confirm selection
4. Update the path automatically using `pkexec`

**Exemplo de uso:**

```bash
$ rdpsm user winege select zionwine

Select Executable for zionwine
===============================

  1. /opt/rdp-users/zionwine/WindowsApps/App.exe
  2. /opt/rdp-users/zionwine/.wine/drive_c/Program Files/MyApp/myapp.exe
  3. /opt/rdp-users/zionwine/.wine/drive_c/Program Files (x86)/Game/game.exe

Select number (1-3) or 'q' to quit: 2

→ Selected: /opt/rdp-users/zionwine/.wine/drive_c/Program Files/MyApp/myapp.exe
Update executable path? (yes/no): yes
OK Executable updated successfully
→ New path: /opt/rdp-users/zionwine/.wine/drive_c/Program Files/MyApp/myapp.exe
```

### Update executable manually

If you already know the executable path:

```bash
sudo /usr/share/rdp-session-manager/helpers/update-winege-exe.sh \
    USERNAME \
    "/path/to/new/app.exe"
```

## Add WineGE App to Existing User

If you already have a user created and want to convert -lo to WineGE RemoteApp:

### Via CLI:

```bash
# 1. Configure WineGE on the user (as root or with pkexec)
sudo /usr/share/rdp-session-manager/helpers/setup-winege-app.sh \
    USERNAME \
    /opt/rdp-users/USERNAME \
    /path/to/app.exe

# 2. Change user session type
rdpsm user session-type USERNAME winege-remoteapp
```

## Window Decoration

All RemoteApps (Linux and WineGE) now include **window decorations** (window decorations) with minimize, maximize and close buttons. This is especially useful for Wine applications that need to be moved or resized.

### Features:
- **Control buttons**: Minimize, maximize, close
- **Title bar**: Allows you to drag and move the window
- **Resizing**: Clickable borders to adjust size
- **Window Manager**: Uses Openbox for efficient management

This solves the common problem where RemoteApp applications get "stuck" without window controls.

## File Structure

After configuration, the WineGE user will have the following structure:

```
/opt/rdp-users/USERNAME/
├── .wine/ # Wine Prefix (virtualized Windows environment)
│   ├── drive_c/                    # Disco C: virtual
│ │ ├── Program Files/ # Installed applications
│   │   ├── Program Files (x86)/
│ │ └── users/ # Windows user data
│   └── ...
├── .local/share/winege/ # WineGE installation
│   └── wine-ge-custom-GE-Proton9-20/
├── WindowsApps/ # Copied executables
│   └── MyApp.exe
├── .winege_app_path # Path of main executable
├── .winege_config # WineGE Configuration
├── .launch_winege_app.sh # Launch wrapper script
└── .xsession # RDP initialization script
```

## Exemplos de Uso

### Example 1: Notepad++ (Portable Application)

```bash
# Download portable Notepad++ first
wget https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.6/npp.8.6.portable.x64.zip
unzip npp.8.6.portable.x64.zip -d /tmp/notepadpp

# Create user
rdpsm user create notepad_user \
    --session-type winege-remoteapp \
    --app-command /tmp/notepadpp/notepad++.exe \
    --fullname "Notepad++ User"
```

### Example 2: Application with Installer

```bash
# Assuming you have a MyAppSetup.exe installer
rdpsm user create myapp_user \
    --session-type winege-remoteapp \
    --app-command /home/user/Downloads/MyAppSetup.exe \
    --fullname "My App User"

# During creation, the installer will run interactively
# Follow the Windows installer instructions
```

### Example 3: Steam Game (Advanced Example)

```bash
# For games you may need special arguments
rdpsm user create game_user \
    --session-type winege-remoteapp \
    --app-command /path/to/game.exe \
    --app-args "-windowed -high" \
    --fullname "Game User"
```

## Troubleshooting

### Application does not start

1. Check the logs:
   ```bash
   rdpsm user info USERNAME
   journalctl -xe | grep xrdp
   ```

2. Teste manualmente:
   ```bash
   su - USERNAME
   bash ~/.launch_winege_app.sh
   ```

### Installer did not find the executable

After installation, the system automatically tries to find the main .exe. If it fails:

1. Find the executable manually:
   ```bash
   find /opt/rdp-users/USERNAME/.wine/drive_c/ -name "*.exe" | grep -v unins
   ```

2. Update the path:
   ```bash
   echo "/path/to/correct/app.exe" | sudo tee /opt/rdp-users/USERNAME/.winege_app_path
   ```

### WineGE does not download

- Check internet connection
- Download manually from: https://github.com/GloriousEggroll/wine-ge-custom/releases
- Extraia em `/opt/rdp-users/USERNAME/.local/share/winege/`

### Application needs additional libraries

Enter the user's Wine Prefix and install:

```bash
su - USERNAME
export WINEPREFIX="$HOME/.wine"
export PATH="$HOME/.local/share/winege/wine-ge-custom-GE-Proton9-20/bin:$PATH"

# Install dependencies via winetricks
winetricks vcrun2019 dotnet48
```

## Limitations

- **Games with anti-cheat**: May not work
- **DirectX 12**: Suporte limitado via VKD3D
- **Applications that require drivers**: May have problems
- **Performance**: Depends on hardware and application compatibility

## Dicas de Performance

1. **Use SSD**: WineGE works best with fast storage
2. **Sufficient RAM**: Recommended 4GB+ per user
3. **Dedicated GPU**: For games or graphics apps
4. **Vulkan drivers**: Install updated Vulkan drivers

## Comparison: RemoteApp vs WineGE RemoteApp

| Feature | RemoteApp | WineGE RemoteApp |
|----------------|-----------|------------------|
| Application Type | Native Linux | Windows (.exe) |
| Installation | Quick | Slow (WineGE download) |
| Disk space | Small | ~2-3GB |
| Performance | Native | Emulated (may be slower) |
| Compatibility | 100% Linux | Varies by application |

## References

- [WineGE GitHub](https://github.com/GloriousEggroll/wine-ge-custom)
- [Wine AppDB](https://appdb.winehq.org/) - App Compatibility
- [ProtonDB](https://www.protondb.com/) - Game compatibility
- [Winetricks](https://github.com/Winetricks/winetricks)

## Suporte

For specific issues with WineGE RemoteApps, please open an issue at:
https://github.com/your-user/rdp-session-manager/issues
