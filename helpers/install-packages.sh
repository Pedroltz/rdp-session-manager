#!/bin/bash
# Helper script to install packages with pkexec
# Uso: pkexec helpers/install-packages.sh package1 package2 package3...

set -e

# Detect distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

DISTRO=$(detect_distro)

# Check if there are packages to install
if [ $# -eq 0 ]; then
    echo "Error: No package specified"
    exit 1
fi

case "$DISTRO" in
    arch|manjaro|endeavouros|cachyos)
        # Update package cache
        echo "Updating package cache..."
        # Avoid partial upgrades: Arch requires a full sync before installing.
        /usr/bin/pacman -Syu --needed --noconfirm

        # Install packages
        echo "Installing packages: $@"
        /usr/bin/pacman -S --noconfirm "$@"
        ;;
    debian|ubuntu|linuxmint|pop)
        # Update package cache
        echo "Updating package cache..."
        /usr/bin/apt-get update

        # Install packages
        echo "Installing packages: $@"
        DEBIAN_FRONTEND=noninteractive /usr/bin/apt-get install -y "$@"
        ;;
    *)
        echo "Error: Unsupported distribution: $DISTRO"
        exit 1
        ;;
esac

echo "Installation completed successfully!"
exit 0
