#!/bin/bash
# Install a pinned, checksum-verified official umu-launcher package.
set -euo pipefail

if command -v umu-run >/dev/null 2>&1; then
    exit 0
fi

. /etc/os-release
case "$(uname -m)" in
    x86_64) ARCH="amd64" ;;
    aarch64) ARCH="arm64" ;;
    *) ARCH="$(uname -m)" ;;
esac
VERSION="1.4.0"
BASE_URL="https://github.com/Open-Wine-Components/umu-launcher/releases/download/$VERSION"

case "${ID}:${VERSION_ID}:${ARCH}" in
    arch:*:amd64)
        pacman -S --needed --noconfirm umu-launcher
        exit 0
        ;;
    ubuntu:22.04:amd64)
        ASSET="umu-launcher-${VERSION}-zipapp.tar"
        SHA256="138ce4b8843608a257d4bee88191ca78a989778bcefd8abb3c1d1aaac3ac6fb8"
        ASSET_TYPE="zipapp"
        ;;
    ubuntu:24.04:amd64)
        ASSET="python3-umu-launcher_${VERSION}-1_amd64_ubuntu-noble.deb"
        SHA256="23e1147ac7a5d407292458d5b432658c9a2dac4395d400afa828072605b88b78"
        ASSET_TYPE="deb"
        ;;
    debian:12:amd64)
        ASSET="python3-umu-launcher_${VERSION}-1_amd64_debian-12.deb"
        SHA256="adb75de5f982f063021ad907a395d3237203bd62bd398418d42eb599192ddd3f"
        ASSET_TYPE="deb"
        ;;
    debian:13:amd64)
        ASSET="python3-umu-launcher_${VERSION}-1_amd64_debian-13.deb"
        SHA256="3de80fdcffdc5daabd65e7c9567aff4b8beeecc238eae11529fe737c0b4083f7"
        ASSET_TYPE="deb"
        ;;
    *:amd64)
        # The official zipapp is distribution-independent. It also covers
        # newer Ubuntu/Debian releases and supported derivatives for which the
        # upstream project does not publish a release-specific .deb.
        ASSET="umu-launcher-${VERSION}-zipapp.tar"
        SHA256="138ce4b8843608a257d4bee88191ca78a989778bcefd8abb3c1d1aaac3ac6fb8"
        ASSET_TYPE="zipapp"
        ;;
    *)
        echo "No verified umu-launcher package is available for ${ID} ${VERSION_ID} ${ARCH}." >&2
        echo "Install umu-run manually before creating Windows RemoteApps." >&2
        exit 1
        ;;
esac

TMP_DIR="$(mktemp -d -t rdpsm-umu-XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
curl --fail --location --retry 3 --output "$TMP_DIR/$ASSET" "$BASE_URL/$ASSET"
printf '%s  %s\n' "$SHA256" "$TMP_DIR/$ASSET" | sha256sum --check -
if [ "$ASSET_TYPE" = "deb" ]; then
    apt-get install -y "$TMP_DIR/$ASSET"
else
    DESTINATION="/opt/rdp-session-manager/umu-launcher-$VERSION"
    SAFE_EXTRACTOR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/extract-safe-tar.py"
    [ -f "$SAFE_EXTRACTOR" ] || {
        echo "Safe tar extractor is missing: $SAFE_EXTRACTOR" >&2
        exit 1
    }
    python3 "$SAFE_EXTRACTOR" "$TMP_DIR/$ASSET" "$TMP_DIR/extracted"
    case "$DESTINATION" in
        /opt/rdp-session-manager/umu-launcher-*) rm -rf "$DESTINATION" ;;
        *) echo "Refusing unsafe destination: $DESTINATION" >&2; exit 1 ;;
    esac
    mkdir -p "$(dirname "$DESTINATION")"
    mv "$TMP_DIR/extracted" "$DESTINATION"
    UMU_SOURCE="$(find "$DESTINATION" -type f \( -name umu-run -o -name 'umu*.pyz' \) -print -quit)"
    [ -n "$UMU_SOURCE" ] || {
        echo "Verified umu zipapp did not contain umu-run." >&2
        exit 1
    }
    chmod 755 "$UMU_SOURCE"
    ln -sfn "$UMU_SOURCE" /usr/local/bin/umu-run
fi
command -v umu-run >/dev/null 2>&1
