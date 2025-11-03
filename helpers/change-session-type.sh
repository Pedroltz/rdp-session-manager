#!/bin/bash
# Script helper para alterar tipo de sessão RDP de usuário existente
# Uso: pkexec change-session-type.sh USERNAME SESSION_TYPE SESSION_COMMAND [APP_ARGS]

set -e

if [ "$#" -lt 3 ]; then
    echo "Uso: $0 USERNAME SESSION_TYPE SESSION_COMMAND [APP_ARGS]"
    exit 1
fi

USERNAME="$1"
SESSION_TYPE="$2"        # 'desktop' ou 'remoteapp'
SESSION_COMMAND="$3"     # DE command ou app command
APP_ARGS="$4"            # Argumentos (opcional)

# Verificar se usuário existe
if ! id "$USERNAME" &>/dev/null; then
    echo "Erro: Usuário $USERNAME não existe"
    exit 1
fi

# Obter diretório home do usuário
HOME_DIR=$(getent passwd "$USERNAME" | cut -d: -f6)

if [ ! -d "$HOME_DIR" ]; then
    echo "Erro: Diretório home $HOME_DIR não encontrado"
    exit 1
fi

echo "Alterando tipo de sessão de $USERNAME para: $SESSION_TYPE"

# Verificar se usuário tem processos ativos
ACTIVE_PIDS=$(pgrep -u "$USERNAME" 2>/dev/null || true)
if [ -n "$ACTIVE_PIDS" ]; then
    echo "Encerrando sessões de $USERNAME..."
    /usr/bin/pkill -TERM -u "$USERNAME" 2>/dev/null || true
    sleep 2
    # Forçar encerramento se ainda houver processos
    /usr/bin/pkill -KILL -u "$USERNAME" 2>/dev/null || true
fi

# Recriar arquivo .xsession
XSESSION_FILE="$HOME_DIR/.xsession"
echo "→ Recriando arquivo .xsession..."

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

# Configure openbox to maximize windows by default
mkdir -p $HOME_DIR/.config/openbox
cat > $HOME_DIR/.config/openbox/rc.xml <<'OPENBOXEOF'
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <applications>
    <application class="*">
      <maximized>yes</maximized>
      <decor>no</decor>
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

# Start desktop environment
exec $SESSION_COMMAND
EOF
fi

/usr/bin/chmod 755 "$XSESSION_FILE"
/usr/bin/chown "$USERNAME:rdp-users" "$XSESSION_FILE"

echo "OK Tipo de sessão alterado com sucesso para $SESSION_TYPE"
exit 0
