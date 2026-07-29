#!/bin/bash
# Helper script to create .xsession file with pkexec
# Uso: pkexec helpers/create-xsession.sh USERNAME HOME_DIR DE_COMMAND

set -e

USERNAME="$1"
HOME_DIR="$2"
DE_COMMAND="$3"

# Validate parameters
if [ -z "$USERNAME" ] || [ -z "$HOME_DIR" ] || [ -z "$DE_COMMAND" ]; then
    echo "Error: Insufficient parameters"
    echo "Uso: $0 USERNAME HOME_DIR DE_COMMAND"
    exit 1
fi

XSESSION_FILE="$HOME_DIR/.xsession"

echo "Creating .xsession file for $USERNAME..."

# Detect system keyboard layout
XKBLAYOUT="us"
XKBVARIANT=""
XKBMODEL="pc105"

if [ -f /etc/default/keyboard ]; then
    source /etc/default/keyboard
    echo "Keyboard layout detected: $XKBLAYOUT (variant: $XKBVARIANT, model: $XKBMODEL)"
fi

# Build command setxkbmap
SETXKBMAP_CMD="setxkbmap -layout $XKBLAYOUT"
if [ -n "$XKBVARIANT" ]; then
    SETXKBMAP_CMD="$SETXKBMAP_CMD -variant $XKBVARIANT"
fi
if [ -n "$XKBMODEL" ]; then
    SETXKBMAP_CMD="$SETXKBMAP_CMD -model $XKBMODEL"
fi

# Create .xsession file
cat > "$XSESSION_FILE" <<EOF
#!/bin/bash
# RDP Session startup script for $USERNAME

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
exec $DE_COMMAND
EOF

# Adjust permissions
/usr/bin/chmod 755 "$XSESSION_FILE"
/usr/bin/chown "$USERNAME:rdp-users" "$XSESSION_FILE"

echo "OK .xsession file created successfully!"
echo " - Keyboard layout: $XKBLAYOUT"
exit 0
