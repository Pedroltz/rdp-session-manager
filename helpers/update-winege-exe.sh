#!/bin/bash
set -e

USERNAME="$1"
NEW_EXE_PATH="$2"

[ -z "$USERNAME" ] || [ -z "$NEW_EXE_PATH" ] && {
    echo "Uso: $0 USERNAME NEW_EXE_PATH"
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
    echo "Error: User $USERNAME is not WineGE RemoteApp"
    exit 1
}

echo "Updating WineGE executable to: $USERNAME"
echo "New executable: $NEW_EXE_PATH"

# Save new path (WITHOUT copying)
echo "$NEW_EXE_PATH" > "$WINEGE_APP_PATH"
chown "$USERNAME:rdp-users" "$WINEGE_APP_PATH"

echo "OK Executable updated successfully!"
echo "Executable will be run from: $NEW_EXE_PATH"
exit 0
