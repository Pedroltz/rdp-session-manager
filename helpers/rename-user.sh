#!/bin/bash
# Script helper para renomear usuário RDP
# Uso: pkexec rename-user.sh OLD_USERNAME NEW_USERNAME

set -e

if [ "$#" -ne 2 ]; then
    echo "Uso: $0 OLD_USERNAME NEW_USERNAME"
    exit 1
fi

OLD_USERNAME="$1"
NEW_USERNAME="$2"

# Verificar se usuário antigo existe
if ! id "$OLD_USERNAME" &>/dev/null; then
    echo "Erro: Usuário $OLD_USERNAME não existe"
    exit 1
fi

# Verificar se novo username já existe
if id "$NEW_USERNAME" &>/dev/null; then
    echo "Erro: Usuário $NEW_USERNAME já existe"
    exit 1
fi

echo "Renomeando usuário: $OLD_USERNAME -> $NEW_USERNAME..."

# Verificar se usuário tem processos ativos
ACTIVE_PIDS=$(pgrep -u "$OLD_USERNAME" 2>/dev/null || true)
if [ -n "$ACTIVE_PIDS" ]; then
    echo "Encerrando sessões de $OLD_USERNAME..."
    /usr/bin/pkill -TERM -u "$OLD_USERNAME" 2>/dev/null || true
    sleep 2
    # Forçar encerramento se ainda houver processos
    /usr/bin/pkill -KILL -u "$OLD_USERNAME" 2>/dev/null || true
fi

# Obter diretório home atual
OLD_HOME=$(getent passwd "$OLD_USERNAME" | cut -d: -f6)
NEW_HOME=$(dirname "$OLD_HOME")/"$NEW_USERNAME"

# Renomear usuário e mover diretório home
echo "Executando usermod..."
/usr/sbin/usermod -l "$NEW_USERNAME" -d "$NEW_HOME" -m "$OLD_USERNAME"

# Renomear grupo primário se existir
if getent group "$OLD_USERNAME" &>/dev/null; then
    echo "Renomeando grupo primário..."
    /usr/sbin/groupmod -n "$NEW_USERNAME" "$OLD_USERNAME" 2>/dev/null || true
fi

echo "OK Usuário renomeado com sucesso: $OLD_USERNAME -> $NEW_USERNAME"
exit 0
