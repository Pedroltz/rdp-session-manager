#!/bin/bash
# Helper script to delete RDP user with pkexec
# Uso: pkexec helpers/delete-rdp-user.sh USERNAME [--remove-home] [--kill-processes]

set -e

USERNAME="$1"
REMOVE_HOME=false
KILL_PROCESSES=false

# Validate parameters
if [ -z "$USERNAME" ]; then
    echo "Error: Username not specified"
    echo "Uso: $0 USERNAME [--remove-home] [--kill-processes]"
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

# 1. Kill processes when requested
if [ "$KILL_PROCESSES" = true ]; then
    echo "→ Checking active processes..."

    # Try to get user processes
    if /usr/bin/pgrep -u "$USERNAME" > /dev/null 2>&1; then
        PROCESS_COUNT=$(/usr/bin/pgrep -u "$USERNAME" | wc -l)
        echo "Found $PROCESS_COUNT active processes"

        echo "→ Terminating processes (SIGTERM)..."
        /usr/bin/pkill -15 -u "$USERNAME" 2>/dev/null || true

        # Wait briefly
        sleep 1

        # Check if there are still processes
        if /usr/bin/pgrep -u "$USERNAME" > /dev/null 2>&1; then
            REMAINING=$(/usr/bin/pgrep -u "$USERNAME" | wc -l)
            echo "There are still $REMAINING processes, forcing termination (SIGKILL)..."
            /usr/bin/pkill -9 -u "$USERNAME" 2>/dev/null || true
            sleep 0.5
        fi

        echo "OK Processes finished"
    else
        echo "No active processes found"
    fi
fi

# 2. Delete user
echo "→ Deleting user $USERNAME..."

if [ "$REMOVE_HOME" = true ]; then
    /usr/sbin/userdel -r "$USERNAME"
    echo "OK User and home directory removed"
else
    /usr/sbin/userdel "$USERNAME"
    echo "OK User removed (home directory kept)"
fi

echo "OK User $USERNAME deleted successfully!"
exit 0
