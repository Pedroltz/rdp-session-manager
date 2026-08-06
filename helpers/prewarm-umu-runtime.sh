#!/bin/bash
# Download and validate the shared Proton/Steam runtime before first RDP login.
set -euo pipefail

USERNAME="${1:-}"
HOME_DIR="${2:-}"
WINE_PREFIX="${3:-$HOME_DIR/.wine}"
SHARED_RUNTIME_ROOT="${4:-/opt/rdp-session-manager/runtimes}"

[ "$(id -u)" -eq 0 ] || {
    echo "Error: UMU prewarm must run as root." >&2
    exit 1
}
[[ "$USERNAME" =~ ^[a-z][a-z0-9_-]{2,31}$ ]] || {
    echo "Error: invalid username." >&2
    exit 2
}
[ "$(getent passwd "$USERNAME" | cut -d: -f6)" = "$HOME_DIR" ] || {
    echo "Error: home directory does not match $USERNAME." >&2
    exit 2
}

UMU_BIN="$(command -v umu-run || true)"
RUNUSER_BIN="$(command -v runuser || true)"
[ -n "$UMU_BIN" ] && [ -n "$RUNUSER_BIN" ] || {
    echo "Error: umu-run and runuser are required." >&2
    exit 3
}

RUNTIME_DIR="$SHARED_RUNTIME_ROOT/umu/steamrt3"
PROTON_ROOT="$SHARED_RUNTIME_ROOT/Steam/compatibilitytools.d"
runtime_ready() {
    [ -f "$RUNTIME_DIR/.installed.ok" ] \
        && find "$RUNTIME_DIR" -maxdepth 1 -type d \
            -name 'sniper_platform_*' -print -quit | grep -q . \
        && find "$PROTON_ROOT" -mindepth 2 -maxdepth 2 -type f \
            -name toolmanifest.vdf -print -quit | grep -q .
}

if runtime_ready; then
    echo "OK Shared UMU runtime is already ready"
    exit 0
fi

echo "→ Downloading and validating the shared UMU runtime..."
PREWARM_LOG="$(mktemp /tmp/rdpsm-umu-prewarm.XXXXXX)"
/usr/bin/chown "$USERNAME:rdp-users" "$PREWARM_LOG"
trap '/usr/bin/rm -f -- "$PREWARM_LOG"' EXIT
set +e
"$RUNUSER_BIN" -u "$USERNAME" -- \
    env \
        HOME="$HOME_DIR" \
        USER="$USERNAME" \
        LOGNAME="$USERNAME" \
        XDG_DATA_HOME="$SHARED_RUNTIME_ROOT" \
        WINEPREFIX="$WINE_PREFIX" \
        GAMEID="umu-default" \
        STORE="none" \
        PROTONPATH="UMU-Proton" \
        UMU_HTTP_RETRIES="5" \
        UMU_HTTP_TIMEOUT="120" \
        "$UMU_BIN" createprefix >"$PREWARM_LOG" 2>&1
PREWARM_STATUS=$?
set -e

# createprefix may return non-zero after successfully preparing the prefix;
# cache validation is the authoritative result.
if ! runtime_ready; then
    echo "Warning: UMU/Proton could not download the required Steam runtime." >&2
    if /usr/bin/grep -Eq 'Connection reset|Temporary failure|Name or service not known|timed out' "$PREWARM_LOG"; then
        echo "Warning: repo.steampowered.com is unreachable; using the local Wine fallback." >&2
    else
        echo "Warning: umu-run exited with code $PREWARM_STATUS; using the local Wine fallback." >&2
    fi
    exit 4
fi

echo "OK Shared UMU runtime downloaded and validated"
