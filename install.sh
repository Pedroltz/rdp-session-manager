#!/bin/bash
###############################################################################
# RDP Session Manager - Installation Script
#
# Supported distributions: Debian 11+, Ubuntu 20.04+, Linux Mint, Pop!_OS
#                         Arch Linux, Manjaro, EndeavourOS, CachyOS
#
# This script installs all required dependencies for RDP Session Manager
# including: xrdp, WineGE support, and optionally Oracle Instant Client
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters for summary
INSTALLED_COUNT=0
SKIPPED_COUNT=0
FAILED_COUNT=0
FAILED_PACKAGES=""

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo ""
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}=========================================${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${YELLOW}→ $1${NC}"
}

print_success() {
    echo -e "  ${GREEN}✓${NC} $1"
    INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
}

print_skip() {
    echo -e "  ${BLUE}○${NC} $1 (already installed)"
    SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
}

print_warning() {
    echo -e "  ${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "  ${RED}✗${NC} $1"
    FAILED_COUNT=$((FAILED_COUNT + 1))
    FAILED_PACKAGES="$FAILED_PACKAGES\n    - $1"
}

print_info() {
    echo -e "  ${BLUE}ℹ${NC} $1"
}

# Detect Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

# Check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check if package is installed (Debian/Ubuntu)
is_pkg_installed_deb() {
    dpkg -l "$1" 2>/dev/null | grep -q "^ii"
}

# Check if package is installed (Arch)
is_pkg_installed_arch() {
    pacman -Q "$1" &>/dev/null
}

###############################################################################
# Main Installation
###############################################################################

DISTRO=$(detect_distro)

print_header "Installing RDP Session Manager"

echo "Detected distribution: $DISTRO"
echo "Script version: 0.3.0"
echo ""

# Verify supported distro
case "$DISTRO" in
    arch|manjaro|endeavouros|cachyos)
        PKG_FILE="release/rdp-session-manager-0.3.0-1-any.pkg.tar.zst"
        DISTRO_TYPE="arch"
        ;;
    debian|ubuntu|linuxmint|pop)
        PKG_FILE="release/rdp-session-manager_0.3.0_all.deb"
        DISTRO_TYPE="debian"
        ;;
    *)
        echo -e "${RED}ERROR: Unsupported distribution: $DISTRO${NC}"
        echo "Supported: Arch Linux (CachyOS, Manjaro, EndeavourOS), Debian, Ubuntu, Linux Mint, Pop!_OS"
        exit 1
        ;;
esac

# Check if package exists
if [ ! -f "$PKG_FILE" ]; then
    echo -e "${RED}ERROR: Package not found: $PKG_FILE${NC}"
    echo "Run ./build_release.sh first"
    exit 1
fi

###############################################################################
# SECTION 1: Core System Dependencies (Required)
###############################################################################

print_header "1/5 - Core System Dependencies"
echo "These packages are required for the application to run."
echo ""

case "$DISTRO_TYPE" in
    arch)
        print_section "Updating package cache..."
        sudo pacman -Sy

        print_section "Installing Python and GTK4 dependencies..."

        CORE_PACKAGES=(
            python
            python-gobject
            python-cairo
            python-psutil
            gtk4
            libadwaita
            polkit
        )

        for pkg in "${CORE_PACKAGES[@]}"; do
            if is_pkg_installed_arch "$pkg"; then
                print_skip "$pkg"
            else
                if sudo pacman -S --noconfirm "$pkg" &>/dev/null; then
                    print_success "$pkg installed"
                else
                    print_error "$pkg"
                fi
            fi
        done
        ;;

    debian)
        print_section "Updating package cache..."
        sudo apt-get update

        print_section "Installing Python and GTK4 dependencies..."

        CORE_PACKAGES=(
            python3
            python3-gi
            python3-gi-cairo
            python3-psutil
            gir1.2-gtk-4.0
            gir1.2-adw-1
            libadwaita-1-0
            polkitd
        )

        for pkg in "${CORE_PACKAGES[@]}"; do
            if is_pkg_installed_deb "$pkg"; then
                print_skip "$pkg"
            else
                if sudo apt-get install -y "$pkg" &>/dev/null; then
                    print_success "$pkg installed"
                else
                    print_error "$pkg"
                fi
            fi
        done
        ;;
esac

###############################################################################
# SECTION 2: RDP Server Dependencies (Required for xrdp)
###############################################################################

print_header "2/5 - RDP Server Dependencies"
echo "These packages enable RDP connections to this machine."
echo ""

case "$DISTRO_TYPE" in
    arch)
        print_section "Installing xrdp and X11 packages..."

        RDP_PACKAGES=(
            xrdp
            xorg-server
            xorg-xinit
            xorg-xrandr
            xorg-xauth
            openbox
            dbus
            zenity
        )

        for pkg in "${RDP_PACKAGES[@]}"; do
            if is_pkg_installed_arch "$pkg"; then
                print_skip "$pkg"
            else
                if sudo pacman -S --noconfirm "$pkg" &>/dev/null; then
                    print_success "$pkg installed"
                else
                    print_error "$pkg"
                fi
            fi
        done
        ;;

    debian)
        print_section "Installing xrdp and X11 packages..."

        RDP_PACKAGES=(
            xrdp
            xorgxrdp
            xorg
            x11-xserver-utils
            x11-utils
            xauth
            openbox
            dbus-x11
            zenity
        )

        for pkg in "${RDP_PACKAGES[@]}"; do
            if is_pkg_installed_deb "$pkg"; then
                print_skip "$pkg"
            else
                if sudo apt-get install -y "$pkg" &>/dev/null; then
                    print_success "$pkg installed"
                else
                    print_error "$pkg"
                fi
            fi
        done
        ;;
esac

# Enable and start xrdp service
print_section "Configuring xrdp service..."
if systemctl is-enabled xrdp &>/dev/null; then
    print_skip "xrdp service already enabled"
else
    if sudo systemctl enable xrdp &>/dev/null; then
        print_success "xrdp service enabled"
    else
        print_warning "Could not enable xrdp service"
    fi
fi

if systemctl is-active xrdp &>/dev/null; then
    print_skip "xrdp service already running"
else
    if sudo systemctl start xrdp &>/dev/null; then
        print_success "xrdp service started"
    else
        print_warning "Could not start xrdp service (may need reboot)"
    fi
fi

###############################################################################
# SECTION 3: Wine Dependencies (Optional - for WineGE RemoteApp)
###############################################################################

print_header "3/5 - Wine Dependencies (WineGE RemoteApp)"
echo "These packages enable running Windows applications via WineGE."
echo "This is optional but required for WineGE RemoteApp sessions."
echo ""

case "$DISTRO_TYPE" in
    arch)
        # Enable multilib repository
        print_section "Checking multilib repository..."
        if grep -q "^\[multilib\]" /etc/pacman.conf; then
            print_skip "multilib repository"
        else
            print_info "Enabling multilib repository..."
            echo -e "\n[multilib]\nInclude = /etc/pacman.d/mirrorlist" | sudo tee -a /etc/pacman.conf > /dev/null
            sudo pacman -Sy
            print_success "multilib repository enabled"
        fi

        print_section "Installing Wine and dependencies..."

        WINE_PACKAGES=(
            wine
            wine-mono
            wine-gecko
            winetricks
            lib32-gnutls
            lib32-libxinerama
            lib32-libpulse
            lib32-alsa-lib
            lib32-mesa
            lib32-vulkan-icd-loader
            cabextract
            p7zip
            unzip
            curl
            wget
            tar
        )

        for pkg in "${WINE_PACKAGES[@]}"; do
            if is_pkg_installed_arch "$pkg"; then
                print_skip "$pkg"
            else
                if sudo pacman -S --noconfirm "$pkg" &>/dev/null; then
                    print_success "$pkg installed"
                else
                    print_warning "$pkg not installed (WineGE may still work)"
                fi
            fi
        done
        ;;

    debian)
        # Enable 32-bit architecture
        print_section "Enabling 32-bit architecture..."
        if dpkg --print-foreign-architectures | grep -q i386; then
            print_skip "i386 architecture"
        else
            sudo dpkg --add-architecture i386
            sudo apt-get update
            print_success "i386 architecture enabled"
        fi

        print_section "Installing Wine and dependencies..."

        # Wine core packages
        WINE_CORE=(
            wine
            wine64
            wine32
        )

        for pkg in "${WINE_CORE[@]}"; do
            if is_pkg_installed_deb "$pkg"; then
                print_skip "$pkg"
            else
                if sudo apt-get install -y "$pkg" &>/dev/null; then
                    print_success "$pkg installed"
                else
                    print_warning "$pkg not installed"
                fi
            fi
        done

        # Wine support libraries
        print_section "Installing Wine support libraries..."

        WINE_LIBS=(
            cabextract
            p7zip-full
            unzip
            curl
            wget
            tar
            libfreetype6:i386
            libfontconfig1:i386
            libxrender1:i386
            libxinerama1:i386
            libxxf86vm1:i386
            libxcomposite1:i386
            libxrandr2:i386
            libxi6:i386
            libxcursor1:i386
            libvulkan1:i386
            libgl1:i386
            libasound2:i386
            libpulse0:i386
            libgnutls30:i386
        )

        for pkg in "${WINE_LIBS[@]}"; do
            if is_pkg_installed_deb "$pkg"; then
                print_skip "$pkg"
            else
                if sudo apt-get install -y "$pkg" &>/dev/null; then
                    print_success "$pkg installed"
                else
                    # Don't count 32-bit libs as errors, just warnings
                    print_warning "$pkg not installed (optional)"
                fi
            fi
        done

        # Install winetricks from GitHub (not in Debian repos)
        print_section "Installing winetricks..."
        if command_exists winetricks; then
            WINETRICKS_VERSION=$(winetricks --version 2>/dev/null | head -1 || echo "installed")
            print_skip "winetricks ($WINETRICKS_VERSION)"
        else
            print_info "Downloading winetricks from GitHub..."
            if wget -q -O /tmp/winetricks https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks; then
                chmod +x /tmp/winetricks
                sudo mv /tmp/winetricks /usr/local/bin/winetricks
                print_success "winetricks installed from GitHub"
            else
                print_error "winetricks (download failed)"
            fi
        fi
        ;;
esac

###############################################################################
# SECTION 4: Oracle Instant Client (Optional - for database connectivity)
###############################################################################

print_header "4/5 - Oracle Instant Client (Optional)"
echo "Oracle Instant Client enables connectivity to Oracle databases."
echo "This is optional and requires manual download due to Oracle licensing."
echo ""

ORACLE_DIR="/opt/oracle"
ORACLE_CLIENT_DIR="$ORACLE_DIR/instantclient_21_15"

# Install Oracle dependencies
case "$DISTRO_TYPE" in
    arch)
        print_section "Installing Oracle dependencies..."

        ORACLE_DEPS=(libaio unixodbc wget)

        for pkg in "${ORACLE_DEPS[@]}"; do
            if is_pkg_installed_arch "$pkg"; then
                print_skip "$pkg"
            else
                if sudo pacman -S --noconfirm "$pkg" &>/dev/null; then
                    print_success "$pkg installed"
                else
                    print_warning "$pkg not installed"
                fi
            fi
        done

        if [ -d "$ORACLE_CLIENT_DIR" ]; then
            print_skip "Oracle Instant Client already installed"
        else
            print_info "Oracle Instant Client not found"
            print_info "For Arch Linux, install from AUR:"
            echo "      yay -S oracle-instantclient-basic oracle-instantclient-sqlplus"
        fi
        ;;

    debian)
        print_section "Installing Oracle dependencies..."

        ORACLE_DEPS=(libaio1 libaio-dev unixodbc unixodbc-dev alien wget)

        for pkg in "${ORACLE_DEPS[@]}"; do
            if is_pkg_installed_deb "$pkg"; then
                print_skip "$pkg"
            else
                if sudo apt-get install -y "$pkg" &>/dev/null; then
                    print_success "$pkg installed"
                else
                    print_warning "$pkg not installed"
                fi
            fi
        done

        # Check if Oracle is already installed
        if [ -d "$ORACLE_CLIENT_DIR" ]; then
            print_skip "Oracle Instant Client already installed"
        else
            # Check for Oracle files in /tmp
            print_section "Checking for Oracle Instant Client files..."

            BASIC_ZIP=$(find /tmp -maxdepth 1 -name "instantclient-basic-linux*.zip" 2>/dev/null | head -1)
            SQLPLUS_ZIP=$(find /tmp -maxdepth 1 -name "instantclient-sqlplus-linux*.zip" 2>/dev/null | head -1)
            BASIC_RPM=$(find /tmp -maxdepth 1 -name "oracle-instantclient*-basic*.rpm" 2>/dev/null | head -1)
            SQLPLUS_RPM=$(find /tmp -maxdepth 1 -name "oracle-instantclient*-sqlplus*.rpm" 2>/dev/null | head -1)

            if [ -n "$BASIC_ZIP" ] && [ -n "$SQLPLUS_ZIP" ]; then
                print_info "Found Oracle ZIP files, installing..."
                sudo mkdir -p "$ORACLE_DIR"
                sudo unzip -o "$BASIC_ZIP" -d "$ORACLE_DIR"
                sudo unzip -o "$SQLPLUS_ZIP" -d "$ORACLE_DIR"

                # Rename to standard directory name
                EXTRACTED=$(find "$ORACLE_DIR" -maxdepth 1 -type d -name "instantclient*" ! -name "instantclient_21_15" | head -1)
                if [ -n "$EXTRACTED" ]; then
                    sudo mv "$EXTRACTED" "$ORACLE_CLIENT_DIR" 2>/dev/null || true
                fi

                print_success "Oracle Instant Client installed from ZIP"

            elif [ -n "$BASIC_RPM" ] && [ -n "$SQLPLUS_RPM" ]; then
                print_info "Found Oracle RPM files, converting to DEB..."
                cd /tmp
                sudo alien -i "$BASIC_RPM"
                sudo alien -i "$SQLPLUS_RPM"

                # Create symlink
                sudo mkdir -p "$ORACLE_DIR"
                INSTALLED_DIR=$(find /usr/lib/oracle -maxdepth 2 -type d -name "client64" 2>/dev/null | head -1)
                if [ -n "$INSTALLED_DIR" ]; then
                    sudo ln -sf "$INSTALLED_DIR" "$ORACLE_CLIENT_DIR"
                fi

                print_success "Oracle Instant Client installed from RPM"
            else
                print_info "Oracle Instant Client not found"
                echo ""
                echo "      To install Oracle Instant Client later:"
                echo "      1. Download from: https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html"
                echo "      2. Place ZIP or RPM files in /tmp/"
                echo "         - instantclient-basic-linux.x64-21.15.0.0.0dbru.zip"
                echo "         - instantclient-sqlplus-linux.x64-21.15.0.0.0dbru.zip"
                echo "      3. Run this installer again"
                echo ""
            fi
        fi
        ;;
esac

# Configure Oracle environment if installed
if [ -d "$ORACLE_CLIENT_DIR" ]; then
    print_section "Configuring Oracle environment..."

    if [ -f /etc/profile.d/oracle.sh ]; then
        print_skip "Oracle environment already configured"
    else
        cat << 'ORACLE_ENV' | sudo tee /etc/profile.d/oracle.sh > /dev/null
export ORACLE_HOME=/opt/oracle/instantclient_21_15
export LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
export PATH=$ORACLE_HOME:$PATH
export TNS_ADMIN=$ORACLE_HOME/network/admin
ORACLE_ENV
        print_success "Oracle environment configured (/etc/profile.d/oracle.sh)"
    fi

    # Create tnsnames.ora directory
    if [ ! -d "$ORACLE_CLIENT_DIR/network/admin" ]; then
        sudo mkdir -p "$ORACLE_CLIENT_DIR/network/admin"
    fi

    # Create sample tnsnames.ora if not exists
    if [ ! -f "$ORACLE_CLIENT_DIR/network/admin/tnsnames.ora" ]; then
        cat << 'TNSNAMES' | sudo tee "$ORACLE_CLIENT_DIR/network/admin/tnsnames.ora" > /dev/null
# Oracle TNS Names Configuration
# Add your database connections below:
#
# MYDB =
#   (DESCRIPTION =
#     (ADDRESS = (PROTOCOL = TCP)(HOST = hostname)(PORT = 1521))
#     (CONNECT_DATA =
#       (SERVER = DEDICATED)
#       (SERVICE_NAME = service_name)
#     )
#   )
TNSNAMES
        print_success "Sample tnsnames.ora created"
        print_info "Edit: $ORACLE_CLIENT_DIR/network/admin/tnsnames.ora"
    fi
fi

###############################################################################
# SECTION 5: Install RDP Session Manager Package
###############################################################################

print_header "5/5 - Installing RDP Session Manager"

print_section "Installing package: $PKG_FILE"

case "$DISTRO_TYPE" in
    arch)
        if sudo pacman -U --noconfirm "$PKG_FILE"; then
            print_success "RDP Session Manager package installed"
        else
            print_error "RDP Session Manager package installation failed"
        fi
        ;;
    debian)
        if sudo dpkg -i "$PKG_FILE"; then
            print_success "RDP Session Manager package installed"
        else
            print_warning "Fixing dependencies..."
            sudo apt-get install -f -y
            print_success "Dependencies fixed"
        fi
        ;;
esac

# Create symlink for compatibility
print_section "Configuring system symlinks..."
if [ ! -e /opt/rdp-user ]; then
    sudo ln -s /opt/rdp-users /opt/rdp-user
    print_success "Created symlink /opt/rdp-user -> /opt/rdp-users"
else
    print_skip "Symlink /opt/rdp-user"
fi

###############################################################################
# Installation Summary
###############################################################################

print_header "Installation Summary"

echo -e "  ${GREEN}✓ Installed:${NC} $INSTALLED_COUNT packages"
echo -e "  ${BLUE}○ Skipped:${NC}   $SKIPPED_COUNT packages (already installed)"

if [ $FAILED_COUNT -gt 0 ]; then
    echo -e "  ${RED}✗ Failed:${NC}    $FAILED_COUNT packages"
    echo -e "$FAILED_PACKAGES"
    echo ""
    print_warning "Some packages failed to install. Check the errors above."
fi

echo ""

# Verify critical components
print_section "Verifying installation..."

CRITICAL_OK=true

# Check xrdp
if systemctl is-active xrdp &>/dev/null; then
    print_success "xrdp service is running"
else
    print_warning "xrdp service is not running (start with: sudo systemctl start xrdp)"
    CRITICAL_OK=false
fi

# Check winetricks
if command_exists winetricks; then
    print_success "winetricks is available"
else
    print_warning "winetricks not found (WineGE RemoteApp may not work)"
fi

# Check Oracle
if [ -d "$ORACLE_CLIENT_DIR" ]; then
    print_success "Oracle Instant Client is installed"
else
    print_info "Oracle Instant Client not installed (optional)"
fi

# Check application
if command_exists rdp-session-manager; then
    print_success "rdp-session-manager command is available"
else
    print_warning "rdp-session-manager command not found"
    CRITICAL_OK=false
fi

echo ""

if [ "$CRITICAL_OK" = true ]; then
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}  Installation completed successfully!${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo "Run: rdp-session-manager"
    echo ""
else
    echo -e "${YELLOW}=========================================${NC}"
    echo -e "${YELLOW}  Installation completed with warnings${NC}"
    echo -e "${YELLOW}=========================================${NC}"
    echo ""
    echo "Please review the warnings above before using the application."
    echo ""
fi
