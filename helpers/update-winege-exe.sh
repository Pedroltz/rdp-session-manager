#!/bin/bash
set -e

USERNAME="$1"
NEW_EXE_PATH="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/audit-lib.sh"
rdpsm_audit_on_exit windows.executable.update "$USERNAME"

[ -z "$USERNAME" ] || [ -z "$NEW_EXE_PATH" ] && {
    echo "Usage: $0 USERNAME NEW_EXE_PATH"
    exit 1
}

id "$USERNAME" &>/dev/null || {
    echo "Error: User does not exist: $USERNAME"
    exit 1
}

[ ! -f "$NEW_EXE_PATH" ] && {
    echo "Error: File not found: $NEW_EXE_PATH"
    exit 1
}

HOME_DIR="/opt/rdp-users/$USERNAME"
WINEGE_APP_PATH="$HOME_DIR/.winege_app_path"

[ ! -f "$WINEGE_APP_PATH" ] && {
    echo "Error: User $USERNAME is not a WineGE RemoteApp user"
    exit 1
}

echo "Updating WineGE executable for: $USERNAME"
echo "  New executable: $NEW_EXE_PATH"

# Salvar novo caminho (SEM copiar)
echo "$NEW_EXE_PATH" > "$WINEGE_APP_PATH"
chown "$USERNAME:rdp-users" "$WINEGE_APP_PATH"

echo "OK Executable updated successfully!"
echo "Executable will run from: $NEW_EXE_PATH"
exit 0
