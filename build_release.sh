#!/bin/bash
###############################################################################
# Build Package - RDP Session Manager
###############################################################################

set -e

APP_NAME="rdp-session-manager"
APP_VERSION="$(python3 -c "import re; print(re.search(r\"version='([^']+)'\", open('setup.py').read()).group(1))")"
APP_DESCRIPTION="Gerenciador de Sessões RDP com Interface GTK4"
APP_MAINTAINER="Your Name <your.email@example.com>"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${PROJECT_DIR}/build_temp"
RELEASE_DIR="${PROJECT_DIR}/release"

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

echo "========================================="
echo "  Building RDP Session Manager"
echo "========================================="
echo "Detected distribution: $DISTRO"
echo ""

# Check fpm
if ! command -v fpm &> /dev/null; then
    echo "ERROR: fpm not installed"
    echo ""
    case "$DISTRO" in
        arch|manjaro|endeavouros|cachyos)
            echo "Install with:"
            echo "  sudo pacman -S ruby rubygems"
            echo "  sudo gem install fpm"
            ;;
        debian|ubuntu|linuxmint|pop)
            echo "Install with:"
            echo "  sudo apt-get install -y ruby ruby-dev rubygems build-essential"
            echo "  sudo gem install fpm"
            ;;
        *)
            echo "Install fpm from: https://github.com/jordansissel/fpm"
            ;;
    esac
    exit 1
fi

# Clean and create directories
rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/share/${APP_NAME}"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${BUILD_DIR}/usr/share/polkit-1/actions"
mkdir -p "${BUILD_DIR}/usr/share/glib-2.0/schemas"
mkdir -p "${BUILD_DIR}/usr/share/metainfo"
mkdir -p "${RELEASE_DIR}"

# Clean old packages
rm -f "${RELEASE_DIR}/${APP_NAME}_${APP_VERSION}_all.deb"
rm -f "${RELEASE_DIR}/${APP_NAME}-${APP_VERSION}-1-any.pkg.tar.zst"

# Copy source files
echo "→ Copying files..."
cp -r src "${BUILD_DIR}/usr/share/${APP_NAME}/"
mkdir -p "${BUILD_DIR}/usr/share/${APP_NAME}/data"
cp -r data/ui "${BUILD_DIR}/usr/share/${APP_NAME}/data/"

# Copy scripts if exist
[ -d "scripts" ] && cp -r scripts "${BUILD_DIR}/usr/share/${APP_NAME}/"

# Copy helper scripts (CRITICAL for user creation!)
if [ -d "helpers" ]; then
    echo "→ Copying helper scripts..."
    cp -r helpers "${BUILD_DIR}/usr/share/${APP_NAME}/"
    chmod +x "${BUILD_DIR}/usr/share/${APP_NAME}/helpers/"*.sh
fi

# Clean Python cache
find "${BUILD_DIR}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_DIR}" -type f -name "*.pyc" -delete 2>/dev/null || true

# Create launcher scripts
cat > "${BUILD_DIR}/usr/bin/${APP_NAME}" << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/usr/share/rdp-session-manager/src')
from main import main
if __name__ == '__main__':
    sys.exit(main())
EOF
chmod +x "${BUILD_DIR}/usr/bin/${APP_NAME}"

cat > "${BUILD_DIR}/usr/bin/rdpsm" << 'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/usr/share/rdp-session-manager/src')
from cli import main
if __name__ == '__main__':
    main()
EOF
chmod +x "${BUILD_DIR}/usr/bin/rdpsm"

# Copy desktop file
[ -f "data/com.rdp.SessionManager.desktop.in" ] && \
    sed "s|@bindir@|/usr/bin|g" data/com.rdp.SessionManager.desktop.in > \
    "${BUILD_DIR}/usr/share/applications/com.rdp.SessionManager.desktop"

# Copy icon
[ -f "imgs/RDPSM.png" ] && \
    cp imgs/RDPSM.png "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps/com.rdp.SessionManager.png"

# Copy other files
[ -f "data/com.rdp.SessionManager.policy" ] && \
    cp data/com.rdp.SessionManager.policy "${BUILD_DIR}/usr/share/polkit-1/actions/"
[ -f "data/com.rdp.SessionManager.gschema.xml" ] && \
    cp data/com.rdp.SessionManager.gschema.xml "${BUILD_DIR}/usr/share/glib-2.0/schemas/"
[ -f "data/com.rdp.SessionManager.appdata.xml" ] && \
    cp data/com.rdp.SessionManager.appdata.xml "${BUILD_DIR}/usr/share/metainfo/"

# Create post-install script inline
cat > "${BUILD_DIR}/DEBIAN_postinst" << 'POSTINSTALL'
#!/bin/bash
echo "Configurando RDP Session Manager..."
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database /usr/share/applications 2>/dev/null || true
command -v glib-compile-schemas >/dev/null 2>&1 && glib-compile-schemas /usr/share/glib-2.0/schemas 2>/dev/null || true
command -v appstreamcli >/dev/null 2>&1 && appstreamcli refresh-cache --force 2>/dev/null || true
echo "✓ RDP Session Manager instalado com sucesso!"
echo "Execute 'rdp-session-manager' para abrir a interface gráfica"
POSTINSTALL
chmod +x "${BUILD_DIR}/DEBIAN_postinst"

# Create post-remove script inline
cat > "${BUILD_DIR}/DEBIAN_postrm" << 'POSTREMOVE'
#!/bin/bash
echo "Removendo configurações do RDP Session Manager..."
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database /usr/share/applications 2>/dev/null || true
command -v glib-compile-schemas >/dev/null 2>&1 && glib-compile-schemas /usr/share/glib-2.0/schemas 2>/dev/null || true
echo "✓ RDP Session Manager removido"
POSTREMOVE
chmod +x "${BUILD_DIR}/DEBIAN_postrm"

# Build package(s)
case "$DISTRO" in
    arch|manjaro|endeavouros|cachyos)
        echo "→ Building Arch package (.pkg.tar.zst)..."
        fpm -s dir -t pacman \
            -n "${APP_NAME}" \
            -v "${APP_VERSION}" \
            -a any \
            --description "${APP_DESCRIPTION}" \
            --maintainer "${APP_MAINTAINER}" \
            --license "GPL-3.0" \
            --category "admin" \
            --depends "python>=3.8" \
            --depends "python-gobject" \
            --depends "python-cairo" \
            --depends "gtk4" \
            --depends "libadwaita" \
            --depends "polkit" \
            --depends "python-psutil" \
            --after-install "${BUILD_DIR}/DEBIAN_postinst" \
            --after-remove "${BUILD_DIR}/DEBIAN_postrm" \
            -C "${BUILD_DIR}" \
            -p "${RELEASE_DIR}/${APP_NAME}-${APP_VERSION}-1-any.pkg.tar.zst" \
            .

        echo ""
        echo "✓ Package created: release/${APP_NAME}-${APP_VERSION}-1-any.pkg.tar.zst"
        ;;
    debian|ubuntu|linuxmint|pop)
        echo "→ Building Debian package (.deb)..."
        fpm -s dir -t deb \
            -n "${APP_NAME}" \
            -v "${APP_VERSION}" \
            -a all \
            --description "${APP_DESCRIPTION}" \
            --maintainer "${APP_MAINTAINER}" \
            --license "GPL-3.0" \
            --category "admin" \
            --depends "python3 >= 3.8" \
            --depends "python3-gi" \
            --depends "python3-gi-cairo" \
            --depends "gir1.2-gtk-4.0" \
            --depends "gir1.2-adw-1" \
            --depends "libadwaita-1-0" \
            --depends "polkitd | policykit-1" \
            --depends "python3-psutil" \
            --after-install "${BUILD_DIR}/DEBIAN_postinst" \
            --after-remove "${BUILD_DIR}/DEBIAN_postrm" \
            -C "${BUILD_DIR}" \
            -p "${RELEASE_DIR}/${APP_NAME}_${APP_VERSION}_all.deb" \
            .

        echo ""
        echo "✓ Package created: release/${APP_NAME}_${APP_VERSION}_all.deb"
        ;;
    *)
        echo "Building both DEB and Arch packages..."

        # Build DEB
        echo "→ Building Debian package (.deb)..."
        fpm -s dir -t deb \
            -n "${APP_NAME}" \
            -v "${APP_VERSION}" \
            -a all \
            --description "${APP_DESCRIPTION}" \
            --maintainer "${APP_MAINTAINER}" \
            --license "GPL-3.0" \
            --category "admin" \
            --depends "python3 >= 3.8" \
            --depends "python3-gi" \
            --depends "python3-gi-cairo" \
            --depends "gir1.2-gtk-4.0" \
            --depends "gir1.2-adw-1" \
            --depends "libadwaita-1-0" \
            --depends "polkitd | policykit-1" \
            --depends "python3-psutil" \
            --after-install "${BUILD_DIR}/DEBIAN_postinst" \
            --after-remove "${BUILD_DIR}/DEBIAN_postrm" \
            -C "${BUILD_DIR}" \
            -p "${RELEASE_DIR}/${APP_NAME}_${APP_VERSION}_all.deb" \
            .

        # Build Arch package
        echo "→ Building Arch package (.pkg.tar.zst)..."
        fpm -s dir -t pacman \
            -n "${APP_NAME}" \
            -v "${APP_VERSION}" \
            -a any \
            --description "${APP_DESCRIPTION}" \
            --maintainer "${APP_MAINTAINER}" \
            --license "GPL-3.0" \
            --category "admin" \
            --depends "python>=3.8" \
            --depends "python-gobject" \
            --depends "python-cairo" \
            --depends "gtk4" \
            --depends "libadwaita" \
            --depends "polkit" \
            --depends "python-psutil" \
            --after-install "${BUILD_DIR}/DEBIAN_postinst" \
            --after-remove "${BUILD_DIR}/DEBIAN_postrm" \
            -C "${BUILD_DIR}" \
            -p "${RELEASE_DIR}/${APP_NAME}-${APP_VERSION}-1-any.pkg.tar.zst" \
            .

        echo ""
        echo "✓ Packages created:"
        echo "  - release/${APP_NAME}_${APP_VERSION}_all.deb"
        echo "  - release/${APP_NAME}-${APP_VERSION}-1-any.pkg.tar.zst"
        ;;
esac

rm -rf "${BUILD_DIR}"

echo ""
echo "Install with: ./install.sh"
