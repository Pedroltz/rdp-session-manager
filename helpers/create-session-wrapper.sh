#!/bin/bash
# Write the stable .xsession entry point used by all RDPSM profile types.
set -eu

USERNAME="${1:-}"
HOME_DIR="${2:-}"
[ -n "$USERNAME" ] && [ -d "$HOME_DIR" ] || {
    echo "Usage: $0 USERNAME HOME_DIR" >&2
    exit 2
}

INSTALL_ROOT="/opt/rdp-users"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
/usr/bin/install -m 755 "$SCRIPT_DIR/rdpsm-session.py" "$INSTALL_ROOT/rdpsm-session.py"
if [ -f "$SCRIPT_DIR/rdp-session-launcher.py" ]; then
    /usr/bin/install -m 755 "$SCRIPT_DIR/rdp-session-launcher.py" "$INSTALL_ROOT/rdp-session-launcher.py"
fi

XSESSION_FILE="$HOME_DIR/.xsession"
cat > "$XSESSION_FILE" <<EOF
#!/bin/bash
export HOME="$HOME_DIR"
export USER="$USERNAME"
export LOGNAME="$USERNAME"
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin:/var/lib/flatpak/exports/bin:\$PATH"
export XDG_DATA_DIRS="/var/lib/snapd/desktop:/var/lib/flatpak/exports/share:$HOME_DIR/.local/share/flatpak/exports/share:/usr/local/share:/usr/share:\${XDG_DATA_DIRS:-}"
if [ -f /etc/default/keyboard ]; then
    . /etc/default/keyboard
    setxkbmap -layout "\${XKBLAYOUT:-us}" -variant "\${XKBVARIANT:-}" -model "\${XKBMODEL:-pc105}" 2>/dev/null || true
fi
if [ -z "\${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
    eval "\$(dbus-launch --sh-syntax --exit-with-session)"
fi
exec /usr/bin/python3 "$INSTALL_ROOT/rdpsm-session.py" "\${1:-}"
EOF
/usr/bin/chmod 755 "$XSESSION_FILE"
/usr/bin/chown "$USERNAME:rdp-users" "$XSESSION_FILE"
/usr/bin/ln -sfn "$XSESSION_FILE" "$HOME_DIR/.xinitrc"
/usr/bin/chown -h "$USERNAME:rdp-users" "$HOME_DIR/.xinitrc"
