#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE="${1:?usage: run_installation.sh SOURCE TAG VERSION FAMILY WITH_WINE REQUIRE_SERVICE [BUNDLE]}"
TAG="${2:?usage: run_installation.sh SOURCE TAG VERSION FAMILY WITH_WINE REQUIRE_SERVICE [BUNDLE]}"
EXPECTED_VERSION="${3:?usage: run_installation.sh SOURCE TAG VERSION FAMILY WITH_WINE REQUIRE_SERVICE [BUNDLE]}"
DISTRO_FAMILY="${4:?usage: run_installation.sh SOURCE TAG VERSION FAMILY WITH_WINE REQUIRE_SERVICE [BUNDLE]}"
WITH_WINE="${5:?usage: run_installation.sh SOURCE TAG VERSION FAMILY WITH_WINE REQUIRE_SERVICE [BUNDLE]}"
REQUIRE_SERVICE="${6:?usage: run_installation.sh SOURCE TAG VERSION FAMILY WITH_WINE REQUIRE_SERVICE [BUNDLE]}"
BUNDLE="${7:-}"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/rdpsm-real-install.XXXXXX")"
trap 'rm -rf "$TEMP_DIR"' EXIT

installer_args=(--yes --verbose)
if [[ "$WITH_WINE" == "true" ]]; then
    installer_args+=(--with-wine)
fi

case "$SOURCE" in
    bundle)
        [[ -f "$BUNDLE" ]] || {
            printf 'Installer bundle not found: %s\n' "$BUNDLE" >&2
            exit 1
        }
        bundle_dir="$TEMP_DIR/bundle"
        mkdir -p "$bundle_dir"
        python3 -m zipfile -e "$BUNDLE" "$bundle_dir"
        mapfile -t bundle_files < <(
            find "$bundle_dir" -maxdepth 1 -type f -printf '%f\n' | sort
        )
        mapfile -t expected_files < <(
            printf '%s\n' \
                installer.pyz \
                rdp-session-manager.deb \
                rdp-session-manager.pkg.tar.zst \
                SHA256SUMS |
                sort
        )
        if [[ "${bundle_files[*]}" != "${expected_files[*]}" ]]; then
            printf 'Unexpected installer bundle contents: %s\n' "${bundle_files[*]}" >&2
            exit 1
        fi
        (cd "$bundle_dir" && sha256sum --check --strict SHA256SUMS)
        python3 "$bundle_dir/installer.pyz" \
            --bundle-dir "$bundle_dir" \
            --resolved-release "$TAG" \
            "${installer_args[@]}"
        ;;
    release)
        repository="${RDPSM_REPOSITORY:-Pedroltz/rdp-session-manager}"
        bootstrap_url="https://github.com/${repository}/releases/download/${TAG}/install.sh"
        curl -fsSL "$bootstrap_url" |
            bash -s -- --release "$TAG" "${installer_args[@]}"
        ;;
    *)
        printf 'Unknown installation source: %s\n' "$SOURCE" >&2
        exit 1
        ;;
esac

bash "$PROJECT_DIR/tests/ci/verify_installation.sh" \
    "$EXPECTED_VERSION" \
    "$DISTRO_FAMILY" \
    "$WITH_WINE" \
    "$REQUIRE_SERVICE"
