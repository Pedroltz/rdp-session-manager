#!/bin/bash
# Helper script to change RDP session type of existing user
# Uso: pkexec change-session-type.sh USERNAME SESSION_TYPE SESSION_COMMAND [APP_ARGS]

set -e

if [ "$#" -lt 3 ]; then
    echo "Uso: $0 USERNAME SESSION_TYPE SESSION_COMMAND [APP_ARGS]"
    exit 1
fi

USERNAME="$1"
SESSION_TYPE="$2"        # 'desktop' or 'remoteapp'
SESSION_COMMAND="$3"     # DE command or application command
APP_ARGS="$4" # Arguments (optional)

# Check if user exists
if ! id "$USERNAME" &>/dev/null; then
    echo "Error: User $USERNAME does not exist"
    exit 1
fi

# Get user's home directory
HOME_DIR=$(getent passwd "$USERNAME" | cut -d: -f6)

if [ ! -d "$HOME_DIR" ]; then
    echo "Error: Home directory $HOME_DIR not found"
    exit 1
fi

echo "Changing session type from $USERNAME to: $SESSION_TYPE"

# Detect system keyboard layout
XKBLAYOUT="us"
XKBVARIANT=""
XKBMODEL="pc105"

if [ -f /etc/default/keyboard ]; then
    source /etc/default/keyboard
    echo "Keyboard layout detected: $XKBLAYOUT"
fi

# Build command setxkbmap
SETXKBMAP_CMD="setxkbmap -layout $XKBLAYOUT"
if [ -n "$XKBVARIANT" ]; then
    SETXKBMAP_CMD="$SETXKBMAP_CMD -variant $XKBVARIANT"
fi
if [ -n "$XKBMODEL" ]; then
    SETXKBMAP_CMD="$SETXKBMAP_CMD -model $XKBMODEL"
fi

# Check if user has active processes
ACTIVE_PIDS=$(pgrep -u "$USERNAME" 2>/dev/null || true)
if [ -n "$ACTIVE_PIDS" ]; then
    echo "Terminating $USERNAME sessions..."
    /usr/bin/pkill -TERM -u "$USERNAME" 2>/dev/null || true
    sleep 2
    # Force shutdown if there are still processes
    /usr/bin/pkill -KILL -u "$USERNAME" 2>/dev/null || true
fi

# Recreate .xsession file
XSESSION_FILE="$HOME_DIR/.xsession"
echo "→ Recreating .xsession file..."

if [ "$SESSION_TYPE" = "remoteapp" ]; then
    # RemoteApp mode
    cat > "$XSESSION_FILE" <<'EOFSCRIPT'
#!/bin/bash
# RDP Session startup script for $USERNAME
# Mode: RemoteApp

# Set environment variables
export HOME=$HOME_DIR
export USER=$USERNAME
export LOGNAME=$USERNAME

# Configure D-Bus
if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
    eval $(dbus-launch --sh-syntax --exit-with-session)
fi

# Configure keyboard layout (inherited from host system)
$SETXKBMAP_CMD

# Configure openbox with window decorations for RemoteApps
mkdir -p $HOME_DIR/.config/openbox
cat > $HOME_DIR/.config/openbox/rc.xml <<'OPENBOXEOF'
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <applications>
    <application class="*">
      <maximized>yes</maximized>
      <decor>yes</decor>
    </application>
  </applications>
</openbox_config>
OPENBOXEOF

# Start openbox window manager (better for fullscreen apps)
openbox --config-file $HOME_DIR/.config/openbox/rc.xml &
sleep 1

# Launch RemoteApp
exec $SESSION_COMMAND $APP_ARGS
EOFSCRIPT

    # Replace variables in the script
    /usr/bin/sed -i "s|\$USERNAME|$USERNAME|g" "$XSESSION_FILE"
    /usr/bin/sed -i "s|\$HOME_DIR|$HOME_DIR|g" "$XSESSION_FILE"
    /usr/bin/sed -i "s|\$SESSION_COMMAND|$SESSION_COMMAND|g" "$XSESSION_FILE"
    /usr/bin/sed -i "s|\$APP_ARGS|$APP_ARGS|g" "$XSESSION_FILE"
    /usr/bin/sed -i "s|\$SETXKBMAP_CMD|$SETXKBMAP_CMD|g" "$XSESSION_FILE"
else
    # Desktop mode
    cat > "$XSESSION_FILE" <<EOF
#!/bin/bash
# RDP Session startup script for $USERNAME
# Mode: Desktop

# Set environment variables
export HOME=$HOME_DIR
export USER=$USERNAME
export LOGNAME=$USERNAME

# Configure D-Bus
if [ -z "\$DBUS_SESSION_BUS_ADDRESS" ]; then
    eval \$(dbus-launch --sh-syntax --exit-with-session)
fi

# Configure keyboard layout (inherited from host system)
$SETXKBMAP_CMD

# Start desktop environment
exec $SESSION_COMMAND
EOF
fi

/usr/bin/chmod 755 "$XSESSION_FILE"
/usr/bin/chown "$USERNAME:rdp-users" "$XSESSION_FILE"

echo "OK Session type successfully changed to $SESSION_TYPE"
echo " - Keyboard layout: $XKBLAYOUT"
exit 0
