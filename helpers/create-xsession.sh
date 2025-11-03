#!/bin/bash
# Helper script para criar arquivo .xsession com pkexec
# Uso: pkexec helpers/create-xsession.sh USERNAME HOME_DIR DE_COMMAND

set -e

USERNAME="$1"
HOME_DIR="$2"
DE_COMMAND="$3"

# Validar parâmetros
if [ -z "$USERNAME" ] || [ -z "$HOME_DIR" ] || [ -z "$DE_COMMAND" ]; then
    echo "Erro: Parâmetros insuficientes"
    echo "Uso: $0 USERNAME HOME_DIR DE_COMMAND"
    exit 1
fi

XSESSION_FILE="$HOME_DIR/.xsession"

echo "Criando arquivo .xsession para $USERNAME..."

# Criar arquivo .xsession
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

# Start desktop environment
exec $DE_COMMAND
EOF

# Ajustar permissões
/usr/bin/chmod 755 "$XSESSION_FILE"
/usr/bin/chown "$USERNAME:rdp-users" "$XSESSION_FILE"

echo "OK Arquivo .xsession criado com sucesso!"
exit 0
