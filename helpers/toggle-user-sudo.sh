#!/bin/bash
# Helper script to grant/revoke sudo privileges for RDP user with pkexec
# Uso: pkexec helpers/toggle-user-sudo.sh USERNAME grant|revoke

set -e

USERNAME="$1"
ACTION="$2"

# Validate parameters
if [ -z "$USERNAME" ] || [ -z "$ACTION" ]; then
    echo "Error: Insufficient parameters"
    echo "Uso: $0 USERNAME grant|revoke"
    exit 1
fi

# Validate action
if [ "$ACTION" != "grant" ] && [ "$ACTION" != "revoke" ]; then
    echo "Error: Invalid action. Use 'grant' or 'revoke'"
    exit 1
fi

# Check if user exists
if ! /usr/bin/id "$USERNAME" &> /dev/null; then
    echo "Error: User $USERNAME does not exist"
    exit 1
fi

if [ "$ACTION" = "grant" ]; then
    echo "Granting superuser privileges to $USERNAME..."

    # Add user to sudo group
    /usr/sbin/usermod -aG sudo "$USERNAME"

    echo "OK Superuser privileges granted to $USERNAME"
    echo "User can now run commands with sudo"
else
    echo "Revoking superuser privileges from $USERNAME..."

    # Remove user from sudo group using gpasswd (more reliable)
    if /usr/bin/gpasswd -d "$USERNAME" sudo 2>/dev/null; then
        echo "OK Superuser privileges revoked from $USERNAME"
        echo "User can no longer execute commands with sudo"
    else
        # Fallback to deluser if gpasswd fails
        if /usr/sbin/deluser "$USERNAME" sudo 2>/dev/null; then
            echo "OK Superuser privileges revoked from $USERNAME"
            echo "User can no longer execute commands with sudo"
        else
            echo "! Warning: Command completed but check user groups"
        fi
    fi
fi

exit 0
