#!/bin/bash
# Configure a per-user Windows prefix using the maintained umu launcher.
# Existing WineGE installations remain usable through rdpsm-session.py's
# explicit legacy fallback, but this helper never creates new legacy runtimes.
set -euo pipefail

USERNAME="${1:-}"
HOME_DIR="${2:-}"
EXE_PATH="${3:-}"
WINE_PREFIX="${4:-$HOME_DIR/.wine}"

[ -n "$USERNAME" ] && [ -d "$HOME_DIR" ] && [ -f "$EXE_PATH" ] || {
    echo "Usage: $0 USERNAME HOME_DIR EXE_PATH [WINE_PREFIX]" >&2
    exit 2
}

UMU_BIN="$(command -v umu-run || true)"
if [ -z "$UMU_BIN" ]; then
    echo "Error: umu-run is required for new Windows RemoteApps." >&2
    echo "Install umu-launcher through the RDPSM installer or your distribution." >&2
    exit 1
fi

SHARED_RUNTIME_ROOT="/opt/rdp-session-manager/runtimes"
/usr/bin/mkdir -p "$SHARED_RUNTIME_ROOT"
/usr/bin/chgrp rdp-users "$SHARED_RUNTIME_ROOT"
/usr/bin/chmod 2775 "$SHARED_RUNTIME_ROOT"

APPS_DIR="$HOME_DIR/WindowsApps"
EXE_BASENAME="$(basename "$EXE_PATH")"
TARGET_EXE="$APPS_DIR/$EXE_BASENAME"
/usr/bin/mkdir -p "$APPS_DIR" "$WINE_PREFIX"
# Copy only the selected executable. Copying its entire source directory could
# unintentionally import every file from locations such as ~/Downloads.
SOURCE_REAL="$(readlink -f "$EXE_PATH")"
TARGET_REAL="$(readlink -f "$TARGET_EXE" 2>/dev/null || true)"
if [ "$SOURCE_REAL" != "$TARGET_REAL" ]; then
    /usr/bin/cp -a "$EXE_PATH" "$TARGET_EXE"
fi
/usr/bin/chown -R "$USERNAME:rdp-users" "$APPS_DIR" "$WINE_PREFIX"
/usr/bin/chmod 755 "$TARGET_EXE"

printf '%s\n' "$TARGET_EXE" > "$HOME_DIR/.winege_app_path"

PREWARM_HELPER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/prewarm-umu-runtime.sh"
[ -x "$PREWARM_HELPER" ] || {
    echo "Error: UMU runtime prewarm helper is missing." >&2
    exit 1
}

RUNTIME_KIND="umu"
LAUNCHER_BIN="$UMU_BIN"
if ! "$PREWARM_HELPER" \
    "$USERNAME" "$HOME_DIR" "$WINE_PREFIX" "$SHARED_RUNTIME_ROOT"; then
    WINE_BIN="$(command -v wine || true)"
    if [ -z "$WINE_BIN" ]; then
        echo "Error: UMU preparation failed and system Wine is unavailable." >&2
        exit 1
    fi
    RUNTIME_KIND="wine"
    LAUNCHER_BIN="$WINE_BIN"
    echo "Warning: Windows RemoteApp configured with $("$WINE_BIN" --version) fallback." >&2
fi

cat > "$HOME_DIR/.windows_runtime.json" <<EOF
{
  "schema_version": 1,
  "runtime": "$RUNTIME_KIND",
  "launcher": "$LAUNCHER_BIN",
  "shared_runtime_root": "$SHARED_RUNTIME_ROOT",
  "wine_prefix": "$WINE_PREFIX",
  "executable": "$TARGET_EXE",
  "legacy_winege_available": false
}
EOF
/usr/bin/chown "$USERNAME:rdp-users" \
    "$HOME_DIR/.winege_app_path" "$HOME_DIR/.windows_runtime.json"
/usr/bin/chmod 600 "$HOME_DIR/.windows_runtime.json"

# Compatibility wrapper for older profiles. Argument boundaries are preserved.
if [ "$RUNTIME_KIND" = "umu" ]; then
    cat > "$HOME_DIR/.launch_winege_app.sh" <<EOF
#!/bin/bash
export WINEPREFIX="$WINE_PREFIX"
export XDG_DATA_HOME="$SHARED_RUNTIME_ROOT"
export GAMEID="umu-default"
export STORE="none"
export PROTONPATH="UMU-Proton"
IFS= read -r APP_PATH < "$HOME_DIR/.winege_app_path"
[ -n "\$APP_PATH" ] && [ -f "\$APP_PATH" ] || {
    echo "Windows application path is invalid: \$APP_PATH" >&2
    exit 2
}
exec "$UMU_BIN" "\$APP_PATH" "\$@"
EOF
else
    cat > "$HOME_DIR/.launch_winege_app.sh" <<EOF
#!/bin/bash
export WINEPREFIX="$WINE_PREFIX"
IFS= read -r APP_PATH < "$HOME_DIR/.winege_app_path"
[ -n "\$APP_PATH" ] && [ -f "\$APP_PATH" ] || {
    echo "Windows application path is invalid: \$APP_PATH" >&2
    exit 2
}
exec "$WINE_BIN" "\$APP_PATH" "\$@"
EOF
fi
/usr/bin/chown "$USERNAME:rdp-users" "$HOME_DIR/.launch_winege_app.sh"
/usr/bin/chmod 755 "$HOME_DIR/.launch_winege_app.sh"

echo "OK $RUNTIME_KIND Windows runtime configured for $USERNAME"
