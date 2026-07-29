#!/bin/bash
# Helper script to create RDP user with pkexec
# Uso: pkexec helpers/create-rdp-user.sh USERNAME USER_UID HOME_DIR FULLNAME SESSION_TYPE SESSION_COMMAND [APP_ARGS]

set -e

USERNAME="$1"
USER_UID="$2"
HOME_DIR="$3"
FULLNAME="$4"
SESSION_TYPE="$5"        # 'desktop', 'remoteapp', or 'winege-remoteapp'
SESSION_COMMAND="$6" # DE command (e.g. startxfce4), app command (e.g. firefox), or .exe path for WineGE
APP_ARGS="$7" # App arguments (for remoteapp only)

# Validate parameters
if [ -z "$USERNAME" ] || [ -z "$USER_UID" ] || [ -z "$HOME_DIR" ]; then
    echo "Error: Insufficient parameters"
    echo "Uso: $0 USERNAME USER_UID HOME_DIR [FULLNAME] [SESSION_TYPE] [SESSION_COMMAND] [APP_ARGS]"
    exit 1
fi

# Defaults
SESSION_TYPE="${SESSION_TYPE:-desktop}"
SESSION_COMMAND="${SESSION_COMMAND:-startxfce4}"

echo "Creating RDP user: $USERNAME"

# Detect system keyboard layout
XKBLAYOUT="us"
XKBVARIANT=""
XKBMODEL="pc105"

if [ -f /etc/default/keyboard ]; then
    source /etc/default/keyboard
    echo "→ Keyboard layout detected: $XKBLAYOUT"
fi

# Build command setxkbmap
SETXKBMAP_CMD="setxkbmap -layout $XKBLAYOUT"
if [ -n "$XKBVARIANT" ]; then
    SETXKBMAP_CMD="$SETXKBMAP_CMD -variant $XKBVARIANT"
fi
if [ -n "$XKBMODEL" ]; then
    SETXKBMAP_CMD="$SETXKBMAP_CMD -model $XKBMODEL"
fi

# 1. Create group rdp-users if it does not exist
if ! getent group rdp-users > /dev/null 2>&1; then
    echo "→ Creating group rdp-users..."
    /usr/sbin/groupadd rdp-users
fi

#2. Create base directory if it does not exist
if [ ! -d "/opt/rdp-users" ]; then
    echo "→ Creating directory /opt/rdp-users..."
    /usr/bin/mkdir -p /opt/rdp-users
    /usr/bin/chmod 755 /opt/rdp-users
fi

# 3. Create user
echo "→ Creating user $USERNAME (UID: $USER_UID)..."
if [ -n "$FULLNAME" ]; then
    /usr/sbin/useradd -u "$USER_UID" -d "$HOME_DIR" -m -g rdp-users -s /bin/bash -c "$FULLNAME" "$USERNAME"
else
    /usr/sbin/useradd -u "$USER_UID" -d "$HOME_DIR" -m -g rdp-users -s /bin/bash "$USERNAME"
fi

# 4. Adjust home directory permissions (751 to allow .xsession to be read)
echo "→ Adjusting home directory permissions..."
/usr/bin/chmod 751 "$HOME_DIR"

# 5. Create .xsession file
echo "→ Creating .xsession file (mode: $SESSION_TYPE)..."
XSESSION_FILE="$HOME_DIR/.xsession"

if [ "$SESSION_TYPE" = "remoteapp" ]; then
    # RemoteApp mode - launch individual app
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
    sed -i "s|\$USERNAME|$USERNAME|g" "$XSESSION_FILE"
    sed -i "s|\$HOME_DIR|$HOME_DIR|g" "$XSESSION_FILE"
    sed -i "s|\$SESSION_COMMAND|$SESSION_COMMAND|g" "$XSESSION_FILE"
    sed -i "s|\$APP_ARGS|$APP_ARGS|g" "$XSESSION_FILE"
    sed -i "s|\$SETXKBMAP_CMD|$SETXKBMAP_CMD|g" "$XSESSION_FILE"
elif [ "$SESSION_TYPE" = "winege-remoteapp" ]; then
    # WineGE RemoteApp mode - launch Windows application via WineGE
    cat > "$XSESSION_FILE" <<'EOFSCRIPT'
#!/bin/bash
# RDP Session startup script for $USERNAME
# Mode: WineGE RemoteApp

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

# Start openbox window manager
openbox --config-file $HOME_DIR/.config/openbox/rc.xml &
sleep 1

# Launch WineGE RemoteApp using wrapper script
exec $HOME_DIR/.launch_winege_app.sh $APP_ARGS
EOFSCRIPT

    # Replace variables in the script
    sed -i "s|\$USERNAME|$USERNAME|g" "$XSESSION_FILE"
    sed -i "s|\$HOME_DIR|$HOME_DIR|g" "$XSESSION_FILE"
    sed -i "s|\$APP_ARGS|$APP_ARGS|g" "$XSESSION_FILE"
    sed -i "s|\$SETXKBMAP_CMD|$SETXKBMAP_CMD|g" "$XSESSION_FILE"
else
    # Desktop mode - launch full desktop
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
echo "OK .xsession file created"

# 6. Configure WineGE for a WineGE RemoteApp session
if [ "$SESSION_TYPE" = "winege-remoteapp" ]; then
    echo ""
    echo "→ Configurando WineGE RemoteApp..."

    # SESSION_COMMAND contains the path of the .exe
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    WINEGE_SCRIPT="$SCRIPT_DIR/setup-winege-app.sh"

    if [ ! -f "$WINEGE_SCRIPT" ]; then
        echo "X Error: Script setup-winege-app.sh not found in $SCRIPT_DIR"
        exit 1
    fi

    # Run WineGE setup (no need for pkexec, we are already root)
    bash "$WINEGE_SCRIPT" "$USERNAME" "$HOME_DIR" "$SESSION_COMMAND"

    if [ $? -ne 0 ]; then
        echo "X Error configuring WineGE"
        exit 1
    fi

    echo "OK WineGE RemoteApp configured successfully"
fi

echo "OK User $USERNAME created successfully!"
echo " - Keyboard layout: $XKBLAYOUT"
exit 0
