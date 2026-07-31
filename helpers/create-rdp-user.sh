#!/bin/bash
# Helper script para criar usuário RDP com pkexec
# Uso: pkexec helpers/create-rdp-user.sh USERNAME USER_UID HOME_DIR FULLNAME SESSION_TYPE SESSION_COMMAND [APP_ARGS]

set -e

step() {
    printf '[%(%Y-%m-%dT%H:%M:%S%z)T] %s\n' -1 "$*"
}

USERNAME="$1"
USER_UID="$2"
HOME_DIR="$3"
FULLNAME="$4"
SESSION_TYPE="$5"        # 'desktop', 'remoteapp', ou 'winege-remoteapp'
SESSION_COMMAND="$6"     # DE command (ex: startxfce4), app command (ex: firefox), ou .exe path para WineGE
APP_ARGS="$7"            # Argumentos do app (apenas para remoteapp)

# Validar parâmetros
if [ -z "$USERNAME" ] || [ -z "$USER_UID" ] || [ -z "$HOME_DIR" ]; then
    echo "Error: Not enough arguments"
    echo "Usage: $0 USERNAME USER_UID HOME_DIR [FULLNAME] [SESSION_TYPE] [SESSION_COMMAND] [APP_ARGS]"
    exit 1
fi

# Defaults
SESSION_TYPE="${SESSION_TYPE:-desktop}"
SESSION_COMMAND="${SESSION_COMMAND:-startxfce4}"

echo "Creating RDP user: $USERNAME"

# Detectar layout de teclado do sistema
XKBLAYOUT="us"
XKBVARIANT=""
XKBMODEL="pc105"

if [ -f /etc/default/keyboard ]; then
    source /etc/default/keyboard
    echo "→ Keyboard layout detected: $XKBLAYOUT"
fi

# Construir comando setxkbmap
SETXKBMAP_CMD="setxkbmap -layout $XKBLAYOUT"
if [ -n "$XKBVARIANT" ]; then
    SETXKBMAP_CMD="$SETXKBMAP_CMD -variant $XKBVARIANT"
fi
if [ -n "$XKBMODEL" ]; then
    SETXKBMAP_CMD="$SETXKBMAP_CMD -model $XKBMODEL"
fi

# 1. Criar grupo rdp-users se não existir
if ! getent group rdp-users > /dev/null 2>&1; then
    echo "→ Creating rdp-users group..."
    /usr/sbin/groupadd rdp-users
fi

# 2. Criar diretório base se não existir
if [ ! -d "/opt/rdp-users" ]; then
    echo "→ Creating /opt/rdp-users directory..."
    /usr/bin/mkdir -p /opt/rdp-users
    /usr/bin/chmod 755 /opt/rdp-users
fi

# 3. Criar usuário
step "→ Creating user $USERNAME (UID: $USER_UID)..."
if [ -n "$FULLNAME" ]; then
    /usr/sbin/useradd -u "$USER_UID" -d "$HOME_DIR" -m -g rdp-users -s /bin/bash -c "$FULLNAME" "$USERNAME"
else
    /usr/sbin/useradd -u "$USER_UID" -d "$HOME_DIR" -m -g rdp-users -s /bin/bash "$USERNAME"
fi
step "  OK System user created"

# 4. Ajustar permissões do home directory (751 para permitir leitura do .xsession)
step "→ Adjusting home directory permissions..."
/usr/bin/chmod 751 "$HOME_DIR"
step "  OK Home directory permissions adjusted"

# 5. Criar arquivo .xsession
step "→ Creating .xsession file (mode: $SESSION_TYPE)..."
XSESSION_FILE="$HOME_DIR/.xsession"

if [ "$SESSION_TYPE" = "remoteapp" ]; then
    # RemoteApp mode - lançar aplicativo individual
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
    # WineGE RemoteApp mode - lançar aplicativo Windows via WineGE
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
    # Desktop mode - lançar desktop completo
    cat > "$XSESSION_FILE" <<EOF
#!/bin/bash
# RDP Session startup script for $USERNAME
# Mode: Desktop

# Set environment variables
export HOME=$HOME_DIR
export USER=$USERNAME
export LOGNAME=$USERNAME

# Configure desktop environment variables
case "$SESSION_COMMAND" in
    *gnome*)
        export XDG_CURRENT_DESKTOP=GNOME-Flashback:GNOME
        export XDG_SESSION_DESKTOP=gnome-flashback-metacity
        export XDG_SESSION_TYPE=x11
        export DESKTOP_SESSION=gnome-flashback-metacity
        ;;
    *plasma*|*kde*)
        export XDG_CURRENT_DESKTOP=KDE
        export XDG_SESSION_DESKTOP=KDE
        export XDG_SESSION_TYPE=x11
        export DESKTOP_SESSION=plasma
        ;;
    *xfce*)
        export XDG_CURRENT_DESKTOP=XFCE
        export XDG_SESSION_DESKTOP=xfce
        export XDG_SESSION_TYPE=x11
        export DESKTOP_SESSION=xfce
        ;;
    *)
        export XDG_SESSION_TYPE=x11
        ;;
esac

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
echo "  OK .xsession file created"

# 6. Se for WineGE RemoteApp, configurar WineGE
if [ "$SESSION_TYPE" = "winege-remoteapp" ]; then
    echo ""
    echo "→ Configuring WineGE RemoteApp..."

    # SESSION_COMMAND contém o caminho do .exe
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    WINEGE_SCRIPT="$SCRIPT_DIR/setup-winege-app.sh"

    if [ ! -f "$WINEGE_SCRIPT" ]; then
        echo "  X Error: setup-winege-app.sh script not found in $SCRIPT_DIR"
        exit 1
    fi

    # Executar setup do WineGE (não precisa de pkexec, já estamos como root)
    bash "$WINEGE_SCRIPT" "$USERNAME" "$HOME_DIR" "$SESSION_COMMAND"

    if [ $? -ne 0 ]; then
        echo "  X Error configuring WineGE"
        exit 1
    fi

    echo "  OK WineGE RemoteApp configured successfully"
fi

echo "OK User $USERNAME created successfully!"
echo "  - Keyboard layout: $XKBLAYOUT"
exit 0
