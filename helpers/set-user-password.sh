#!/bin/bash
# Helper script to set user password with pkexec
# Uso: echo "username:password" | pkexec helpers/set-user-password.sh

set -e

# Read credentials from stdin
read -r CREDENTIALS

if [ -z "$CREDENTIALS" ]; then
    echo "Error: Credentials not provided via stdin"
    exit 1
fi

# Set password using chpasswd
echo "$CREDENTIALS" | /usr/sbin/chpasswd

echo "OK Password set successfully!"
exit 0
