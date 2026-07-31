#!/bin/bash
# Helper script para deletar usuário RDP com pkexec
# Uso: pkexec helpers/delete-rdp-user.sh USERNAME [--remove-home] [--kill-processes]

set -e

USERNAME="$1"
REMOVE_HOME=false
KILL_PROCESSES=false

# Validar parâmetros
if [ -z "$USERNAME" ]; then
    echo "Error: Username was not specified"
    echo "Usage: $0 USERNAME [--remove-home] [--kill-processes]"
    exit 1
fi

# Processar flags
shift
while [ $# -gt 0 ]; do
    case "$1" in
        --remove-home)
            REMOVE_HOME=true
            ;;
        --kill-processes)
            KILL_PROCESSES=true
            ;;
    esac
    shift
done

echo "Deleting RDP user: $USERNAME"

# 1. Matar processos se solicitado
if [ "$KILL_PROCESSES" = true ]; then
echo "→ Checking active processes..."

    # Tentar obter processos do usuário
    if /usr/bin/pgrep -u "$USERNAME" > /dev/null 2>&1; then
        PROCESS_COUNT=$(/usr/bin/pgrep -u "$USERNAME" | wc -l)
        echo "  Found $PROCESS_COUNT active processes"

        echo "→ Terminating processes (SIGTERM)..."
        /usr/bin/pkill -15 -u "$USERNAME" 2>/dev/null || true

        # Aguardar um pouco
        sleep 1

        # Verificar se ainda há processos
        if /usr/bin/pgrep -u "$USERNAME" > /dev/null 2>&1; then
            REMAINING=$(/usr/bin/pgrep -u "$USERNAME" | wc -l)
    echo "  $REMAINING processes remain; forcing termination (SIGKILL)..."
            /usr/bin/pkill -9 -u "$USERNAME" 2>/dev/null || true
            sleep 0.5
        fi

        echo "  OK Processes terminated"
    else
    echo "  No active processes found"
    fi
fi

# 2. Deletar usuário
echo "→ Deleting user $USERNAME..."

if [ "$REMOVE_HOME" = true ]; then
    /usr/sbin/userdel -r "$USERNAME"
    echo "  OK User and home directory removed"
else
    /usr/sbin/userdel "$USERNAME"
    echo "  OK User removed (home directory kept)"
fi

echo "OK User $USERNAME deleted successfully!"
exit 0
