#!/bin/bash
# Helper script to rename RDP user
# Uso: pkexec rename-user.sh OLD_USERNAME NEW_USERNAME

set -e

if [ "$#" -ne 2 ]; then
    echo "Uso: $0 OLD_USERNAME NEW_USERNAME"
    exit 1
fi

OLD_USERNAME="$1"
NEW_USERNAME="$2"

# Check if old user exists
if ! id "$OLD_USERNAME" &>/dev/null; then
    echo "Error: User $OLD_USERNAME does not exist"
    exit 1
fi

# Check if new username already exists
if id "$NEW_USERNAME" &>/dev/null; then
    echo "Error: User $NEW_USERNAME already exists"
    exit 1
fi

echo "Renaming user: $OLD_USERNAME -> $NEW_USERNAME..."

# Check if user has active processes
ACTIVE_PIDS=$(pgrep -u "$OLD_USERNAME" 2>/dev/null || true)
if [ -n "$ACTIVE_PIDS" ]; then
    echo "Terminating $OLD_USERNAME sessions..."
    /usr/bin/pkill -TERM -u "$OLD_USERNAME" 2>/dev/null || true
    sleep 2
    # Force shutdown if there are still processes
    /usr/bin/pkill -KILL -u "$OLD_USERNAME" 2>/dev/null || true
fi

# Get current home directory
OLD_HOME=$(getent passwd "$OLD_USERNAME" | cut -d: -f6)
NEW_HOME=$(dirname "$OLD_HOME")/"$NEW_USERNAME"

# Rename user and move home directory
echo "Running usermod..."
/usr/sbin/usermod -l "$NEW_USERNAME" -d "$NEW_HOME" -m "$OLD_USERNAME"

# Rename primary group if exists
if getent group "$OLD_USERNAME" &>/dev/null; then
    echo "Renaming primary group..."
    /usr/sbin/groupmod -n "$NEW_USERNAME" "$OLD_USERNAME" 2>/dev/null || true
fi

echo "OK User successfully renamed: $OLD_USERNAME -> $NEW_USERNAME"
exit 0
