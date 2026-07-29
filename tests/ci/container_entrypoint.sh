#!/usr/bin/env bash
set -Eeuo pipefail

: "${RDPSM_FAMILY:?RDPSM_FAMILY is required}"
: "${RDPSM_SOURCE:?RDPSM_SOURCE is required}"
: "${RDPSM_TAG:?RDPSM_TAG is required}"
: "${RDPSM_VERSION:?RDPSM_VERSION is required}"
: "${RDPSM_WITH_WINE:?RDPSM_WITH_WINE is required}"

run_test() {
    bash /workspace/tests/ci/run_installation.sh \
        "$RDPSM_SOURCE" \
        "$RDPSM_TAG" \
        "$RDPSM_VERSION" \
        "$RDPSM_FAMILY" \
        "$RDPSM_WITH_WINE" \
        false \
        "${RDPSM_BUNDLE:-}"
}

case "$RDPSM_FAMILY" in
    debian)
        export DEBIAN_FRONTEND=noninteractive
        apt-get update
        apt-get install -y --no-install-recommends \
            bash \
            ca-certificates \
            curl \
            dbus-x11 \
            iproute2 \
            procps \
            python3 \
            systemd \
            xvfb
        export HOME=/ci-home
        run_test
        ;;
    arch)
        pacman -Syu --needed --noconfirm \
            bash \
            ca-certificates \
            curl \
            dbus \
            iproute \
            procps-ng \
            python \
            sudo \
            xorg-server-xvfb
        useradd --create-home --shell /bin/bash rdpsm-ci
        printf 'rdpsm-ci ALL=(ALL) NOPASSWD: ALL\n' >/etc/sudoers.d/rdpsm-ci
        chmod 440 /etc/sudoers.d/rdpsm-ci
        chown -R rdpsm-ci:rdpsm-ci /ci-home
        set +e
        sudo -u rdpsm-ci \
            env \
                HOME=/ci-home \
                PATH="$PATH" \
                RDPSM_FAMILY="$RDPSM_FAMILY" \
                RDPSM_SOURCE="$RDPSM_SOURCE" \
                RDPSM_TAG="$RDPSM_TAG" \
                RDPSM_VERSION="$RDPSM_VERSION" \
                RDPSM_WITH_WINE="$RDPSM_WITH_WINE" \
                RDPSM_BUNDLE="${RDPSM_BUNDLE:-}" \
                RDPSM_REPOSITORY="${RDPSM_REPOSITORY:-}" \
            bash -c '
                bash /workspace/tests/ci/run_installation.sh \
                    "$RDPSM_SOURCE" \
                    "$RDPSM_TAG" \
                    "$RDPSM_VERSION" \
                    "$RDPSM_FAMILY" \
                    "$RDPSM_WITH_WINE" \
                    false \
                    "$RDPSM_BUNDLE"
            '
        test_status=$?
        set -e
        chmod -R a+rX /ci-home
        exit "$test_status"
        ;;
    *)
        printf 'Unsupported container family: %s\n' "$RDPSM_FAMILY" >&2
        exit 1
        ;;
esac
