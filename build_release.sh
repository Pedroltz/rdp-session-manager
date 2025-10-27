#!/bin/bash
###############################################################################
# Build .deb Package - RDP Session Manager
###############################################################################

set -e

APP_NAME="rdp-session-manager"
APP_VERSION="0.2.2"
APP_DESCRIPTION="Gerenciador de Sessões RDP com Interface GTK4"
APP_MAINTAINER="Your Name <your.email@example.com>"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${PROJECT_DIR}/build_temp"
RELEASE_DIR="${PROJECT_DIR}/release"

echo "========================================="
echo "  Building RDP Session Manager"
echo "========================================="
echo ""

# Check fpm
if ! command -v fpm &> /dev/null; then
    echo "ERROR: fpm not installed"
    echo ""
    echo "Install with:"
    echo "  sudo apt-get install -y ruby ruby-dev rubygems build-essential"
    echo "  sudo gem install fpm"
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
rm -f "${RELEASE_DIR}/${APP_NAME}_${APP_VERSION}_all.deb"

# Copy source files
echo "→ Copying files..."
cp -r src "${BUILD_DIR}/usr/share/${APP_NAME}/"
mkdir -p "${BUILD_DIR}/usr/share/${APP_NAME}/data"
cp -r data/ui "${BUILD_DIR}/usr/share/${APP_NAME}/data/"

# Copy scripts if exist
[ -d "scripts" ] && cp -r scripts "${BUILD_DIR}/usr/share/${APP_NAME}/"

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

# Build package
echo "→ Building .deb package..."
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
    --after-install "${PROJECT_DIR}/post-install.sh" \
    --after-remove "${PROJECT_DIR}/post-remove.sh" \
    -C "${BUILD_DIR}" \
    -p "${RELEASE_DIR}/${APP_NAME}_${APP_VERSION}_all.deb" \
    .

rm -rf "${BUILD_DIR}"

echo ""
echo "✓ Package created: release/${APP_NAME}_${APP_VERSION}_all.deb"
echo ""
echo "Install with: ./install.sh"
