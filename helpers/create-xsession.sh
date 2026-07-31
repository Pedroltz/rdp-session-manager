#!/bin/bash
# Helper script para criar arquivo .xsession com pkexec
# Uso: pkexec helpers/create-xsession.sh USERNAME HOME_DIR DE_COMMAND

set -e

USERNAME="$1"
HOME_DIR="$2"
DE_COMMAND="$3"

# Validar parâmetros
if [ -z "$USERNAME" ] || [ -z "$HOME_DIR" ] || [ -z "$DE_COMMAND" ]; then
    echo "Error: Not enough arguments"
    echo "Usage: $0 USERNAME HOME_DIR DE_COMMAND"
    exit 1
fi

XSESSION_FILE="$HOME_DIR/.xsession"

echo "Creating .xsession file for $USERNAME..."

# Detectar layout de teclado do sistema
XKBLAYOUT="us"
XKBVARIANT=""
XKBMODEL="pc105"

if [ -f /etc/default/keyboard ]; then
    source /etc/default/keyboard
echo "Keyboard layout detected: $XKBLAYOUT (variant: $XKBVARIANT, model: $XKBMODEL)"
fi

# Construir comando setxkbmap
SETXKBMAP_CMD="setxkbmap -layout $XKBLAYOUT"
if [ -n "$XKBVARIANT" ]; then
    SETXKBMAP_CMD="$SETXKBMAP_CMD -variant $XKBVARIANT"
fi
if [ -n "$XKBMODEL" ]; then
    SETXKBMAP_CMD="$SETXKBMAP_CMD -model $XKBMODEL"
fi

# Criar arquivo .xsession
cat > "$XSESSION_FILE" <<EOF
#!/bin/bash
# RDP Session startup script for $USERNAME

# Set environment variables
export HOME=$HOME_DIR
export USER=$USERNAME
export LOGNAME=$USERNAME

# Configure desktop environment variables
case "$DE_COMMAND" in
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
exec $DE_COMMAND
EOF

# Ajustar permissões
/usr/bin/chmod 755 "$XSESSION_FILE"
/usr/bin/chown "$USERNAME:rdp-users" "$XSESSION_FILE"

echo "OK .xsession file created successfully!"
echo "  - Keyboard layout: $XKBLAYOUT"
exit 0
