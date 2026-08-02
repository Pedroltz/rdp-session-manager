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
/usr/bin/cp -a "$(dirname "$EXE_PATH")/." "$APPS_DIR/"
/usr/bin/chown -R "$USERNAME:rdp-users" "$APPS_DIR" "$WINE_PREFIX"
/usr/bin/chmod 755 "$TARGET_EXE"

printf '%s\n' "$TARGET_EXE" > "$HOME_DIR/.winege_app_path"
cat > "$HOME_DIR/.windows_runtime.json" <<EOF
{
  "schema_version": 1,
  "runtime": "umu",
  "launcher": "$UMU_BIN",
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
cat > "$HOME_DIR/.launch_winege_app.sh" <<EOF
#!/bin/bash
export WINEPREFIX="$WINE_PREFIX"
export XDG_DATA_HOME="$SHARED_RUNTIME_ROOT"
export GAMEID="umu-default"
export STORE="none"
export PROTONPATH="UMU-Proton"
exec "$UMU_BIN" "$TARGET_EXE" "\$@"
EOF
/usr/bin/chown "$USERNAME:rdp-users" "$HOME_DIR/.launch_winege_app.sh"
/usr/bin/chmod 755 "$HOME_DIR/.launch_winege_app.sh"

echo "OK umu Windows runtime configured for $USERNAME"
