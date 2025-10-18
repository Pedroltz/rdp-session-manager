#!/bin/bash
# Helper script para criar usuário RDP com pkexec
# Uso: pkexec helpers/create-rdp-user.sh USERNAME USER_UID HOME_DIR FULLNAME [DE_COMMAND]

set -e

USERNAME="$1"
USER_UID="$2"
HOME_DIR="$3"
FULLNAME="$4"
DE_COMMAND="$5"

# Validar parâmetros
if [ -z "$USERNAME" ] || [ -z "$USER_UID" ] || [ -z "$HOME_DIR" ]; then
    echo "Erro: Parâmetros insuficientes"
    echo "Uso: $0 USERNAME USER_UID HOME_DIR [FULLNAME] [DE_COMMAND]"
    exit 1
fi

echo "Criando usuário RDP: $USERNAME"

# 1. Criar grupo rdp-users se não existir
if ! getent group rdp-users > /dev/null 2>&1; then
    echo "→ Criando grupo rdp-users..."
    /usr/sbin/groupadd rdp-users
fi

# 2. Criar diretório base se não existir
if [ ! -d "/opt/rdp-users" ]; then
    echo "→ Criando diretório /opt/rdp-users..."
    /usr/bin/mkdir -p /opt/rdp-users
    /usr/bin/chmod 755 /opt/rdp-users
fi

# 3. Criar usuário
echo "→ Criando usuário $USERNAME (UID: $USER_UID)..."
if [ -n "$FULLNAME" ]; then
    /usr/sbin/useradd -u "$USER_UID" -d "$HOME_DIR" -m -g rdp-users -s /bin/bash -c "$FULLNAME" "$USERNAME"
else
    /usr/sbin/useradd -u "$USER_UID" -d "$HOME_DIR" -m -g rdp-users -s /bin/bash "$USERNAME"
fi

# 4. Ajustar permissões do home directory (751 para permitir leitura do .xsession)
echo "→ Ajustando permissões do diretório home..."
/usr/bin/chmod 751 "$HOME_DIR"

# 5. Criar arquivo .xsession se DE_COMMAND foi fornecido
if [ -n "$DE_COMMAND" ]; then
    echo "→ Criando arquivo .xsession..."
    XSESSION_FILE="$HOME_DIR/.xsession"

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

    /usr/bin/chmod 755 "$XSESSION_FILE"
    /usr/bin/chown "$USERNAME:rdp-users" "$XSESSION_FILE"
    echo "  ✓ Arquivo .xsession criado"
fi

echo "✓ Usuário $USERNAME criado com sucesso!"
exit 0
