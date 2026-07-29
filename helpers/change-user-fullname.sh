#!/bin/bash
# Helper script to change RDP user's full name (GECOS)
# Uso: pkexec change-user-fullname.sh USERNAME "Full Name"

set -e

if [ "$#" -ne 2 ]; then
    echo "Uso: $0 USERNAME \"Full Name\""
    exit 1
fi

USERNAME="$1"
FULLNAME="$2"

# Check if user exists
if ! id "$USERNAME" &>/dev/null; then
    echo "Error: User $USERNAME does not exist"
    exit 1
fi

echo "Changing full name of $USERNAME to: $FULLNAME"

# Change GECOS (full name)
/usr/sbin/usermod -c "$FULLNAME" "$USERNAME"

echo "OK Full name changed successfully"
exit 0
