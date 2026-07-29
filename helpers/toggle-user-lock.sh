#!/bin/bash
# Helper script to enable/disable RDP user with pkexec
# Uso: pkexec helpers/toggle-user-lock.sh USERNAME lock|unlock

set -e

USERNAME="$1"
ACTION="$2"

# Validate parameters
if [ -z "$USERNAME" ] || [ -z "$ACTION" ]; then
    echo "Error: Insufficient parameters"
    echo "Uso: $0 USERNAME lock|unlock"
    exit 1
fi

# Validate action
if [ "$ACTION" != "lock" ] && [ "$ACTION" != "unlock" ]; then
    echo "Error: Invalid action. Use 'lock' or 'unlock'"
    exit 1
fi

# Check if user exists
if ! /usr/bin/id "$USERNAME" &> /dev/null; then
    echo "Error: User $USERNAME does not exist"
    exit 1
fi

if [ "$ACTION" = "lock" ]; then
    echo "Disabling user $USERNAME..."
    /usr/sbin/usermod --lock "$USERNAME"
    echo "OK User $USERNAME disabled (account blocked)"
else
    echo "Enabling user $USERNAME..."
    /usr/sbin/usermod --unlock "$USERNAME"
    echo "OK User $USERNAME enabled (account unlocked)"
fi

exit 0
